"""Bir martalik kodlar (parolni tiklash, 2FA) — cache'da, kod o'zi emas HASHI saqlanadi.

Qoidalar: kod 5 xonali, 120 soniya amal qiladi, har telefonga 45 soniyada bir marta (`retry_after`) va kuniga ko'pi bilan
10 marta yuboriladi; noto'g'ri kiritish 5 martadan keyin kodni bekor qiladi.
"""
import hashlib
import hmac
import secrets
import time

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import Throttled, ValidationError

from apps.core import sms

CODE_TTL = 120
RETRY_AFTER = 45
DAILY_LIMIT = 10
MAX_ATTEMPTS = 5


def _digest(scope: str, code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f'{scope}:{code}'.encode(), hashlib.sha256).hexdigest()


def issue(*, scope: str, phone: str, payload: dict | None = None) -> dict:
    """Yangi kod yaratib SMS yuboradi. Qaytaradi: `{sent, expires_in, retry_after}`. Juda tez/ko'p so'ralsa — 429."""
    norm = sms.normalize_phone(phone)
    now = time.time()
    cool_key = f'otp:cool:{scope}:{norm}'
    last = cache.get(cool_key)
    if last and now - last < RETRY_AFTER:
        raise Throttled(wait=RETRY_AFTER - int(now - last))
    day_key = f'otp:day:{scope}:{norm}'
    cache.add(day_key, 0, 24 * 3600)
    try:
        used = cache.incr(day_key)
    except ValueError:
        used = 1
    if used > DAILY_LIMIT:
        raise Throttled(wait=3600, detail=str(_("Bugun juda ko'p kod so'raldi. Ertaga urinib ko'ring.")))
    code = f'{secrets.randbelow(100000):05d}'
    sms.send_sms(phone, sms.code_text(code))  # yuborilmasa (503/502) — sovitish va hisoblagich kuymasin
    cache.set(cool_key, now, RETRY_AFTER)
    cache.set(
        f'otp:code:{scope}:{norm}',
        {'hash': _digest(scope, code), 'attempts': 0, 'payload': payload or {}, 'exp': now + CODE_TTL}, CODE_TTL,
    )
    return {'sent': True, 'expires_in': CODE_TTL, 'retry_after': RETRY_AFTER}


def check(*, scope: str, phone: str, code: str) -> dict:
    """Kodni tekshiradi (bir martalik). Muvaffaqiyatda `payload` qaytadi; aks holda 400."""
    norm = sms.normalize_phone(phone)
    key = f'otp:code:{scope}:{norm}'
    entry = cache.get(key)
    bad = ValidationError({'detail': _("Kod noto'g'ri yoki muddati o'tgan")})
    if not entry:
        raise bad
    if not hmac.compare_digest(entry['hash'], _digest(scope, str(code or '').strip())):
        entry['attempts'] += 1
        if entry['attempts'] >= MAX_ATTEMPTS:
            cache.delete(key)
        else:
            cache.set(key, entry, max(int(entry['exp'] - time.time()), 1))  # asl muddat saqlanadi
        raise bad
    cache.delete(key)
    return entry['payload']
