"""Bildirishnoma service layer — admin xabar yuborishi, o'qildi belgilash."""
import json
import logging
import re

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.models import User
from apps.core import audit

from . import realtime
from .models import Notification, NotificationRecipient, PushSubscription

logger = logging.getLogger('apps')

# Rich editor (CKEditor) HTML'iga ruxsat etilgan teglar — XSS'dan himoya.
# Rasm/fayl yo'q (FRD: hozircha faqat formatlangan matn) — shuning uchun
# img/src kabi tashqi resurs teglariga ruxsat berilmaydi.
_ALLOWED_TAGS = {
    'p', 'br', 'b', 'strong', 'i', 'em', 'u', 's', 'strike',
    'h2', 'h3', 'ul', 'ol', 'li', 'blockquote', 'a',
}
_ALLOWED_ATTRS = {'a': {'href'}}


def sanitize_html(html: str) -> str:
    """Admin yozgan HTML'ni tozalaydi. nh3 (Rust ammonia) bo'lsa u bilan,
    bo'lmasa konservativ regex fallback (homework/services.py bilan bir xil yondashuv)."""
    html = (html or '').strip()
    if not html:
        return ''
    try:
        import nh3
        return nh3.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS)
    except ImportError:
        return re.sub(r'<[^>]+>', '', html)


@transaction.atomic
def send_notification(
    *, sender: User, description: str, target_type: str, user_id=None, request=None,
    link_type: str = '', link_id: str = '', kind: str = '',
) -> Notification:
    if target_type not in Notification.Target.values:
        raise ValidationError({'target_type': _("'user' yoki 'all' bo'lishi kerak.")})
    clean = sanitize_html(description)
    if not clean:
        raise ValidationError({'description': _("Xabar matni bo'sh bo'lishi mumkin emas.")})

    if target_type == Notification.Target.USER:
        try:
            recipients = [User.objects.get(pk=user_id)]
        except (User.DoesNotExist, ValueError, TypeError):
            raise NotFound(_('Foydalanuvchi topilmadi.'))
    else:
        recipients = list(User.objects.exclude(pk=sender.pk))

    notification = Notification.objects.create(
        sender=sender, description=clean, target_type=target_type,
        link_type=link_type, link_id=link_id, kind=kind,
    )
    NotificationRecipient.objects.bulk_create([
        NotificationRecipient(notification=notification, user=u) for u in recipients
    ])

    transaction.on_commit(lambda: realtime.broadcast_notification(notification, recipients))
    transaction.on_commit(lambda: send_web_push(notification, recipients))
    audit.record(
        action='notification.send', actor=sender, target=notification,
        meta={'target_type': target_type, 'recipient_count': len(recipients)}, request=request,
    )
    return notification


def mark_read(*, user: User, notification_id) -> NotificationRecipient:
    try:
        recipient = NotificationRecipient.objects.get(notification_id=notification_id, user=user)
    except (NotificationRecipient.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Bildirishnoma topilmadi.'))
    if recipient.read_at is None:
        recipient.read_at = timezone.now()
        recipient.save(update_fields=['read_at'])
    return recipient


# ── Web Push — ilova/tab yopiq bo'lganda ham bildirishnoma ─────────────────

def save_push_subscription(*, user: User, endpoint: str, p256dh: str, auth: str) -> PushSubscription:
    """Brauzer `PushManager.subscribe()` natijasini saqlaydi. `endpoint`
    UNIQUE — bitta brauzer nusxasi qayta obuna bo'lsa, eski qatorning o'zi
    yangilanadi (boshqa foydalanuvchiga o'tib ketmasin — masalan umumiy
    kompyuterda chiqib, boshqa hisobga kirilsa)."""
    sub, _created = PushSubscription.objects.update_or_create(
        endpoint=endpoint, defaults={'user': user, 'p256dh': p256dh, 'auth': auth},
    )
    return sub


def remove_push_subscription(*, user: User, endpoint: str) -> bool:
    deleted, _ = PushSubscription.objects.filter(user=user, endpoint=endpoint).delete()
    return bool(deleted)


def send_web_push(notification: Notification, recipients: list[User]) -> None:
    """Har qabul qiluvchining barcha obuna qilingan qurilmalariga push
    yuboradi — ilova/tab yopiq bo'lsa ham operatsion tizim darajasida
    bildirishnoma chiqishi uchun. Best-effort: bitta obuna muvaffaqiyatsiz
    bo'lsa ham (masalan brauzer obunani bekor qilgan — 404/410), boshqalarga
    ta'sir qilmaydi; eskirgan obuna avtomatik o'chiriladi."""
    from pywebpush import WebPushException, webpush

    user_ids = [u.id for u in recipients]
    subs = PushSubscription.objects.filter(user_id__in=user_ids)
    if not subs:
        return
    payload = json.dumps({
        'title': 'Fokus',
        'body': notification.description[:200],
        'kind': notification.kind,
        'link_type': notification.link_type,
        'link_id': notification.link_id,
    })
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={'sub': settings.VAPID_CLAIM_EMAIL},
            )
        except WebPushException as exc:
            status_code = getattr(exc.response, 'status_code', None)
            if status_code in (404, 410):
                # Brauzer obunani bekor qilgan (masalan foydalanuvchi ruxsatni
                # olib tashlagan) — eskirgan qatorni o'chirib qo'yamiz.
                sub.delete()
            else:
                logger.warning('web push failed (%s): %s', status_code, exc)
        except Exception:  # noqa: BLE001 — push umuman ishlamasa ham notification o'zi saqlanib qolgan
            logger.exception('web push failed')
