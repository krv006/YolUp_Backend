"""Speaking club (2026-11-10): o'qituvchi ochadigan, o'z chati va jonli mashg'ulotlari bor guruh.

Club = `Course(kind='club')`: chat xonasi (`ensure_course_room`), jonli darslar (`/lessons/` da `course=<club id>`), davomat va
yozuvlar tayyor infratuzilmadan ishlaydi. O'qituvchi turli guruhlaridan o'quvchilarni (yoki butun guruhni) qo'shadi — qo'shilganlar
DARHOL a'zo bo'ladi (taklifni qabul qilish shart emas) va ularga bildirishnoma boradi.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core import audit

from .models import Course, Enrollment


def _own_club(teacher: User, club_id) -> Course:
    try:
        club = Course.objects.get(pk=club_id, kind=Course.Kind.CLUB)
    except (Course.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        raise NotFound(_('Klub topilmadi.'))
    if club.teacher_id != teacher.id:
        raise PermissionDenied(_("Bu klub sizniki emas."))
    return club


def _students(teacher: User, course_ids, student_ids) -> set:
    from apps.chat import channel_service

    return channel_service._resolve_students(teacher, course_ids, student_ids)


def _enroll(club: Course, student_ids: set) -> list:
    """Yangi a'zolarni darhol APPROVED qiladi. Qaytaradi: yangi qo'shilgan o'quvchilar."""
    existing = {str(i) for i in Enrollment.objects.filter(course=club, student_id__in=student_ids).values_list('student_id', flat=True)}
    fresh = [sid for sid in student_ids if sid not in existing]
    Enrollment.objects.bulk_create(
        [Enrollment(course=club, student_id=sid, status=Enrollment.Status.APPROVED) for sid in fresh], ignore_conflicts=True,
    )
    # kutayotgan/rad etilgan yozuv bo'lsa — ham tasdiqlanadi (o'qituvchi o'zi qo'shyapti)
    Enrollment.objects.filter(course=club, student_id__in=student_ids).exclude(status=Enrollment.Status.APPROVED).update(
        status=Enrollment.Status.APPROVED,
    )
    return fresh


def _notify_added(teacher: User, club: Course, student_ids: list) -> None:
    if not student_ids:
        return
    import logging

    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    try:
        send_notification(
            sender=teacher, description=_("Siz «%(club)s» klubiga qo'shildingiz.") % {'club': club.title},
            target_type=Notification.Target.USERS, user_ids=list(student_ids), kind='club_added',
            link_type='club', link_id=str(club.id),
        )
    except Exception:  # noqa: BLE001
        logging.getLogger('apps').exception('club_added notification failed')


@transaction.atomic
def create_club(*, teacher: User, title, description='', subject='', course_ids=None, student_ids=None, request=None) -> Course:
    from . import services

    if teacher.role != User.Role.TEACHER:
        raise PermissionDenied(_("Klubni faqat o'qituvchi ochadi."))
    title = (title or '').strip()
    if not title or len(title) > 200:
        raise ValidationError({'title': _("Klub nomi kerak (1-200 belgi).")})
    if subject and subject not in Course.Subject.values:
        raise ValidationError({'subject': _("Noma'lum fan.")})
    members = _students(teacher, course_ids, student_ids)
    club = services.create_course(
        teacher=teacher, request=request, title=title, description=(description or '').strip(),
        subject=subject or Course.Subject.OTHER, kind=Course.Kind.CLUB,
    )
    added = _enroll(club, members)
    transaction.on_commit(lambda: _notify_added(teacher, club, added))
    return club


@transaction.atomic
def update_club(*, teacher: User, club_id, title=None, description=None, request=None) -> Course:
    club = _own_club(teacher, club_id)
    fields = []
    if title is not None:
        title = str(title).strip()
        if not title or len(title) > 200:
            raise ValidationError({'title': _("Klub nomi kerak (1-200 belgi).")})
        club.title = title
        fields.append('title')
    if description is not None:
        club.description = str(description).strip()
        fields.append('description')
    if fields:
        club.save(update_fields=[*fields, 'updated_at'])
    audit.record(action='club.update', actor=teacher, target=club, request=request)
    return club


@transaction.atomic
def delete_club(*, teacher: User, club_id, request=None) -> None:
    club = _own_club(teacher, club_id)
    audit.record(action='club.delete', actor=teacher, target=club, request=request)
    club.delete()  # SoftDeleteModel


@transaction.atomic
def add_members(*, teacher: User, club_id, course_ids=None, student_ids=None, request=None) -> dict:
    club = _own_club(teacher, club_id)
    added = _enroll(club, _students(teacher, course_ids, student_ids))
    transaction.on_commit(lambda: _notify_added(teacher, club, added))
    audit.record(action='club.members_add', actor=teacher, target=club, meta={'added': len(added)}, request=request)
    return {'added': len(added)}


@transaction.atomic
def remove_member(*, teacher: User, club_id, student_id, request=None) -> None:
    club = _own_club(teacher, club_id)
    deleted, _details = Enrollment.objects.filter(course=club, student_id=student_id).delete()
    if not deleted:
        raise NotFound(_("A'zo topilmadi."))
    audit.record(action='club.member_remove', actor=teacher, target=club, request=request)
