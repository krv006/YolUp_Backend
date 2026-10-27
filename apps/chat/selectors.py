"""Chat selectors — o'qish yo'li: kim qaysi xonani ko'radi."""
from datetime import datetime, timezone as dt_timezone

from django.db.models import Count, DateTimeField, Exists, IntegerField, OuterRef, Prefetch, Q, Subquery, Value
from django.db.models.functions import Coalesce

from apps.accounts.models import User
from apps.lessons.models import Enrollment

from .models import ChatRoom, Message, MessageReaction, RoomRead


_EPOCH = datetime(1970, 1, 1, tzinfo=dt_timezone.utc)


def with_room_stats(qs, user: User):
    """Xonalar ro'yxati uchun o'qilmaganlar soni, birinchi o'qilmagan xabar, belgilanish (@) va oxirgi o'qilgan xabar —
    bitta SO'ROVDA (avval har xona uchun 4-5 ta alohida so'rov ketardi). Mantiq `ChatRoomSerializer._unread_qs` bilan bir xil."""
    read_at = Subquery(RoomRead.objects.filter(room=OuterRef('pk'), user=user).values('last_read_at')[:1], output_field=DateTimeField())
    qs = qs.annotate(room_read_at=read_at)
    unread = (
        Message.objects.filter(room=OuterRef('pk'), deleted_at__isnull=True)
        .exclude(sender=user).exclude(hides__user=user)
        .filter(created_at__gt=Coalesce(OuterRef('room_read_at'), Value(_EPOCH, output_field=DateTimeField())))
    )
    last_read = Message.objects.filter(
        room=OuterRef('pk'), deleted_at__isnull=True, created_at__lte=OuterRef('room_read_at'),
    ).order_by('-created_at').values('id')[:1]
    return qs.annotate(
        room_unread=Coalesce(Subquery(unread.order_by().values('room').annotate(c=Count('pk')).values('c'), output_field=IntegerField()), 0),
        room_first_unread=Subquery(unread.order_by('created_at').values('id')[:1]),
        room_has_mention=Exists(unread.filter(mentions=user)),
        room_last_read_id=Subquery(last_read),
    )


def rooms_for(user: User):
    """Foydalanuvchi a'zo bo'lgan xonalar.

    - Kurs guruhi: o'qituvchi (kurs egasi) yoki tasdiqlangan o'quvchi.
    - Direct: taraflardan biri (pending/blocked ham ro'yxatda ko'rinadi —
      holatini ko'rsatish uchun; yozish esa faqat ACTIVE'da).
    """
    approved_courses = Enrollment.objects.filter(
        student=user, status=Enrollment.Status.APPROVED,
    ).values('course_id')
    return (
        ChatRoom.objects
        .filter(
            Q(kind=ChatRoom.Kind.COURSE)
            & (Q(course__teacher=user) | Q(course_id__in=approved_courses))
            | Q(kind=ChatRoom.Kind.DIRECT) & (Q(teacher=user) | Q(student=user))
        )
        .select_related('course', 'course__teacher', 'teacher', 'student')
        .distinct()
    )


def can_read(user: User, room: ChatRoom) -> bool:
    if room.kind == ChatRoom.Kind.DIRECT:
        return user.id in (room.teacher_id, room.student_id)
    if room.course.teacher_id == user.id:
        return True
    # Ro'yxatda bitta xona uchun can_write/capabilities/can_pin shuni qayta-qayta so'raydi — natijani xona ob'ektida eslab qolamiz
    memo = room.__dict__.setdefault('_can_read_memo', {})
    if user.id not in memo:
        memo[user.id] = Enrollment.objects.filter(
            course=room.course, student=user, status=Enrollment.Status.APPROVED,
        ).exists()
    return memo[user.id]


def can_write(user: User, room: ChatRoom) -> bool:
    if not can_read(user, room):
        return False
    if room.kind == ChatRoom.Kind.DIRECT:
        return room.direct_status == ChatRoom.DirectStatus.ACTIVE
    if room.announcement_only and not is_room_teacher(user, room):
        return False  # e'lon rejimi: guruhga faqat o'qituvchi yozadi
    return True


def is_room_teacher(user: User, room: ChatRoom) -> bool:
    """Kurs guruhining o'qituvchisi (guruhni boshqarish huquqi shunda)."""
    return room.kind == ChatRoom.Kind.COURSE and room.course.teacher_id == user.id


def can_pin(user: User, room: ChatRoom) -> bool:
    """Qadash huquqi: kurs guruhida faqat o'qituvchi, direct chatda ikkala tomon."""
    if room.kind == ChatRoom.Kind.COURSE:
        return is_room_teacher(user, room)
    return can_read(user, room)


def capabilities(user: User, room: ChatRoom, message: Message) -> dict:
    """Shu foydalanuvchi bu xabar bilan nima qila oladi (frontend tugmalarni shunga qarab yashiradi).
    `delete` — "men uchun o'chirish" (har doim mumkin), `delete_everyone` — hamma uchun (muallif yoki guruh o'qituvchisi)."""
    user_message = message.kind == Message.Kind.USER
    own = message.sender_id == user.id
    return {
        'edit': own and user_message and message.message_type in (Message.Type.TEXT, Message.Type.FILE, Message.Type.IMAGE, Message.Type.VIDEO),
        'delete': True,
        'delete_everyone': own or is_room_teacher(user, room),
        'pin': can_pin(user, room),
        'react': True,
        'forward': user_message and message.message_type != Message.Type.ASSIGNMENT,
    }


def visible_messages(room: ChatRoom, user: User):
    """Foydalanuvchi ko'radigan xabarlar: hamma uchun o'chirilganlar va "men uchun o'chirilgan"lar chiqarilgan."""
    return (
        room.messages.filter(deleted_at__isnull=True)
        .exclude(hides__user=user)
        .select_related('sender', 'reply_to', 'reply_to__sender', 'assignment', 'forwarded_from_author')
        .prefetch_related('mentions', 'files', Prefetch('reactions', queryset=MessageReaction.objects.only('message_id', 'user_id', 'emoji')))
    )


def hidden_filter(user: User):
    """Ro'yxatdan yashirilgan suhbatlar: foydalanuvchi "o'chirgan" va shundan keyin yangi xabar kelmagan."""
    newer = Message.objects.filter(
        room=OuterRef('room'), created_at__gt=OuterRef('hidden_at'), deleted_at__isnull=True,
    )
    return RoomRead.objects.filter(user=user, hidden_at__isnull=False).annotate(
        has_new=Exists(newer),
    ).filter(has_new=False)


def member_ids(room: ChatRoom) -> list:
    """Xonaning barcha a'zolari (kurs guruhi: o'qituvchi + tasdiqlangan o'quvchilar; direct: ikki tomon)."""
    if room.kind == ChatRoom.Kind.DIRECT:
        return [i for i in (room.teacher_id, room.student_id) if i]
    students = Enrollment.objects.filter(
        course_id=room.course_id, status=Enrollment.Status.APPROVED,
    ).values_list('student_id', flat=True)
    return [room.course.teacher_id, *students]
