"""Kim kimga yoza oladi (shaxsiy chat) va "odamlar" qidiruvi — bitta joyda (2026-11-10).

Kelishilgan qoidalar:
  - O'qituvchi -> O'Z o'quvchisi / o'z o'quvchisining tasdiqlangan ota-onasi: so'rovsiz ("write", chat darhol ACTIVE).
  - O'quvchi -> ISTALGAN o'qituvchi: so'rov ("request"), o'qituvchi accept/block qiladi.
  - Ota-ona -> farzandining o'qituvchilari: so'rov ("request").
  - Qolgan hamma juftliklar (o'quvchi<->o'quvchi, o'quvchi<->ota-ona, ...): "none".
  - Spam deb belgilangan chat ("spam" holati): har ikki tomon uchun "none" — faqat admin qayta ochadi.

DIRECT xonada `teacher` — o'qituvchi, `student` — O'QITUVCHIDAN BOSHQA ishtirokchi (o'quvchi YOKI ota-ona):
juftlik unique va mavjud kod (`rooms_for`, `member_ids`, `title_for`) o'zgarishsiz ishlaydi.
"""
from django.db.models import Q

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Enrollment

from .models import ChatRoom

WRITE, REQUEST, NONE = 'write', 'request', 'none'


def own_student_ids(teacher: User) -> set:
    return set(
        Enrollment.objects.filter(course__teacher=teacher, status=Enrollment.Status.APPROVED)
        .values_list('student_id', flat=True)
    )


def own_parent_ids(teacher: User) -> set:
    return set(
        ParentChildLink.objects.filter(
            status=ParentChildLink.Status.APPROVED, student_id__in=own_student_ids(teacher),
        ).values_list('parent_id', flat=True)
    )


def children_teacher_ids(parent: User) -> set:
    """Ota-onaning tasdiqlangan farzandlari o'qiydigan guruhlarning o'qituvchilari."""
    children = ParentChildLink.objects.filter(
        parent=parent, status=ParentChildLink.Status.APPROVED,
    ).values('student_id')
    return set(
        Enrollment.objects.filter(student_id__in=children, status=Enrollment.Status.APPROVED)
        .values_list('course__teacher_id', flat=True)
    )


def _room_between(teacher_id, participant_id):
    return ChatRoom.objects.filter(kind=ChatRoom.Kind.DIRECT, teacher_id=teacher_id, student_id=participant_id).first()


def can_message(viewer: User, other: User, room: ChatRoom | None = None) -> str:
    """`write` | `request` | `none` — yakka juftlik uchun."""
    return _policy(viewer, other, room, _context(viewer))


def _context(viewer: User) -> dict:
    if viewer.role == User.Role.TEACHER:
        return {'students': own_student_ids(viewer), 'parents': own_parent_ids(viewer)}
    if viewer.role == User.Role.PARENT:
        return {'teachers': children_teacher_ids(viewer)}
    return {}


def _policy(viewer: User, other: User, room: ChatRoom | None, ctx: dict) -> str:
    if viewer.pk == other.pk or not other.is_active:
        return NONE
    if room is not None and room.direct_status == ChatRoom.DirectStatus.SPAM:
        return NONE
    if viewer.role == User.Role.TEACHER:
        if other.role == User.Role.STUDENT and other.pk in ctx['students']:
            return WRITE
        if other.role == User.Role.PARENT and other.pk in ctx['parents']:
            return WRITE
        return NONE
    if other.role != User.Role.TEACHER:
        return NONE
    if viewer.role == User.Role.PARENT and other.pk not in ctx['teachers']:
        return NONE
    if viewer.role not in (User.Role.STUDENT, User.Role.PARENT):
        return NONE
    if room is not None and room.direct_status == ChatRoom.DirectStatus.ACTIVE:
        return WRITE
    return REQUEST


def _rooms_for_people(viewer: User, people: list) -> dict:
    """{boshqa_odam_id: xona} — bitta so'rovda."""
    ids = [p.pk for p in people]
    if viewer.role == User.Role.TEACHER:
        rooms = ChatRoom.objects.filter(kind=ChatRoom.Kind.DIRECT, teacher=viewer, student_id__in=ids)
        return {r.student_id: r for r in rooms}
    rooms = ChatRoom.objects.filter(kind=ChatRoom.Kind.DIRECT, student=viewer, teacher_id__in=ids)
    return {r.teacher_id: r for r in rooms}


def people_row(person: User, room: ChatRoom | None, can: str) -> dict:
    """Begona odam uchun faqat ism, username, avatar, rol (telefon va boshqa ma'lumot CHIQMAYDI)."""
    return {
        'id': str(person.id), 'name': person.get_full_name() or person.username, 'username': person.username,
        'role': person.role, 'avatar': person.avatar.url if person.avatar else None,
        'room_id': str(room.id) if room and room.direct_status != ChatRoom.DirectStatus.BLOCKED else None,
        'direct_status': room.direct_status if room else None,
        'can_message': can,
    }


def people_search(viewer: User, q: str) -> list:
    """Odamlar qidiruvi (o'quvchi/ota-ona/o'qituvchi uchun).

    - O'qituvchi: o'z guruhlaridagi o'quvchilar (kutayotganlari ham) va ularning ota-onalari — ism, @username yoki telefon.
    - O'quvchi: HAMMANI topadi (o'qituvchilar, o'quvchilar, ota-onalar), lekin yoza oladigani faqat o'qituvchi (so'rov bilan).
    - Ota-ona: kamida farzandining o'qituvchilari.
    Har natijada `role`, `room_id`, `direct_status`, `can_message`.
    """
    if viewer.role == User.Role.TEACHER:
        from apps.accounts.selectors import teacher_people_search

        found = teacher_people_search(viewer, q)
        people = {str(u.pk): u for u in User.objects.filter(pk__in=[row['id'] for row in found])}
        ordered = [people[row['id']] for row in found if row['id'] in people]
    else:
        match = Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        qs = User.objects.filter(is_active=True).exclude(pk=viewer.pk).filter(match)
        if viewer.role == User.Role.PARENT:
            qs = qs.filter(role=User.Role.TEACHER, pk__in=children_teacher_ids(viewer))
        else:
            qs = qs.filter(role__in=(User.Role.TEACHER, User.Role.STUDENT, User.Role.PARENT))
            qs = qs.exclude(role=User.Role.TEACHER, is_approved=False)
        ordered = list(qs.order_by('first_name', 'last_name', 'username')[:20])
    rooms = _rooms_for_people(viewer, ordered)
    ctx = _context(viewer)
    return [people_row(p, rooms.get(p.pk), _policy(viewer, p, rooms.get(p.pk), ctx)) for p in ordered]
