"""Chat xabarlari uchun push (brauzer va mobil) — faqat hozir chatda BO'LMAGAN a'zolarga.

Qoidalar:
  - yuboruvchining o'ziga, hozir chat WebSocket'i ochiq a'zolarga (ular xabarni jonli ko'radi) push yo'q;
  - `notify_messages=false` bo'lgan yoki shu suhbatni ovozsiz qilgan (`muted`, muddati o'tmagan) a'zoga yo'q;
  - @eslatilganga alohida `mention` bildirishnomasi boradi — bu yerdan ikkinchi push yuborilmaydi;
  - bir a'zoga bir suhbatdan 30 soniyada ko'pi bilan bitta push (xabarlar ketma-ket kelsa to'planib qolmasin);
  - push bildirishnomalar ro'yxatiga yozilmaydi (bazada `Notification` qatori yaratilmaydi) — faqat qurilmaga boradi.
Hammasi fonda bajariladi; xato xabar yuborishni hech qachon buzmaydi.
"""
import logging
import uuid

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.core import background

from . import presence, selectors
from .models import ChatRoom, Message, RoomRead

logger = logging.getLogger('apps')

THROTTLE_SECONDS = 30
MAX_RECIPIENTS = 300

_PLACEHOLDERS = {
    Message.Type.VOICE: '🎤 Ovozli xabar',
    Message.Type.IMAGE: '📷 Rasm',
    Message.Type.VIDEO: '🎬 Video',
    Message.Type.FILE: '📎 Fayl',
}


def schedule(message: Message) -> None:
    """Xabar saqlangandan keyin chaqiriladi (`transaction.on_commit`)."""
    background.run(_send, message.id)


def _body(message: Message, sender_name: str, group: bool) -> str:
    text = (message.text or '').strip().replace('\n', ' ')
    snippet = text[:120] or _PLACEHOLDERS.get(message.message_type, '📎 Fayl')
    return f'{sender_name}: {snippet}' if group else snippet


def recipients_for(message: Message) -> list:
    """Push olishi kerak bo'lgan a'zolar (yuqoridagi qoidalar bo'yicha), throttle'siz."""
    room = message.room
    ids = {str(i) for i in selectors.member_ids(room)} - {str(message.sender_id)}
    if not ids:
        return []
    ids -= presence.online_ids(ids)
    ids -= {str(u.id) for u in message.mentions.all()}
    if not ids:
        return []
    now = timezone.now()
    muted = RoomRead.objects.filter(room=room, user_id__in=ids, muted=True).filter(
        Q(muted_until__isnull=True) | Q(muted_until__gt=now),
    ).values_list('user_id', flat=True)
    ids -= {str(i) for i in muted}
    return list(User.objects.filter(pk__in=ids, is_active=True, notify_messages=True)[:MAX_RECIPIENTS])


def _send(message_id) -> None:
    from apps.notifications.models import Notification
    from apps.notifications.services import send_mobile_push, send_web_push

    message = (
        Message.objects.select_related('room', 'room__course', 'sender')
        .filter(pk=message_id, deleted_at__isnull=True, kind=Message.Kind.USER).first()
    )
    if message is None:
        return
    room = message.room
    users = [
        u for u in recipients_for(message)
        if cache.add(f'chat:push:{room.id}:{u.id}', 1, THROTTLE_SECONDS)
    ]
    if not users:
        return
    sender = message.sender
    sender_name = (sender.get_full_name() or sender.username) if sender else 'Chat'
    group = room.kind == ChatRoom.Kind.COURSE
    title = room.course.title if group else sender_name
    note = Notification(
        id=uuid.uuid4(), description=_body(message, sender_name, group), kind='chat_message',
        link_type='chat_room', link_id=str(room.id),
    )
    send_web_push(note, users, title=title)
    send_mobile_push(note, users, title=title)
