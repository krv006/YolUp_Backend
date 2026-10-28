"""Accounts service layer — barcha yozuvchi biznes-logika shu yerda.

Qoida: view'lar faqat HTTP bilan ishlaydi (parse/serialize), qaror va yozuv —
service'da. Har bir muhim harakat audit'ga tushadi.
"""
import secrets

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.core import audit

from .models import Consent, ParentChildLink, SocialIdentity, TeacherCertificate, User

# O'quvchi/ota-ona uchun standart 15 daqiqa (User.lesson_reminder_minutes
# maydon standarti) yetarli — o'qituvchi esa darsni BOSHLASHI kerak,
# shuning uchun biroz kamroq (10 daqiqa) oldindan ogohlantiriladi.
TEACHER_LESSON_REMINDER_MINUTES = 10


def _notify_admins_of_pending_teacher(teacher: User, request=None) -> None:
    """Yangi o'qituvchi ro'yxatdan o'tganda BARCHA adminlarga bildirishnoma.
    (Tasdiqlash endi to'siq emas — o'qituvchi darhol ishlay oladi — lekin
    admin yangi o'qituvchidan xabardor bo'lib turadi. `kind` nomi frontend
    bilan moslik uchun o'zgarmagan.)"""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    full_name = teacher.get_full_name() or teacher.username
    admin_ids = User.objects.filter(
        role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN],
    ).values_list('id', flat=True)
    for admin_id in admin_ids:
        send_notification(
            sender=teacher,
            description=_("Yangi o'qituvchi ro'yxatdan o'tdi: %(name)s (@%(username)s).") % {
                'name': full_name, 'username': teacher.username,
            },
            target_type=Notification.Target.USER, user_id=admin_id,
            kind='teacher_pending_approval', link_type='teacher', link_id=str(teacher.id),
            request=request,
        )


def _notify_teacher_approved(teacher: User, request=None) -> None:
    """Tasdiqlangandan keyin o'qituvchining o'ziga xabar — endi kurs/dars
    ochish kabi barcha amallar ochilganini bilishi uchun."""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    send_notification(
        sender=teacher,
        description=_("Sizning hisobingiz admin tomonidan tasdiqlandi — endi kurs va dars yaratishingiz mumkin."),
        target_type=Notification.Target.USER, user_id=teacher.id,
        kind='teacher_approved', request=request,
    )


@transaction.atomic
def register_user(*, username: str, password: str, role: str, request=None, phone_token: str = '', **extra) -> User:
    if role not in (User.Role.TEACHER, User.Role.PARENT, User.Role.STUDENT):
        raise ValidationError({'role': _("Faqat o'qituvchi, ota-ona yoki o'quvchi ro'yxatdan o'ta oladi.")})
    user = User(username=username, role=role, **extra)
    if phone_token:
        user.phone_verified = consume_phone_token(phone_token, user.phone)
        user.phone_verified_at = timezone.now()
    if role == User.Role.TEACHER:
        # `is_approved` standart True: yangi o'qituvchi darhol ishlay oladi
        # (loyiha egasi qarori, 2026-10-05). Bayroq saqlanib qolgan — admin
        # uni qo'lda False qilsa, o'qituvchi yana bloklanadi (apps.core.permissions).
        user.lesson_reminder_minutes = TEACHER_LESSON_REMINDER_MINUTES
    user.set_password(password)
    user.save()
    audit.record(action='auth.register', actor=user, target=user, meta={'role': role}, request=request)
    if role == User.Role.TEACHER:
        transaction.on_commit(lambda: _notify_admins_of_pending_teacher(user, request=request))
    return user


def _free_username(email: str) -> str:
    """Ijtimoiy akkaunt uchun band bo'lmagan login: email boshi + (kerak bo'lsa) tasodifiy raqamlar."""
    import re
    import secrets

    base = re.sub(r'[^a-zA-Z0-9._]', '', (email or '').split('@')[0])[:20].lower() or 'user'
    if len(base) < 3:
        base = f'user{base}'
    candidate = base
    for _attempt in range(30):
        if not User.objects.filter(username__iexact=candidate).exists():
            return candidate
        candidate = f'{base}{secrets.randbelow(9000) + 1000}'
    return f'{base}{secrets.token_hex(4)}'


def social_login(*, provider: str, id_token: str, role=None, first_name: str = '', last_name: str = '', request=None):
    """Google/Apple bilan kirish. Qaytaradi `(holat, qiymat)`:

    - `('login', user)` — shu provayder akkaunti avval bog'langan yoki TASDIQLANGAN email bo'yicha mavjud akkaunt topildi;
    - `('created', user)` — yangi akkaunt ochildi (`role` berilgan);
    - `('signup_required', claims)` — yangi foydalanuvchi, lekin `role` berilmagan: ilova rol tanlatib qayta yuboradi.

    Xavfsizlik: mavjud akkauntga FAQAT ikkala tomonda email tasdiqlangan bo'lsa bog'lanadi (aks holda birovning emailini
    yozib olib akkauntini egallash mumkin bo'lardi). Parolsiz akkaunt: parol faqat "parolni tiklash" orqali o'rnatiladi."""
    from . import social

    claims = social.verify_id_token(provider, id_token)
    identity = SocialIdentity.objects.select_related('user').filter(provider=provider, subject=claims.subject).first()
    if identity is not None:
        if not identity.user.is_active:
            raise PermissionDenied(_('Akkaunt faol emas.'))
        return 'login', identity.user

    if claims.email and claims.email_verified:
        matches = list(User.objects.filter(email__iexact=claims.email, email_verified=True, is_active=True)[:2])
        if len(matches) == 1:
            SocialIdentity.objects.create(user=matches[0], provider=provider, subject=claims.subject, email=claims.email)
            audit.record(action='auth.social_link', actor=matches[0], target=matches[0], meta={'provider': provider}, request=request)
            return 'login', matches[0]

    if not role:
        return 'signup_required', claims

    with transaction.atomic():
        user = register_user(
            username=_free_username(claims.email), password=secrets.token_urlsafe(32), role=role, request=request,
            first_name=(first_name or claims.first_name)[:150], last_name=(last_name or claims.last_name)[:150],
            email=claims.email, email_verified=bool(claims.email and claims.email_verified),
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        SocialIdentity.objects.create(user=user, provider=provider, subject=claims.subject, email=claims.email)
    audit.record(action='auth.social_register', actor=user, target=user, meta={'provider': provider}, request=request)
    return 'created', user


def get_teacher(*, teacher_id) -> User:
    """Admin ko'rinishlarida (statistika/baholar) qayta-qayta kerak bo'lgan
    "topilmasa 404" qidiruvi — `approve_teacher` bilan bir xil xato xabari."""
    try:
        return User.objects.get(pk=teacher_id, role=User.Role.TEACHER)
    except (User.DoesNotExist, ValueError, TypeError):
        raise NotFound(_("O'qituvchi topilmadi."))


@transaction.atomic
def approve_teacher(*, admin: User, teacher_id, request=None) -> User:
    """Admin tomonidan tasdiqlash — shundan keyin o'qituvchiga hamma narsa ochiladi."""
    teacher = get_teacher(teacher_id=teacher_id)
    teacher.is_approved = True
    teacher.save(update_fields=['is_approved'])
    audit.record(action='teacher.approve', actor=admin, target=teacher, request=request)
    transaction.on_commit(lambda: _notify_teacher_approved(teacher, request=request))
    return teacher


@transaction.atomic
@transaction.atomic
def create_child(*, creator: User, username: str, password: str, request=None, course_id=None, **extra) -> User:
    """O'quvchi hisobini yaratadi — ota-ona yoki o'qituvchi.

    Ota-ona yaratsa — ParentChildLink darhol APPROVED (FRD: auth.child_create).
    O'qituvchi yaratsa — bog'lanish yaratilmaydi (o'qituvchi ota-ona emas);
    o'quvchiga invite_code beriladi, haqiqiy ota-ona keyin shu kod orqali
    bog'lanishi mumkin. O'qituvchi bolani alohida enroll/ orqali kursiga
    biriktiradi.
    """
    course = None
    if course_id:
        # `course_id` faqat o'qituvchi uchun: o'z kursiga darhol biriktiradi (xato bo'lsa hisob ham yaratilmaydi)
        from apps.lessons.models import Course

        if creator.role != User.Role.TEACHER:
            raise ValidationError({'course_id': _("Kursga faqat o'qituvchi biriktira oladi.")})
        course = Course.objects.filter(pk=course_id).first()
        if course is None:
            raise NotFound(_('Kurs topilmadi.'))
        if course.teacher_id != creator.id:
            raise PermissionDenied(_("Faqat o'z kursingizga o'quvchi biriktira olasiz."))
    child = User(username=username, role=User.Role.STUDENT, **extra)
    child.set_password(password)
    child.save()
    if course is not None:
        from apps.lessons import services as lesson_services

        lesson_services.enroll(course_id=course.id, by_user=creator, student_id=child.id, request=request)
        child.enrolled_course_id = course.id
    if creator.role == User.Role.PARENT:
        ParentChildLink.objects.create(
            parent=creator, student=child, status=ParentChildLink.Status.APPROVED,
            responded_at=timezone.now(),
        )
    audit.record(action='child.create', actor=creator, target=child, request=request)
    return child


def change_password(*, user: User, current_password: str, new_password: str, request=None):
    """Parolni o'zgartiradi. Qaytaradi: `password_changed_at`."""
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError as DjangoValidationError

    if not user.check_password(current_password or ''):
        raise ValidationError({'detail': _("Joriy parol noto'g'ri")})
    if not new_password or new_password == current_password:
        raise ValidationError({'new_password': _("Yangi parol joriy paroldan farq qilishi kerak.")})
    try:
        validate_password(new_password, user)
    except DjangoValidationError as exc:
        raise ValidationError({'new_password': list(exc.messages)}) from None
    user.set_password(new_password)
    user.password_changed_at = timezone.now()
    user.save(update_fields=['password', 'password_changed_at'])
    audit.record(action='auth.password_change', actor=user, request=request)
    return user.password_changed_at


# ---------------------------------------------------------------------------
# Parolni tiklash (telefon + SMS kod)
# ---------------------------------------------------------------------------
RESET_TOKEN_TTL = 600


def _accounts_by_phone(raw_phone: str):
    from apps.core import sms

    users = User.objects.filter(phone__in=sms.phone_variants(raw_phone), is_active=True)
    digits = sms.normalize_phone(raw_phone)
    return [u for u in users if sms.normalize_phone(u.phone) == digits]


def password_reset_request(*, phone: str, request=None) -> dict:
    """1-qadam: shu telefonli akkaunt bor bo'lsa SMS kod yuboradi. Yo'q — 404 (frontend talabi)."""
    from . import otp

    if not _accounts_by_phone(phone):
        raise NotFound(_('Bunday raqam topilmadi'))
    result = otp.issue(scope='pwreset', phone=phone)
    audit.record(action='auth.password_reset_request', actor=None, meta={'phone': otp.sms.mask_phone(phone)}, request=request)
    return result


def password_reset_verify(*, phone: str, code: str) -> dict:
    """2-qadam: kod to'g'ri bo'lsa bir martalik `reset_token` (10 daqiqa)."""
    import hashlib
    import secrets

    from django.core.cache import cache

    from . import otp

    otp.check(scope='pwreset', phone=phone, code=code)
    token = secrets.token_urlsafe(32)
    cache.set(
        f'pwreset:token:{hashlib.sha256(token.encode()).hexdigest()}', otp.sms.normalize_phone(phone), RESET_TOKEN_TTL,
    )
    return {'reset_token': token, 'expires_in': RESET_TOKEN_TTL}


def password_reset_confirm(*, reset_token: str, password: str, request=None) -> dict:
    """3-qadam: yangi parol. Shu telefondagi hamma faol akkaunt (bitta odamning rol-akkauntlari) parolini yangilaydi,
    hamma seans va tokenlar bekor qilinadi."""
    import hashlib

    from django.contrib.auth.password_validation import validate_password
    from django.core.cache import cache
    from django.core.exceptions import ValidationError as DjangoValidationError
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    from . import sessions

    key = f'pwreset:token:{hashlib.sha256((reset_token or "").encode()).hexdigest()}'
    phone = cache.get(key)
    if not phone:
        raise ValidationError({'detail': _('Tiklash havolasi yaroqsiz yoki muddati o\'tgan. Qaytadan boshlang.')})
    users = _accounts_by_phone(phone)
    if not users:
        raise NotFound(_('Akkaunt topilmadi.'))
    try:
        validate_password(password or '', users[0])
    except DjangoValidationError as exc:
        raise ValidationError({'password': list(exc.messages)}) from None
    cache.delete(key)  # bir martalik
    now = timezone.now()
    with transaction.atomic():
        for user in users:
            user.set_password(password)
            user.password_changed_at = now
            user.save(update_fields=['password', 'password_changed_at'])
            sessions.revoke_all(user)
            for token in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=token)
            audit.record(action='auth.password_reset', actor=user, target=user, request=request)
    return {'ok': True}


# ---------------------------------------------------------------------------
# Ikki bosqichli tasdiqlash (2FA, SMS kod)
# ---------------------------------------------------------------------------
def two_factor_enable(*, user: User, password: str) -> dict:
    """SMS kod yuboradi; yoqish `two_factor_confirm` bilan tugaydi."""
    from . import otp

    if not user.check_password(password or ''):
        raise ValidationError({'password': _("Parol noto'g'ri.")})
    if not user.phone:
        raise ValidationError({'detail': _("Avval profilda telefon raqamingizni kiriting.")})
    if user.two_factor_enabled:
        raise ValidationError({'detail': _('Ikki bosqichli tasdiqlash allaqachon yoqilgan.')})
    return otp.issue(scope='2fa-setup', phone=user.phone, payload={'user': str(user.id)})


def two_factor_confirm(*, user: User, code: str, request=None) -> dict:
    from . import otp

    payload = otp.check(scope='2fa-setup', phone=user.phone or '', code=code)
    if payload.get('user') != str(user.id):
        raise ValidationError({'detail': _("Kod noto'g'ri yoki muddati o'tgan")})
    user.two_factor_enabled = True
    user.save(update_fields=['two_factor_enabled'])
    audit.record(action='auth.2fa_enable', actor=user, target=user, request=request)
    return {'enabled': True}


def two_factor_disable(*, user: User, password: str, request=None) -> dict:
    if not user.check_password(password or ''):
        raise ValidationError({'password': _("Parol noto'g'ri.")})
    user.two_factor_enabled = False
    user.save(update_fields=['two_factor_enabled'])
    audit.record(action='auth.2fa_disable', actor=user, target=user, request=request)
    return {'enabled': False}


def two_factor_challenge(user: User) -> dict:
    """Loginda parol to'g'ri, lekin 2FA yoqilgan: SMS kod yuboriladi va `challenge_token` qaytadi (tokenlar HALI berilmaydi)."""
    import secrets

    from django.core.cache import cache

    from . import otp

    challenge = secrets.token_urlsafe(24)
    otp.issue(scope='2fa-login', phone=user.phone or '', payload={'user': str(user.id)})
    cache.set(f'2fa:challenge:{challenge}', str(user.id), otp.CODE_TTL * 5)
    return {
        'two_factor_required': True, 'challenge_token': challenge, 'expires_in': otp.CODE_TTL,
        'retry_after': otp.RETRY_AFTER, 'phone_hint': otp.sms.mask_phone(user.phone or ''),
    }


def two_factor_login(*, challenge_token: str, code: str, request=None) -> User:
    """Loginning 2-bosqichi: kod to'g'ri bo'lsa foydalanuvchini qaytaradi (tokenni view beradi)."""
    from django.core.cache import cache

    from . import otp

    user_id = cache.get(f'2fa:challenge:{challenge_token}')
    user = User.objects.filter(pk=user_id, is_active=True).first() if user_id else None
    if user is None:
        raise ValidationError({'detail': _("Kirish so'rovi eskirgan. Qaytadan kiring.")})
    payload = otp.check(scope='2fa-login', phone=user.phone or '', code=code)
    if payload.get('user') != str(user.id):
        raise ValidationError({'detail': _("Kod noto'g'ri yoki muddati o'tgan")})
    cache.delete(f'2fa:challenge:{challenge_token}')
    return user


# ---------------------------------------------------------------------------
# Email va telefonni kod bilan tasdiqlash
# ---------------------------------------------------------------------------
def send_email_code(*, user: User) -> dict:
    from . import otp

    if not user.email:
        raise ValidationError({'detail': _("Avval profilda email manzilingizni kiriting.")})
    if user.email_verified:
        raise ValidationError({'detail': _('Email allaqachon tasdiqlangan.')})
    return otp.issue_email(scope='email-verify', email=user.email, payload={'user': str(user.id), 'email': user.email})


def verify_email(*, user: User, code: str, request=None) -> dict:
    from . import otp

    payload = otp.check_email(scope='email-verify', email=user.email or '', code=code)
    if payload.get('user') != str(user.id) or payload.get('email') != user.email:
        raise ValidationError({'detail': _("Kod noto'g'ri yoki muddati o'tgan")})
    user.email_verified = True
    user.save(update_fields=['email_verified'])
    audit.record(action='auth.email_verified', actor=user, target=user, request=request)
    return {'verified': True}


def send_phone_code(*, user: User) -> dict:
    from . import otp

    if not user.phone:
        raise ValidationError({'detail': _("Avval profilda telefon raqamingizni kiriting.")})
    if user.phone_verified:
        raise ValidationError({'detail': _('Telefon allaqachon tasdiqlangan.')})
    return otp.issue(scope='phone-verify', phone=user.phone, payload={'user': str(user.id), 'phone': user.phone})


def verify_phone(*, user: User, code: str, request=None) -> dict:
    from . import otp

    payload = otp.check(scope='phone-verify', phone=user.phone or '', code=code)
    if payload.get('user') != str(user.id) or payload.get('phone') != user.phone:
        raise ValidationError({'detail': _("Kod noto'g'ri yoki muddati o'tgan")})
    user.phone_verified = True
    user.phone_verified_at = timezone.now()
    user.save(update_fields=['phone_verified', 'phone_verified_at'])
    audit.record(action='auth.phone_verified', actor=user, target=user, request=request)
    return {'verified': True}


PHONE_TOKEN_TTL = 30 * 60


def _clean_phone_input(phone) -> str:
    from .serializers import clean_phone

    value = clean_phone(phone)
    if not value:
        raise ValidationError({'phone': _('Telefon raqamini kiriting.')})
    return value


def register_phone_request(*, phone: str) -> dict:
    """Ro'yxatdan o'tishdan OLDIN raqamga SMS kod yuboradi (5 xonali, 120 s; qayta yuborish — `retry_after`)."""
    from apps.core.sms import normalize_phone

    from . import otp

    phone = _clean_phone_input(phone)
    return otp.issue(scope='register-phone', phone=phone, payload={'phone': normalize_phone(phone)})


def register_phone_verify(*, phone: str, code: str) -> dict:
    """Kod to'g'ri bo'lsa `phone_token` qaytadi: uni `/auth/register/` ga `phone_token` sifatida yuboring (30 daqiqa, bir marta)."""
    from django.core.cache import cache

    from apps.core.sms import normalize_phone

    from . import otp

    phone = _clean_phone_input(phone)
    payload = otp.check(scope='register-phone', phone=phone, code=code)
    if payload.get('phone') != normalize_phone(phone):
        raise ValidationError({'detail': _("Kod noto'g'ri yoki muddati o'tgan")})
    token = secrets.token_urlsafe(24)
    cache.set(f'phone-token:{token}', normalize_phone(phone), PHONE_TOKEN_TTL)
    return {'phone_token': token, 'expires_in': PHONE_TOKEN_TTL}


def consume_phone_token(token: str, phone) -> bool:
    """Tokenni tekshirib BIR MARTA ishlatadi; ro'yxatdan o'tayotgan raqamga mos bo'lishi shart."""
    from django.core.cache import cache

    from apps.core.sms import normalize_phone

    stored = cache.get(f'phone-token:{token}')
    if not stored or stored != normalize_phone(phone or ''):
        raise ValidationError({'phone_token': _("Telefon tasdiqlash tokeni noto'g'ri yoki muddati o'tgan.")})
    cache.delete(f'phone-token:{token}')
    return True


def phone_change_request(*, user: User, phone: str) -> dict:
    """Raqamni o'zgartirish: YANGI raqamga kod yuboriladi (raqam tasdiqlangunga qadar eskisi o'zgarmaydi)."""
    from apps.core.sms import normalize_phone

    from . import otp

    phone = _clean_phone_input(phone)
    return otp.issue(scope='phone-change', phone=phone, payload={'user': str(user.id), 'phone': normalize_phone(phone)})


def phone_change_confirm(*, user: User, phone: str, code: str, request=None) -> User:
    from apps.core.sms import normalize_phone

    from . import otp

    phone = _clean_phone_input(phone)
    payload = otp.check(scope='phone-change', phone=phone, code=code)
    if payload.get('user') != str(user.id) or payload.get('phone') != normalize_phone(phone):
        raise ValidationError({'detail': _("Kod noto'g'ri yoki muddati o'tgan")})
    user.phone = phone
    user.phone_verified = True
    user.phone_verified_at = timezone.now()
    user.save(update_fields=['phone', 'phone_verified', 'phone_verified_at'])
    audit.record(action='auth.phone_changed', actor=user, target=user, request=request)
    return user


def me_stats(user: User) -> dict:
    """Profildagi "Guruh / O'quvchi / Tajriba" raqamlari."""
    from apps.lessons.models import Course, Enrollment

    approved = Enrollment.Status.APPROVED
    groups = students = 0
    if user.role == User.Role.TEACHER:
        groups = Course.objects.filter(teacher=user).count()
        students = Enrollment.objects.filter(
            course__teacher=user, status=approved,
        ).values('student').distinct().count()
    elif user.role == User.Role.STUDENT:
        groups = Enrollment.objects.filter(student=user, status=approved).count()
    return {'groups': groups, 'students': students, 'experience_years': user.experience_years}


def deactivate_account(*, user: User, password: str | None = None, request=None) -> None:
    """Akkauntni o'chirish = FAOLSIZLANTIRISH: kirib bo'lmaydi, hamma seans va tokenlar bekor, ma'lumotlar (kurslar,
    darslar, xabarlar, natijalar) saqlanadi — admin qayta yoqa oladi. O'qituvchining kurslari arxivlanadi (`is_active=False`).
    Admin akkauntlari o'zini o'chira olmaydi."""
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    from . import sessions

    if user.role in (User.Role.ADMIN, User.Role.SUPER_ADMIN) or user.is_superuser:
        raise PermissionDenied(_("Admin akkauntini o'zingiz o'chira olmaysiz."))
    if password is not None and not user.check_password(password):
        raise ValidationError({'password': _("Parol noto'g'ri.")})
    with transaction.atomic():
        user.is_active = False
        user.save(update_fields=['is_active'])
        if user.role == User.Role.TEACHER:
            from apps.lessons.models import Course

            Course.objects.filter(teacher=user).update(is_active=False)
        sessions.revoke_all(user)
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
        audit.record(action='account.deactivate', actor=user, target=user, request=request)


def _student_by_username(username: str) -> User:
    """Aniq moslik birinchi; topilmasa — katta/kichik harfdan qat'i nazar,
    FAQAT bitta o'quvchi mos kelsagina (mobil klaviatura birinchi harfni
    katta qilib yuborishi mumkin). `krv006` va `KRV006` ikkalasi ham mavjud
    bo'lsa va aniq mos kelmasa — qaysi bolaga ulanayotgani noaniq, rad etiladi."""
    username = username.strip()
    students = User.objects.filter(role=User.Role.STUDENT)
    exact = students.filter(username=username).first()
    if exact is not None:
        return exact
    loose = list(students.filter(username__iexact=username)[:2])
    if len(loose) == 1:
        return loose[0]
    raise NotFound(_("Bunday o'quvchi topilmadi."))


@transaction.atomic
def request_link(
    *, parent: User, invite_code: str | None = None, username: str | None = None, request=None,
) -> tuple[ParentChildLink, bool]:
    """O'quvchi logini (`username`) yoki taklif kodi (`invite_code`) orqali
    so'rov — o'quvchi tasdig'igacha PENDING (rozilik oqimi). Ikkalasidan
    biri yetarli; ikkalasi ham kelsa, login ustun."""
    if username:
        student = _student_by_username(username)
    else:
        try:
            student = User.objects.get(invite_code=(invite_code or '').strip().upper(), role=User.Role.STUDENT)
        except User.DoesNotExist:
            raise NotFound(_('Bunday taklif kodi topilmadi.'))

    link, created = ParentChildLink.objects.get_or_create(
        parent=parent, student=student,
        defaults={'status': ParentChildLink.Status.PENDING},
    )
    if not created and link.status == ParentChildLink.Status.DECLINED:
        link.status = ParentChildLink.Status.PENDING
        link.responded_at = None
        link.save(update_fields=['status', 'responded_at'])
    audit.record(action='link.request', actor=parent, target=link, request=request)
    return link, created


@transaction.atomic
def respond_link(*, student: User, link_id, action: str, request=None) -> ParentChildLink:
    """O'quvchi so'rovni tasdiqlaydi/rad etadi. Tasdiqlanganini keyin bekor qilishi ham mumkin."""
    try:
        link = ParentChildLink.objects.get(pk=link_id, student=student)
    except ParentChildLink.DoesNotExist:
        raise NotFound(_("So'rov topilmadi."))
    link.status = (
        ParentChildLink.Status.APPROVED if action == 'approve' else ParentChildLink.Status.DECLINED
    )
    link.responded_at = timezone.now()
    link.save(update_fields=['status', 'responded_at'])
    audit.record(action=f'link.{action}', actor=student, target=link, request=request)
    return link


@transaction.atomic
def set_consent(*, parent: User, student: User, kind: str, granted: bool, request=None) -> Consent:
    """Rozilik bayrog'i — faqat tasdiqlangan bog'lanishdagi ota-ona o'zgartira oladi."""
    is_linked = ParentChildLink.objects.filter(
        parent=parent, student=student, status=ParentChildLink.Status.APPROVED
    ).exists()
    if not is_linked:
        raise PermissionDenied(_("Bu o'quvchi sizga bog'lanmagan."))
    consent, _created = Consent.objects.update_or_create(
        student=student, kind=kind,
        defaults={'granted': granted, 'granted_by': parent},
    )
    audit.record(
        action='consent.set', actor=parent, target=consent,
        meta={'kind': kind, 'granted': granted}, request=request,
    )
    return consent


# ── Login jurnali: IP/qurilma o'zgarishini aniqlash (EduTech nazorat) ───────

def record_login(*, user: User, request) -> dict:
    """Har muvaffaqiyatli logindan keyin chaqiriladi (LoginView).

    Oxirgi login bilan solishtiradi: IP yoki qurilma (User-Agent) o'zgargan
    bo'lsa meta'da belgilanadi — ota-ona/admin "boshqa joydan kirildi"ni
    darhol ko'radi. Yozuv AuditLog'da (action='auth.login').
    """
    from apps.core.models import AuditLog

    user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:300]
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')

    last = (
        AuditLog.objects
        .filter(actor=user, action='auth.login')
        .order_by('-created_at')
        .first()
    )
    from .sessions import city_for_ip

    meta = {
        'user_agent': user_agent,
        'location': city_for_ip(ip) if ip else '',
        'first_login': last is None,
        'new_ip': bool(last and str(last.ip_address or '') != str(ip or '')),
        'new_device': bool(last and (last.meta or {}).get('user_agent', '') != user_agent),
    }
    audit.record(action='auth.login', actor=user, meta=meta, request=request)
    return meta


def login_history(*, viewer: User, student_id=None, limit: int = 50, request=None) -> list:
    """Login tarixi: o'zi uchun; ota-ona TASDIQLANGAN bolasi uchun ham."""
    from apps.core.models import AuditLog

    target = viewer
    if student_id:
        allowed = ParentChildLink.objects.filter(
            parent=viewer, student_id=student_id,
            status=ParentChildLink.Status.APPROVED,
        ).exists()
        if not allowed:
            raise PermissionDenied(_("Bu foydalanuvchi login tarixini ko'rish huquqingiz yo'q."))
        try:
            target = User.objects.get(pk=student_id)
        except (User.DoesNotExist, ValueError, TypeError):
            raise NotFound(_('Foydalanuvchi topilmadi.'))

    rows = (
        AuditLog.objects
        .filter(actor=target, action='auth.login')
        .order_by('-created_at')[:limit]
    )
    from .sessions import city_for_ip

    own = target == viewer and request is not None
    current_ua = (request.META.get('HTTP_USER_AGENT') or '')[:300] if own else None
    xff = request.META.get('HTTP_X_FORWARDED_FOR') if own else None
    current_ip = (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')) if own else None
    result, current_marked = [], False
    for r in rows:
        agent = (r.meta or {}).get('user_agent', '')
        is_current = False
        if own and not current_marked and agent == current_ua and str(r.ip_address or '') == str(current_ip or ''):
            is_current = current_marked = True  # shu qurilmadagi eng so'nggi kirish
        result.append({
            'at': r.created_at,
            'ip': r.ip_address,
            'user_agent': agent,
            'location': (r.meta or {}).get('location') or (city_for_ip(r.ip_address) if r.ip_address else '') or None,
            'new_ip': (r.meta or {}).get('new_ip', False),
            'new_device': (r.meta or {}).get('new_device', False),
            'is_current': is_current,
        })
    return result


def upload_certificate(*, teacher: User, file, title: str = '', issuer: str = '', issued_year=None) -> TeacherCertificate:
    certificate = TeacherCertificate.objects.create(
        teacher=teacher, file=file, title=title, issuer=issuer, issued_year=issued_year,
    )
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    for admin in User.objects.filter(role=User.Role.ADMIN, is_active=True):
        try:
            send_notification(
                sender=teacher, description=_("Yangi sertifikat tekshiruvni kutmoqda: %(name)s") % {
                    'name': teacher.get_full_name() or teacher.username},
                target_type=Notification.Target.USER, user_id=admin.id, kind='certificate_pending',
                link_type='certificate', link_id=str(certificate.id),
            )
        except Exception:  # noqa: BLE001 — bildirishnoma yuklashni to'xtatmasin
            pass
    return certificate


@transaction.atomic
def review_certificate(*, admin: User, certificate_id, verify: bool, reason: str = '', request=None) -> TeacherCertificate:
    """Admin sertifikatni tasdiqlaydi yoki rad etadi (sabab bilan); egasiga bildirishnoma boradi."""
    try:
        certificate = TeacherCertificate.objects.select_related('teacher').get(pk=certificate_id)
    except (TeacherCertificate.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Sertifikat topilmadi.'))
    reason = (reason or '').strip()
    if not verify and not reason:
        raise ValidationError({'reason': _('Rad etish sababini yozing.')})
    certificate.status = TeacherCertificate.Status.VERIFIED if verify else TeacherCertificate.Status.REJECTED
    certificate.reject_reason = '' if verify else reason[:1000]
    certificate.verified_at = timezone.now() if verify else None
    certificate.reviewed_by = admin
    certificate.save(update_fields=['status', 'reject_reason', 'verified_at', 'reviewed_by', 'updated_at'])
    audit.record(
        action='certificate.verify' if verify else 'certificate.reject', actor=admin, target=certificate,
        meta={'reason': reason} if not verify else {}, request=request,
    )

    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    text = (_('Sertifikatingiz tasdiqlandi: %(title)s') if verify else _('Sertifikatingiz rad etildi: %(title)s. Sabab: %(reason)s')) % {
        'title': certificate.title or certificate.file.name.split('/')[-1], 'reason': reason}
    transaction.on_commit(lambda: send_notification(
        sender=admin, description=text, target_type=Notification.Target.USER, user_id=certificate.teacher_id,
        kind='certificate_verified' if verify else 'certificate_rejected', link_type='certificate', link_id=str(certificate.id),
    ))
    return certificate


def delete_certificate(*, teacher: User, certificate_id) -> None:
    try:
        certificate = TeacherCertificate.objects.get(pk=certificate_id, teacher=teacher)
    except (TeacherCertificate.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Sertifikat topilmadi.'))
    certificate.file.delete(save=False)
    certificate.delete()


def switch_account(*, current_user: User, target_id, request=None) -> User:
    """Xuddi shu telefon raqamidagi boshqa rol-akkauntga (masalan
    o'qituvchi -> ota-ona) parolsiz o'tish — joriy sessiya autentifikatsiyasi
    yetarli, chunki ikkala akkaunt bir xil telefon raqami bilan ro'yxatdan
    o'tgan (`selectors.linked_accounts`). Login jurnaliga ham yoziladi —
    shundan keyingi "yangi qurilma/IP" solishtiruvlari to'g'ri ishlashi uchun."""
    from . import selectors

    if not selectors.linked_accounts(current_user).filter(pk=target_id).exists():
        raise PermissionDenied(_("Bu akkaunt sizga bog'lanmagan."))
    try:
        target = User.objects.get(pk=target_id, is_active=True)
    except (User.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Akkaunt topilmadi.'))
    audit.record(
        action='auth.switch', actor=current_user, target=target,
        meta={'from_user_id': str(current_user.pk)}, request=request,
    )
    record_login(user=target, request=request)
    return target


_SELF_SERVICE_ROLES = (User.Role.TEACHER, User.Role.PARENT, User.Role.STUDENT)


def _generate_unique_username(base: str) -> str:
    base = (base or 'user')[:140]
    candidate = base
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f'{base}{suffix}'
    return candidate


@transaction.atomic
def switch_or_provision_role(*, current_user: User, role: str, request=None) -> User:
    """Boshqa rolga (masalan o'qituvchi -> ota-ona) parolsiz o'tish — agar
    shu telefon raqamida o'sha rol hali mavjud bo'lmasa, ro'yxatdan
    o'tishsiz avtomatik yaratiladi ("ochiladi") va darhol shunga o'tiladi.

    XAVFSIZLIK: STUDENT hisob HECH QAYSI rolga o'ta olmaydi (hatto mavjud
    bo'lsa ham) — bu ochiq (hech qanday tasdiqsiz) ro'yxatdan o'tish yo'li,
    shuning uchun aks holda istalgan kishi o'quvchi sifatida ro'yxatdan
    o'tib, bir zumda o'qituvchi imkoniyatlariga "o'tib" olar edi."""
    if current_user.role == User.Role.STUDENT:
        raise PermissionDenied(_("O'quvchi hisobidan boshqa rolga o'tib bo'lmaydi."))
    if role not in _SELF_SERVICE_ROLES:
        raise ValidationError({'role': _("Noto'g'ri rol.")})
    if role == current_user.role:
        raise ValidationError({'role': _('Siz allaqachon shu roldasiz.')})
    if not current_user.phone:
        raise ValidationError({'role': _("Rol almashtirish uchun avval telefon raqamingizni kiriting.")})

    target = User.objects.filter(
        phone=current_user.phone, role=role,
    ).exclude(pk=current_user.pk).first()
    if target is not None and not target.is_active:
        raise PermissionDenied(_('Bu akkaunt faolsizlantirilgan.'))

    auto_provisioned = False
    if target is None:
        target = User(
            username=_generate_unique_username(f'{current_user.username}_{role}'),
            role=role,
            phone=current_user.phone,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
        )
        target.set_password(secrets.token_urlsafe(32))
        target.save()
        auto_provisioned = True
        audit.record(
            action='auth.role_auto_provisioned', actor=current_user, target=target,
            meta={'role': role}, request=request,
        )

    audit.record(
        action='auth.switch', actor=current_user, target=target,
        meta={'from_user_id': str(current_user.pk), 'auto_provisioned': auto_provisioned},
        request=request,
    )
    record_login(user=target, request=request)
    return target


def logout(*, user: User, refresh_token: str | None = None, device_id: str | None = None, request=None) -> None:
    """Chiqish — berilgan refresh token bekor qilinadi (blacklist), qayta
    ishlatib bo'lmaydi. Access token o'z muddati tugaguncha amal qiladi
    (JWT'ning odatiy xatti-harakati); boshqa qurilmalardagi sessiyalarga
    ta'sir qilmaydi. `device_id` berilsa — mobil push qurilma yozuvi ham
    o'chiriladi (chiqib ketgan foydalanuvchiga push kelib turmasin;
    PUSH-BACKEND.md 2.2 — `push/device/` DELETE'ga qo'shimcha himoya)."""
    if refresh_token:
        from . import sessions

        sessions.revoke_by_token(refresh_token)
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            RefreshToken(refresh_token).blacklist()
        except Exception:  # noqa: BLE001 — token allaqachon yaroqsiz/eskirgan bo'lishi mumkin
            pass

    if device_id:
        from apps.notifications.services import remove_push_device
        remove_push_device(user=user, device_id=device_id)

    audit.record(action='auth.logout', actor=user, target=user, request=request)
