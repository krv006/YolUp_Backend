"""Kanallar (2026-11-10): Telegram kanaliga o'xshash. Egasi — o'qituvchi (post yozadi); a'zolar — uning o'quvchilari va ularning
tasdiqlangan ota-onalari (o'qiydi va har post ostida izoh qoldiradi).

Guruh tanlanib (`course_ids`) ochilgan/qo'shilgan bo'lsa kanal shu guruhga BOG'LANADI (`ChannelCourse`): guruhga keyin qo'shilgan tasdiqlangan
o'quvchi (va uning tasdiqlangan ota-onalari) avtomatik a'zo bo'ladi, guruhdan chiqqani chiqadi (apps/chat/signals.py). `student_ids` bilan
alohida tanlangan o'quvchi guruhdan chiqsa ham qoladi (`RoomMember.explicit`).
"""
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import ParentChildLink, User
from apps.core import audit
from apps.lessons.models import Course, Enrollment

from . import contacts, services
from .models import ChannelCourse, ChatRoom, RoomMember

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


def _resolve_split(teacher: User, course_ids, student_ids) -> tuple:
    """(barcha o'quvchilar, o'qituvchi alohida tanlaganlari, toza `course_ids`)."""
    course_ids, student_ids = _ids(course_ids, 'course_ids'), _ids(student_ids, 'student_ids')
    return _resolve_students(teacher, course_ids, student_ids), set(student_ids), course_ids


def _add_members(room: ChatRoom, student_ids: set, explicit: set = frozenset()) -> int:
    """O'quvchilarni va ularning tasdiqlangan ota-onalarini qo'shadi. `explicit` — o'qituvchi alohida tanlagan o'quvchilar (guruhdan
    chiqsa ham kanalda qoladi). Qaytaradi: nechta yangi a'zo qo'shildi."""
    if not student_ids:
        return 0
    parents = {str(i) for i in ParentChildLink.objects.filter(
        student_id__in=student_ids, status=ParentChildLink.Status.APPROVED,
    ).values_list('parent_id', flat=True)}
    existing = {str(i) for i in RoomMember.objects.filter(room=room).values_list('user_id', flat=True)}
    rows = [
        RoomMember(room=room, user_id=uid, source=RoomMember.Source.STUDENT, explicit=uid in explicit)
        for uid in student_ids if uid not in existing
    ] + [
        RoomMember(room=room, user_id=uid, source=RoomMember.Source.PARENT, explicit=False)
        for uid in parents if uid not in existing and uid not in student_ids
    ]
    RoomMember.objects.bulk_create(rows, ignore_conflicts=True)
    keep = set(student_ids) & explicit & existing  # allaqachon a'zo, endi alohida tanlangan: guruhdan chiqsa ham qolsin
    if keep:
        RoomMember.objects.filter(room=room, user_id__in=keep).update(explicit=True)
    return len(rows)


def _link_courses(room: ChatRoom, course_ids: list) -> None:
    for course_id in course_ids:
        ChannelCourse.objects.get_or_create(room=room, course_id=course_id)


def _drop_orphan_parents(room: ChatRoom) -> None:
    """Kanalda farzandi (tasdiqlangan bog'lanish bilan) qolmagan ota-onalarni chiqaradi."""
    student_ids = set(RoomMember.objects.filter(room=room, source=RoomMember.Source.STUDENT).values_list('user_id', flat=True))
    RoomMember.objects.filter(room=room, source=RoomMember.Source.PARENT).exclude(
        user_id__in=ParentChildLink.objects.filter(
            status=ParentChildLink.Status.APPROVED, student_id__in=student_ids,
        ).values('parent_id'),
    ).delete()


# ── Guruh/bog'lanish o'zgarganda kanalni sinxronlash (signals orqali, apps/chat/signals.py) ─────────────

def sync_student_joined(course_id, student_id) -> None:
    """Guruhga tasdiqlangan o'quvchi qo'shildi: shu guruhga bog'langan kanallarga (va ota-onalari) avtomatik a'zo."""
    for link in ChannelCourse.objects.filter(course_id=course_id).select_related('room'):
        _add_members(link.room, {str(student_id)})


def sync_student_left(course_id, student_id) -> None:
    """O'quvchi guruhdan chiqdi (yoki tasdiqlanmay qoldi): kanalda faqat shu guruh orqali bo'lsa — chiqadi (ota-onasi ham, boshqa
    farzandi qolmagan bo'lsa)."""
    for link in ChannelCourse.objects.filter(course_id=course_id).select_related('room'):
        member = RoomMember.objects.filter(room=link.room, user_id=student_id, source=RoomMember.Source.STUDENT).first()
        if member is None or member.explicit:
            continue
        other = ChannelCourse.objects.filter(room=link.room).exclude(course_id=course_id).values('course_id')
        if Enrollment.objects.filter(course_id__in=other, student_id=student_id, status=Enrollment.Status.APPROVED).exists():
            continue  # kanalga bog'langan boshqa guruhda hamon o'qiyapti
        member.delete()
        _drop_orphan_parents(link.room)


def sync_parent_linked(parent_id, student_id) -> None:
    """Ota-ona farzandi bilan bog'lanishi tasdiqlandi: farzandi a'zo bo'lgan kanallarga qo'shiladi."""
    rooms = RoomMember.objects.filter(user_id=student_id, source=RoomMember.Source.STUDENT).values_list('room_id', flat=True)
    for room in ChatRoom.objects.filter(pk__in=rooms, kind=ChatRoom.Kind.CHANNEL):
        RoomMember.objects.get_or_create(
            room=room, user_id=parent_id, defaults={'source': RoomMember.Source.PARENT, 'explicit': False},
        )


def sync_parent_unlinked(parent_id) -> None:
    for member in RoomMember.objects.filter(user_id=parent_id, source=RoomMember.Source.PARENT).select_related('room'):
        _drop_orphan_parents(member.room)


@transaction.atomic
def create_channel(*, teacher: User, title, description='', course_ids=None, student_ids=None, request=None) -> ChatRoom:
    if teacher.role != User.Role.TEACHER:
        raise PermissionDenied(_("Kanalni faqat o'qituvchi ochadi."))
    title = (title or '').strip()
    if not title or len(title) > MAX_TITLE:
        raise ValidationError({'title': _("Kanal nomi kerak (1-200 belgi).")})
    students, explicit, linked = _resolve_split(teacher, course_ids, student_ids)
    room = ChatRoom.objects.create(
        kind=ChatRoom.Kind.CHANNEL, teacher=teacher, title=title, description=(description or '').strip(),
    )
    _link_courses(room, linked)
    _add_members(room, students, explicit)
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
    students, explicit, linked = _resolve_split(teacher, course_ids, student_ids)
    _link_courses(room, linked)
    added = _add_members(room, students, explicit)
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
        _drop_orphan_parents(room)
    audit.record(action='chat.channel_member_remove', actor=teacher, target=room, request=request)


@transaction.atomic
def unlink_course(*, teacher: User, room_id, course_id, request=None) -> int:
    """Guruhni kanaldan ajratadi: faqat shu guruh orqali kelgan (alohida tanlanmagan) o'quvchilar va ota-onalari chiqariladi.
    Qaytaradi: chiqarilgan a'zolar soni."""
    room = _own_channel(teacher, room_id)
    link = ChannelCourse.objects.filter(room=room, course_id=course_id if services._is_uuid(course_id) else None).first()
    if link is None:
        raise NotFound(_("Bu guruh kanalga bog'lanmagan."))
    link.delete()
    before = RoomMember.objects.filter(room=room).count()
    remaining = ChannelCourse.objects.filter(room=room).values('course_id')
    still = Enrollment.objects.filter(course_id__in=remaining, status=Enrollment.Status.APPROVED).values('student_id')
    RoomMember.objects.filter(room=room, source=RoomMember.Source.STUDENT, explicit=False).exclude(user_id__in=still).delete()
    _drop_orphan_parents(room)
    removed = before - RoomMember.objects.filter(room=room).count()
    audit.record(action='chat.channel_course_unlink', actor=teacher, target=room, meta={'removed': removed}, request=request)
    return removed
