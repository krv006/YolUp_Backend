"""Faol seanslar (qurilmalar): har kirish (login / ro'yxatdan o'tish / akkaunt almashtirish) bitta `UserSession`.

Seans refresh va access tokenlarda `sid` da'vosi (claim) sifatida yuradi — token yangilanganda ham saqlanadi.
Seansni "chiqarib yuborish" = `revoked_at` qo'yish: shu seansning access tokeni darhol (cache belgisi orqali,
`SessionJWTAuthentication`), refresh tokeni esa keyingi yangilashda rad etiladi.
Eski (yangilanishdan oldingi) tokenlarda `sid` yo'q — ular keyingi yangilashda avtomatik seansga ega bo'ladi.
"""
import re

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserSession

MAX_ACTIVE_SESSIONS = 20
REVOKED_MARK_TTL = 2 * 60 * 60  # access token umridan (60 daqiqa) uzunroq


def _mark_key(sid) -> str:
    return f'session:revoked:{sid}'


def _mark_revoked(sid) -> None:
    try:
        cache.set(_mark_key(sid), 1, REVOKED_MARK_TTL)
    except Exception:  # noqa: BLE001 — cache ishlamasa ham seans bazada bekor qilingan, refresh rad etiladi
        pass


def is_revoked(sid) -> bool:
    """Access token tekshiruvi uchun tez yo'l (har so'rovda chaqiriladi — faqat cache)."""
    try:
        return bool(cache.get(_mark_key(sid)))
    except Exception:  # noqa: BLE001
        return False


def parse_device(user_agent: str, header_name: str = '') -> str:
    """Foydalanuvchiga ko'rsatiladigan qurilma nomi. Mobil ilova `X-Device-Name` yuborsa — o'sha."""
    header_name = (header_name or '').strip()
    if header_name:
        return header_name[:120]
    ua = user_agent or ''
    if not ua:
        return "Noma'lum qurilma"
    if re.match(r'^(okhttp|Dart|CFNetwork)', ua):
        return 'Mobil ilova'
    model = re.search(r'Android [\d.]+; ([^;)]+)', ua)
    if model:
        system = model.group(1).strip()
    elif 'iPhone' in ua:
        system = 'iPhone'
    elif 'iPad' in ua:
        system = 'iPad'
    elif 'Windows' in ua:
        system = 'Windows'
    elif 'Mac OS X' in ua or 'Macintosh' in ua:
        system = 'macOS'
    elif 'Android' in ua:
        system = 'Android'
    elif 'Linux' in ua:
        system = 'Linux'
    else:
        system = ''
    for needle, name in (('Edg/', 'Edge'), ('OPR/', 'Opera'), ('Firefox/', 'Firefox'), ('Chrome/', 'Chrome'), ('Safari/', 'Safari')):
        if needle in ua:
            browser = name
            break
    else:
        browser = ''
    return ' · '.join(part for part in (browser, system) if part)[:120] or ua[:60]


def client_ip(request):
    if request is None:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')) or None


_geoip_reader = None
_geoip_failed = False


def city_for_ip(ip) -> str:
    """IP bo'yicha shahar nomi. `GEOIP_CITY_DB` (MaxMind GeoLite2-City `.mmdb` yo'li) sozlanmagan, kutubxona yoki fayl
    yo'q, yoki IP topilmasa — bo'sh qator (kirishni hech qachon to'xtatmaydi)."""
    global _geoip_reader, _geoip_failed
    path = getattr(settings, 'GEOIP_CITY_DB', '')
    if not ip or not path or _geoip_failed:
        return ''
    try:
        if _geoip_reader is None:
            import geoip2.database

            _geoip_reader = geoip2.database.Reader(path)
        record = _geoip_reader.city(str(ip))
        return (record.city.name or '')[:100]
    except Exception:  # noqa: BLE001 — AddressNotFound, fayl yo'q, kutubxona yo'q va h.k.
        if _geoip_reader is None:
            _geoip_failed = True  # fayl ochilmadi — har kirishda urinib o'tirmaymiz
        return ''


def start_session(user, request) -> UserSession:
    meta = request.META if request is not None else {}
    ip = client_ip(request)
    session = UserSession.objects.create(
        user=user, user_agent=(meta.get('HTTP_USER_AGENT') or '')[:300], ip=ip, city=city_for_ip(ip),
        device=parse_device(meta.get('HTTP_USER_AGENT', ''), meta.get('HTTP_X_DEVICE_NAME', '')),
    )
    extra = list(
        UserSession.objects.filter(user=user, revoked_at__isnull=True)
        .order_by('-last_active', '-created_at')[MAX_ACTIVE_SESSIONS:]
    )
    for old in extra:
        revoke(old)
    return session


def issue_refresh(user, request) -> RefreshToken:
    """Yangi kirish uchun refresh token (access shundan olinadi) — `sid` bilan."""
    refresh = RefreshToken.for_user(user)
    refresh['sid'] = str(start_session(user, request).id)
    return refresh


def revoke(session: UserSession) -> None:
    if session.revoked_at is None:
        session.revoked_at = timezone.now()
        session.save(update_fields=['revoked_at', 'updated_at'])
    _mark_revoked(session.id)


def revoke_by_token(refresh_token: str) -> None:
    """Chiqishda (logout): refresh tokendagi `sid` seansini yopadi. Yaroqsiz token e'tiborsiz qoladi."""
    try:
        sid = RefreshToken(refresh_token).get('sid')
    except Exception:  # noqa: BLE001
        return
    if sid:
        for session in UserSession.objects.filter(pk=sid, revoked_at__isnull=True):
            revoke(session)


def revoke_all(user) -> None:
    for session in UserSession.objects.filter(user=user, revoked_at__isnull=True):
        revoke(session)


class SessionTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login: odatiy token juftligi + yangi seans (`sid`)."""

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.two_factor_enabled:
            from . import services

            return services.two_factor_challenge(self.user)  # kod tasdiqlanmaguncha token berilmaydi
        refresh = RefreshToken(data['refresh'])
        refresh['sid'] = str(start_session(self.user, self.context.get('request')).id)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        return data


class SessionTokenRefreshSerializer(TokenRefreshSerializer):
    """Token yangilash: bekor qilingan seans rad etiladi; `sid`siz eski token seansga ega bo'ladi."""

    def validate(self, attrs):
        token = RefreshToken(attrs['refresh'])  # yaroqsiz/blacklist bo'lsa shu yerda xato beradi
        sid = token.get('sid')
        now = timezone.now()
        if sid:
            session = UserSession.objects.filter(pk=sid, user_id=token.get('user_id')).first()
            if session is None or session.revoked_at is not None:
                raise InvalidToken('Seans yopilgan.')
            session.last_active = now
            session.save(update_fields=['last_active', 'updated_at'])
        else:
            from .models import User

            user = User.objects.filter(pk=token.get('user_id')).first()
            if user is not None:
                token['sid'] = str(start_session(user, self.context.get('request')).id)
                attrs = {**attrs, 'refresh': str(token)}
        return super().validate(attrs)
