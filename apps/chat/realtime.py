"""Chat real-time broadcast — service qatlamidan channel layer'ga.

send_message (REST yoki WS orqali) har safar shu yerdan o'tadi: xabar
saqlangach xonaning WebSocket guruhiga tarqatiladi. Channel layer
sozlanmagan bo'lsa (masalan, ba'zi testlar) jimgina o'tkazib yuboriladi.
"""
import json

from asgiref.sync import async_to_sync
from rest_framework.renderers import JSONRenderer


def broadcast_message(message) -> None:
    from channels.layers import get_channel_layer

    from .consumers import group_name
    from .serializers import MessageSerializer

    layer = get_channel_layer()
    if layer is None:
        return
    # UUID/datetime kabi qiymatlarni toza JSON'ga aylantiramiz —
    # channel layer payload'i serializable bo'lishi shart.
    # Chaqiruvchi doim sync kontekstda (view yoki database_sync_to_async
    # worker thread'i) — async_to_sync xavfsiz.
    payload = json.loads(JSONRenderer().render(MessageSerializer(message).data))
    async_to_sync(layer.group_send)(group_name(message.room_id), {
        'type': 'chat.message',
        'message': payload,
    })


def _course_room_group(course_id):
    from .consumers import group_name
    from .models import ChatRoom

    room = ChatRoom.objects.filter(kind=ChatRoom.Kind.COURSE, course_id=course_id).first()
    return group_name(room.id) if room else None


def broadcast_lesson_live(lesson) -> None:
    """Dars LIVE bo'lganda — guruh chatga "jonli dars boshlandi" signali
    (Telegram uslubidagi guruh video chat chizig'i uchun)."""
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    group = _course_room_group(lesson.course_id)
    if group is None:
        return
    async_to_sync(layer.group_send)(group, {
        'type': 'chat.lesson_live',
        'lesson': {'id': str(lesson.id), 'title': lesson.course.title, 'room_name': lesson.room_name},
    })


def broadcast_lesson_ended(lesson) -> None:
    """Dars tugaganda — guruh chatga "jonli dars tugadi" signali."""
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    group = _course_room_group(lesson.course_id)
    if group is None:
        return
    async_to_sync(layer.group_send)(group, {
        'type': 'chat.lesson_ended',
        'lesson_id': str(lesson.id),
    })


def broadcast_member_removed(course_id, student_id) -> None:
    """O'quvchi kursdan (unenroll) chiqarilganda — guruh chatga signal.

    Ruxsat (can_read/can_write) faqat YANGI so'rovda tekshiriladi; o'quvchining
    ALLAQACHON ochiq WebSocket ulanishi buni o'zi bilmaydi. Shu event orqali
    consumer o'zini "bu men emasmi?" deb tekshirib, agar o'zi bo'lsa — ulanishni
    o'zi yopadi (apps.chat.consumers.ChatConsumer.chat_member_removed).
    """
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    group = _course_room_group(course_id)
    if group is None:
        return
    async_to_sync(layer.group_send)(group, {
        'type': 'chat.member_removed',
        'user_id': str(student_id),
    })
