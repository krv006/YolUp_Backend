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

from .models import Consent, ParentChildLink, TeacherCertificate, User


def _notify_admins_of_pending_teacher(teacher: User, request=None) -> None:
    """Yangi o'qituvchi ro'yxatdan o'tganda BARCHA adminlarga bildirishnoma —
    aks holda admin tasdiqlash kerakligini bilishi uchun ro'yxatni o'zi
    tekshirib turishga majbur bo'lardi."""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    full_name = teacher.get_full_name() or teacher.username
    admin_ids = User.objects.filter(
        role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN],
    ).values_list('id', flat=True)
    for admin_id in admin_ids:
        send_notification(
            sender=teacher,
            description=_("Yangi o'qituvchi ro'yxatdan o'tdi: %(name)s (@%(username)s) — tasdiqlash kerak.") % {
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
def register_user(*, username: str, password: str, role: str, request=None, **extra) -> User:
    if role not in (User.Role.TEACHER, User.Role.PARENT, User.Role.STUDENT):
        raise ValidationError({'role': _("Faqat o'qituvchi, ota-ona yoki o'quvchi ro'yxatdan o'ta oladi.")})
    user = User(username=username, role=role, **extra)
    if role == User.Role.TEACHER:
        # Kira oladi, lekin admin tasdiqlamaguncha kurs/dars ochish kabi
        # amallarga ruxsati yo'q (RequirePerm — apps.core.permissions).
        user.is_approved = False
    user.set_password(password)
    user.save()
    audit.record(action='auth.register', actor=user, target=user, meta={'role': role}, request=request)
    if role == User.Role.TEACHER:
        transaction.on_commit(lambda: _notify_admins_of_pending_teacher(user, request=request))
    return user


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
def create_child(*, creator: User, username: str, password: str, request=None, **extra) -> User:
    """O'quvchi hisobini yaratadi — ota-ona yoki o'qituvchi.

    Ota-ona yaratsa — ParentChildLink darhol APPROVED (FRD: auth.child_create).
    O'qituvchi yaratsa — bog'lanish yaratilmaydi (o'qituvchi ota-ona emas);
    o'quvchiga invite_code beriladi, haqiqiy ota-ona keyin shu kod orqali
    bog'lanishi mumkin. O'qituvchi bolani alohida enroll/ orqali kursiga
    biriktiradi.
    """
    child = User(username=username, role=User.Role.STUDENT, **extra)
    child.set_password(password)
    child.save()
    if creator.role == User.Role.PARENT:
        ParentChildLink.objects.create(
            parent=creator, student=child, status=ParentChildLink.Status.APPROVED,
            responded_at=timezone.now(),
        )
    audit.record(action='child.create', actor=creator, target=child, request=request)
    return child


@transaction.atomic
def request_link(*, parent: User, invite_code: str, request=None) -> tuple[ParentChildLink, bool]:
    """Taklif-kod orqali so'rov — o'quvchi tasdig'igacha PENDING (rozilik oqimi)."""
    try:
        student = User.objects.get(invite_code=invite_code.strip().upper(), role=User.Role.STUDENT)
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
    meta = {
        'user_agent': user_agent,
        'first_login': last is None,
        'new_ip': bool(last and str(last.ip_address or '') != str(ip or '')),
        'new_device': bool(last and (last.meta or {}).get('user_agent', '') != user_agent),
    }
    audit.record(action='auth.login', actor=user, meta=meta, request=request)
    return meta


def login_history(*, viewer: User, student_id=None, limit: int = 50) -> list:
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
    return [{
        'at': r.created_at,
        'ip': r.ip_address,
        'user_agent': (r.meta or {}).get('user_agent', ''),
        'new_ip': (r.meta or {}).get('new_ip', False),
        'new_device': (r.meta or {}).get('new_device', False),
    } for r in rows]


def upload_certificate(*, teacher: User, file, title: str = '') -> TeacherCertificate:
    return TeacherCertificate.objects.create(teacher=teacher, file=file, title=title)


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

    auto_provisioned = False
    if target is None:
        target = User(
            username=_generate_unique_username(f'{current_user.username}_{role}'),
            role=role,
            phone=current_user.phone,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
        )
        if role == User.Role.TEACHER:
            # Oddiy ro'yxatdan o'tish bilan bir xil qoida — admin
            # tasdiqlamaguncha kurs/dars ochilmaydi.
            target.is_approved = False
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


def logout(*, user: User, refresh_token: str | None = None, request=None) -> None:
    """Chiqish — berilgan refresh token bekor qilinadi (blacklist), qayta
    ishlatib bo'lmaydi. Access token o'z muddati tugaguncha amal qiladi
    (JWT'ning odatiy xatti-harakati); boshqa qurilmalardagi sessiyalarga
    ta'sir qilmaydi."""
    if refresh_token:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            RefreshToken(refresh_token).blacklist()
        except Exception:  # noqa: BLE001 — token allaqachon yaroqsiz/eskirgan bo'lishi mumkin
            pass

    audit.record(action='auth.logout', actor=user, target=user, request=request)
