"""Shaxsiy chatda spam/shikoyat (2026-11-10).

Barcha rollar (o'qituvchi, o'quvchi, ota-ona) shaxsiy chatdagi suhbatdoshini sababi bilan belgilay oladi. Belgilangach chat
DARHOL `spam` holatiga o'tadi (belgilangan odam belgilaganga yoza olmaydi — `can_write` faqat ACTIVE'da ochiq), shikoyat
admin panelga tushadi va adminlarga bildirishnoma boradi. Admin: tasdiqlaydi (chat bloklangan qoladi), rad etadi (chat avvalgi
holatiga qaytadi) yoki istalgan paytda chatni qayta ochadi (unblock).
"""
import logging

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core import audit

from . import selectors, services
from .models import ChatRoom, SpamReport

logger = logging.getLogger('apps')

MAX_COMMENT = 1000


def _person(user: User) -> dict:
    return {'id': str(user.id), 'name': user.get_full_name() or user.username, 'username': user.username, 'role': user.role}


def report_row(report: SpamReport, with_messages: bool = False) -> dict:
    row = {
        'id': str(report.id), 'room_id': str(report.room_id), 'reporter': _person(report.reporter),
        'reported': _person(report.reported), 'reason': report.reason, 'comment': report.comment, 'status': report.status,
        'room_status': report.room.direct_status, 'created_at': report.created_at,
        'handled_by': _person(report.handled_by) if report.handled_by else None, 'handled_at': report.handled_at,
    }
    if with_messages:  # admin shikoyatni ko'rayotganda suhbatning oxirgi xabarlari
        row['recent_messages'] = [
            {'sender_id': str(m.sender_id), 'text': m.text[:300], 'created_at': m.created_at}
            for m in report.room.messages.filter(deleted_at__isnull=True).order_by('-created_at')[:10]
        ][::-1]
    return row


@transaction.atomic
def report_room(*, user: User, room_id, reason: str, comment: str = '', request=None) -> SpamReport:
    room = services._readable_room(user, room_id)
    if room.kind != ChatRoom.Kind.DIRECT:
        raise ValidationError({'detail': _("Faqat shaxsiy suhbatni spam deb belgilash mumkin.")})
    if reason not in SpamReport.Reason.values:
        raise ValidationError({'reason': _("insult, harassment, advertising yoki other bo'lishi kerak.")})
    comment = (comment or '').strip()[:MAX_COMMENT]
    other_id = room.student_id if user.id == room.teacher_id else room.teacher_id
    existing = SpamReport.objects.filter(
        reporter=user, room=room, status=SpamReport.Status.OPEN,
    ).select_related('reporter', 'reported', 'room').first()
    if existing is not None:
        return existing  # takroriy bosish yangi shikoyat yaratmaydi
    report = SpamReport.objects.create(
        reporter=user, reported_id=other_id, room=room, reason=reason, comment=comment,
        room_status_before=room.direct_status if room.direct_status != ChatRoom.DirectStatus.SPAM else ChatRoom.DirectStatus.ACTIVE,
    )
    room.direct_status = ChatRoom.DirectStatus.SPAM
    room.save(update_fields=['direct_status', 'updated_at'])
    audit.record(action='chat.spam_report', actor=user, target=room, meta={'reason': reason}, request=request)
    transaction.on_commit(lambda: _notify_admins(report, request))
    report = SpamReport.objects.select_related('reporter', 'reported', 'room', 'handled_by').get(pk=report.pk)
    return report


def _notify_admins(report: SpamReport, request=None) -> None:
    """Xato shikoyatni to'xtatmasin."""
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import send_notification

        text = _("Chatda shikoyat: %(reporter)s -> %(reported)s (%(reason)s).") % {
            'reporter': report.reporter.get_full_name() or report.reporter.username,
            'reported': report.reported.get_full_name() or report.reported.username,
            'reason': report.get_reason_display(),
        }
        for admin_id in User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]).values_list('id', flat=True):
            send_notification(
                sender=report.reporter, description=text, target_type=Notification.Target.USER, user_id=admin_id,
                kind='spam_report', link_type='spam_report', link_id=str(report.id), request=request,
            )
    except Exception:  # noqa: BLE001
        logger.exception('spam report notification failed')


# ── Admin ──────────────────────────────────────────────────────────────────

def reports_for_admin(status: str | None):
    qs = SpamReport.objects.select_related('reporter', 'reported', 'room', 'handled_by')
    if status:
        if status not in SpamReport.Status.values:
            raise ValidationError({'status': _("open, resolved yoki dismissed.")})
        qs = qs.filter(status=status)
    return qs


def _get_report(report_id) -> SpamReport:
    try:
        return SpamReport.objects.select_related('reporter', 'reported', 'room', 'handled_by').get(pk=report_id)
    except (SpamReport.DoesNotExist, *services.BAD_ID):
        raise NotFound(_('Shikoyat topilmadi.'))


def _restore_room(report: SpamReport) -> None:
    room = report.room
    if room.direct_status == ChatRoom.DirectStatus.SPAM:
        room.direct_status = report.room_status_before or ChatRoom.DirectStatus.ACTIVE
        room.save(update_fields=['direct_status', 'updated_at'])


@transaction.atomic
def handle_report(*, admin: User, report_id, action: str, request=None) -> SpamReport:
    """`resolve` — shikoyat to'g'ri, chat bloklangan qoladi; `dismiss` — shikoyat asossiz, chat qayta ochiladi;
    `unblock` — (tasdiqlanganidan keyin ham) chatni qayta ochish."""
    if action not in ('resolve', 'dismiss', 'unblock'):
        raise ValidationError({'action': _("resolve, dismiss yoki unblock.")})
    report = _get_report(report_id)
    if action == 'resolve':
        report.status = SpamReport.Status.RESOLVED
    elif action == 'dismiss':
        report.status = SpamReport.Status.DISMISSED
        _restore_room(report)
    else:
        _restore_room(report)
        if report.status == SpamReport.Status.OPEN:
            report.status = SpamReport.Status.DISMISSED
    report.handled_by, report.handled_at = admin, timezone.now()
    report.save(update_fields=['status', 'handled_by', 'handled_at', 'updated_at'])
    audit.record(action=f'chat.spam_{action}', actor=admin, target=report.room, request=request)
    report.room.refresh_from_db()
    return report
