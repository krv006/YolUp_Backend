"""Email yuborish (tasdiqlash kodi, bildirishnoma xatlari). SMTP `EMAIL_HOST` va hamkasblari orqali sozlanadi.

`EMAIL_HOST` bo'sh bo'lsa email ULANMAGAN: `send_email` 503 (`email_not_configured`) beradi — kod yuborilgan deb yolg'on
aytilmaydi. Testlarda Django o'zining xotira backend'idan foydalanadi (`django.core.mail.outbox`).
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException

logger = logging.getLogger('apps')


class EmailNotConfigured(APIException):
    status_code = 503
    default_code = 'email_not_configured'
    default_detail = _("Email xizmati hali ulanmagan. Keyinroq urinib ko'ring yoki administrator bilan bog'laning.")


class EmailFailed(APIException):
    status_code = 502
    default_code = 'email_failed'
    default_detail = _("Xat yuborib bo'lmadi. Birozdan keyin qayta urinib ko'ring.")


def configured() -> bool:
    return bool(getattr(settings, 'EMAIL_HOST', '')) or 'locmem' in getattr(settings, 'EMAIL_BACKEND', '')


def send_email(to: str, subject: str, body: str) -> None:
    """Bitta manzilga oddiy matnli xat. Ulanmagan — `EmailNotConfigured`; SMTP xatosi — `EmailFailed`."""
    if not configured():
        raise EmailNotConfigured()
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
    except Exception:  # noqa: BLE001 — tarmoq/SMTP xatosi mijozga ichki tafsilotsiz
        logger.exception('Xat yuborilmadi (%s)', to)
        raise EmailFailed() from None


def code_text(code: str) -> tuple:
    """(mavzu, matn) — tasdiqlash kodi xati."""
    return (
        'YolUp tasdiqlash kodi',
        f'Tasdiqlash kodingiz: {code}\n\nKod 2 daqiqa amal qiladi. Uni hech kimga bermang.\n\n— YolUp',
    )
