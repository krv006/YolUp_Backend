"""Kanallar (2026-11-10): Telegram kanaliga o'xshash. Egasi — o'qituvchi (post yozadi); a'zolar — uning o'quvchilari va ularning
tasdiqlangan ota-onalari (o'qiydi va har post ostida izoh qoldiradi).

A'zolar kanal ochilganda ro'yxat sifatida olinadi (guruh yoki alohida o'quvchilar tanlanadi) — guruhga KEYIN qo'shilgan o'quvchi
avtomatik qo'shilmaydi, o'qituvchi uni `members` orqali qo'shadi (egasi bilan kelishilmagan ochiq savol — hozircha shunday).
"""
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import ParentChildLink, User
from apps.core import audit
from apps.lessons.models import Course, Enrollment

from . import contacts, services
from .models import ChatRoom, RoomMember

MAX_TITLE = 200


def _own_channel(teacher: User, room_id) -> ChatRoom:
    room = services._get_room(room_id)
    if room.kind != ChatRoom.Kind.CHANNEL or room.teacher_id != teacher.id:
        raise PermissionDenied(_("Bu kanal sizniki emas."))
    return room


def _ids(raw, field: str) -> list:
    if raw in (None, ''):
        return []
    if not isinstance(raw, (list, tuple)) or not all(services._is_uuid(i) for i in raw):
        raise ValidationError({field: _("UUID'lar ro'yxati kerak.")})
    return list(dict.fromkeys(str(i) for i in raw))


def _resolve_students(teacher: User, course_ids, student_ids) -> set:
    """Tanlangan guruhlarning tasdiqlangan o'quvchilari + alohida tanlanganlar (faqat o'qituvchining o'z o'quvchilari)."""
    course_ids, student_ids = _ids(course_ids, 'course_ids'), _ids(student_ids, 'student_ids')
    students = set()
    if course_ids:
        own = Course.objects.filter(pk__in=course_ids, teacher=teacher).values_list('pk', flat=True)
        if len(set(str(i) for i in own)) != len(course_ids):
            raise PermissionDenied(_("Ro'yxatda sizniki bo'lmagan guruh bor."))
        students |= {str(i) for i in Enrollment.objects.filter(
            course_id__in=course_ids, status=Enrollment.Status.APPROVED,
        ).values_list('student_id', flat=True)}
    if student_ids:
        mine = {str(i) for i in contacts.own_student_ids(teacher)}
        if set(student_ids) - mine:
            raise PermissionDenied(_("Ro'yxatda sizning o'quvchingiz bo'lmagan foydalanuvchi bor."))
        students |= set(student_ids)
    return students


def _add_members(room: ChatRoom, student_ids: set) -> int:
    """O'quvchilarni va ularning tasdiqlangan ota-onalarini qo'shadi. Qaytaradi: nechta yangi a'zo qo'shildi."""
    if not student_ids:
        return 0
    parents = {str(i) for i in ParentChildLink.objects.filter(
        student_id__in=student_ids, status=ParentChildLink.Status.APPROVED,
    ).values_list('parent_id', flat=True)}
    existing = {str(i) for i in RoomMember.objects.filter(room=room).values_list('user_id', flat=True)}
    rows = [
        RoomMember(room=room, user_id=uid, source=RoomMember.Source.STUDENT) for uid in student_ids if uid not in existing
    ] + [
        RoomMember(room=room, user_id=uid, source=RoomMember.Source.PARENT)
        for uid in parents if uid not in existing and uid not in student_ids
    ]
    RoomMember.objects.bulk_create(rows, ignore_conflicts=True)
    return len(rows)


@transaction.atomic
def create_channel(*, teacher: User, title, description='', course_ids=None, student_ids=None, request=None) -> ChatRoom:
    if teacher.role != User.Role.TEACHER:
        raise PermissionDenied(_("Kanalni faqat o'qituvchi ochadi."))
    title = (title or '').strip()
    if not title or len(title) > MAX_TITLE:
        raise ValidationError({'title': _("Kanal nomi kerak (1-200 belgi).")})
    students = _resolve_students(teacher, course_ids, student_ids)
    room = ChatRoom.objects.create(
        kind=ChatRoom.Kind.CHANNEL, teacher=teacher, title=title, description=(description or '').strip(),
    )
    _add_members(room, students)
    audit.record(action='chat.channel_create', actor=teacher, target=room, request=request)
    return room


@transaction.atomic
def update_channel(*, teacher: User, room_id, title=None, description=None, request=None) -> ChatRoom:
    room = _own_channel(teacher, room_id)
    if title is not None:
        title = str(title).strip()
        if not title or len(title) > MAX_TITLE:
            raise ValidationError({'title': _("Kanal nomi kerak (1-200 belgi).")})
        room.title = title
    if description is not None:
        room.description = str(description).strip()
    room.save(update_fields=['title', 'description', 'updated_at'])
    audit.record(action='chat.channel_update', actor=teacher, target=room, request=request)
    return room


@transaction.atomic
def delete_channel(*, teacher: User, room_id, request=None) -> None:
    room = _own_channel(teacher, room_id)
    audit.record(action='chat.channel_delete', actor=teacher, target=room, request=request)
    room.delete()


@transaction.atomic
def add_members(*, teacher: User, room_id, course_ids=None, student_ids=None, request=None) -> dict:
    room = _own_channel(teacher, room_id)
    added = _add_members(room, _resolve_students(teacher, course_ids, student_ids))
    audit.record(action='chat.channel_members_add', actor=teacher, target=room, meta={'added': added}, request=request)
    return {'added': added}


@transaction.atomic
def remove_member(*, teacher: User, room_id, user_id, request=None) -> None:
    """A'zoni chiqaradi. O'quvchi chiqsa, ota-onasi faqat kanalda boshqa farzandi qolmasa chiqadi."""
    room = _own_channel(teacher, room_id)
    member = RoomMember.objects.filter(room=room, user_id=user_id if services._is_uuid(user_id) else None).first()
    if member is None:
        raise NotFound(_("A'zo topilmadi."))
    member.delete()
    if member.source == RoomMember.Source.STUDENT:
        student_ids = set(RoomMember.objects.filter(room=room, source=RoomMember.Source.STUDENT).values_list('user_id', flat=True))
        orphan_parents = RoomMember.objects.filter(room=room, source=RoomMember.Source.PARENT).exclude(
            user_id__in=ParentChildLink.objects.filter(
                status=ParentChildLink.Status.APPROVED, student_id__in=student_ids,
            ).values('parent_id'),
        )
        orphan_parents.delete()
    audit.record(action='chat.channel_member_remove', actor=teacher, target=room, request=request)
