"""Chat service layer — yozuvchi biznes-logika."""
import json
import logging
import uuid
from datetime import datetime, timezone as dt_timezone

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core import audit
from apps.lessons.models import Course, Enrollment

from . import attachments, presence, realtime, selectors
from .models import ChatRoom, Message, MessageHide, MessageReaction, PinnedMessage, RoomRead
from .serializers import member_row

logger = logging.getLogger('apps')

# UUID bo'lmagan id Django'da ValidationError beradi (500 emas, 400/404 qaytishi uchun)
BAD_ID = (ValueError, TypeError, DjangoValidationError)
MAX_TEXT = 4000
MAX_FORWARD = 50
MAX_BULK_DELETE = 100
MAX_EMOJIS_PER_MESSAGE = 20
MAX_VOICE_SECONDS = 5 * 60
MAX_MENTIONS = 20
MAX_PINS = 20
MAX_TARGET_ROOMS = 10
SEARCH_LIMIT = 100
EPOCH = datetime(1970, 1, 1, tzinfo=dt_timezone.utc)


def ensure_course_room(course: Course) -> ChatRoom:
    """Kurs uchun guruh chat — yo'q bo'lsa yaratadi (kurs yaratilganda chaqiriladi)."""
    room, _created = ChatRoom.objects.get_or_create(
        kind=ChatRoom.Kind.COURSE, course=course,
    )
    return room


def _get_room(room_id) -> ChatRoom:
    try:
        return ChatRoom.objects.select_related('course', 'teacher', 'student').get(pk=room_id)
    except (ChatRoom.DoesNotExist, *BAD_ID):
        raise NotFound(_('Chat topilmadi.'))


def _readable_room(user: User, room_id) -> ChatRoom:
    room = _get_room(room_id)
    if not selectors.can_read(user, room):
        raise PermissionDenied(_("Bu chatga kirish huquqingiz yo'q."))
    return room


def _get_message(user: User, message_id) -> Message:
    """Xabar — foydalanuvchi o'qiy oladigan va unga ko'rinadigan (hamma/men uchun o'chirilmagan) bo'lsa."""
    try:
        message = Message.objects.select_related('room', 'room__course', 'sender').get(pk=message_id)
    except (Message.DoesNotExist, *BAD_ID):
        raise NotFound(_('Xabar topilmadi.'))
    if not selectors.can_read(user, message.room):
        raise PermissionDenied(_("Bu chatga kirish huquqingiz yo'q."))
    if message.deleted_at is not None or message.hides.filter(user=user).exists():
        raise NotFound(_('Xabar topilmadi.'))
    return message


def _check_text(text: str) -> str:
    text = (text or '').strip()
    if len(text) > MAX_TEXT:
        raise ValidationError({'text': _('Xabar juda uzun (maks. 4000 belgi).')})
    return text


def _find_reply(room: ChatRoom, reply_to_id):
    if not reply_to_id:
        return None
    try:
        return Message.objects.get(pk=reply_to_id, room=room, deleted_at__isnull=True)
    except (Message.DoesNotExist, *BAD_ID):
        raise ValidationError({'reply_to_id': _('Javob beriladigan xabar topilmadi.')}) from None


def send_message_ex(
    *, user: User, room_id, text='', reply_to_id=None, client_message_id='', upload=None,
    message_type='', duration=None, waveform=None, mentions=None,
) -> tuple:
    """Xabar yuboradi. Qaytaradi: (xabar, yangi_yaratildimi). Bir xil `client_message_id` bilan qayta kelsa —
    avval yaratilgan xabar qaytadi (yangi_yaratildimi=False) va qayta tarqatilmaydi."""
    room = _get_room(room_id)
    if not selectors.can_write(user, room):
        if room.kind == ChatRoom.Kind.DIRECT and room.direct_status != ChatRoom.DirectStatus.ACTIVE:
            raise PermissionDenied(_("Chat hali ochiq emas (so'rov qabul qilinmagan yoki bloklangan)."))
        if room.kind == ChatRoom.Kind.COURSE and room.announcement_only and selectors.can_read(user, room):
            raise PermissionDenied(_("Bu guruhda faqat o'qituvchi yozadi (e'lon rejimi)."))
        raise PermissionDenied(_("Bu chatga yozish huquqingiz yo'q."))

    client_message_id = str(client_message_id or '').strip()
    if len(client_message_id) > 64:
        raise ValidationError({'client_message_id': _('Juda uzun (maks. 64 belgi).')})
    if client_message_id:
        existing = Message.objects.filter(room=room, sender=user, client_message_id=client_message_id).first()
        if existing is not None:
            return existing, False

    text = _check_text(text)
    reply = _find_reply(room, reply_to_id)
    mentioned = _find_mentions(room, user, mentions)
    fields = {}
    if upload is not None:
        fields = attachments.inspect_upload(upload, message_type)
        if fields['message_type'] == Message.Type.VOICE:
            try:
                seconds = int(duration)
            except (TypeError, ValueError):
                seconds = 0
            if not 0 < seconds <= MAX_VOICE_SECONDS:
                raise ValidationError({'duration': _("Ovozli xabar uchun davomiylik shart (1 soniyadan 5 daqiqagacha).")})
            fields['duration'] = seconds
            fields['waveform'] = attachments.clean_waveform(waveform)
    elif message_type == Message.Type.VOICE:
        raise ValidationError({'file': _('Ovozli xabar uchun audio fayl kerak.')})
    if not text and upload is None:
        raise ValidationError({'text': _("Xabar bo'sh bo'lishi mumkin emas.")})

    try:
        with transaction.atomic():
            message = Message.objects.create(
                room=room, sender=user, text=text, reply_to=reply, client_message_id=client_message_id,
                file=upload if upload is not None else '', **fields,
            )
            # xona ro'yxatda tepaga chiqsin
            room.save(update_fields=['updated_at'])
            if mentioned:
                message.mentions.set(mentioned)
            # Real-time: tranzaksiya muvaffaqiyatli yopilgandan KEYIN tarqatamiz (aks holda ulangan
            # client hali bazada yo'q xabarni ko'rishi mumkin)
            transaction.on_commit(lambda: realtime.broadcast_message(message))
            if mentioned:
                transaction.on_commit(lambda: _notify_mentions(message, mentioned))
    except IntegrityError:
        # bir vaqtda kelgan ikkita bir xil `client_message_id` — g'olibini qaytaramiz
        existing = Message.objects.filter(room=room, sender=user, client_message_id=client_message_id).first()
        if existing is None:
            raise
        return existing, False
    return message, True


def _find_mentions(room: ChatRoom, sender: User, raw) -> list:
    """`mentions` — eslatilgan foydalanuvchi id'lari (ro'yxat yoki JSON matn). Faqat chat a'zolari qoladi,
    o'zini eslatish e'tiborsiz; noto'g'ri id — 400."""
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = [raw]
    if not isinstance(raw, (list, tuple)):
        raise ValidationError({'mentions': _("Ro'yxat bo'lishi kerak.")})
    ids = []
    for item in raw:
        try:
            ids.append(str(uuid.UUID(str(item))))
        except (ValueError, TypeError, AttributeError):
            raise ValidationError({'mentions': _("Noto'g'ri foydalanuvchi id'si.")}) from None
    ids = list(dict.fromkeys(ids))
    if len(ids) > MAX_MENTIONS:
        raise ValidationError({'mentions': _("Bir xabarda ko'pi bilan 20 ta eslatma.")})
    members = {str(i) for i in selectors.member_ids(room)}
    return list(User.objects.filter(pk__in=[i for i in ids if i in members]).exclude(pk=sender.pk))


def _notify_mentions(message: Message, users: list) -> None:
    """Eslatilganga bildirishnoma (push ham) — ovozsiz qilingan chatda ham boradi. Xato xabar yuborishni buzmaydi."""
    from apps.notifications.models import Notification
    from apps.notifications.services import send_notification

    sender = message.sender
    name = sender.get_full_name() or sender.username
    snippet = (message.text or message.file_name)[:120]
    for user in users:
        try:
            send_notification(
                sender=sender, target_type=Notification.Target.USER, user_id=user.id, kind='mention',
                description=f'{name} sizni «{message.room.title_for(user)}» chatida eslatdi: {snippet}',
                link_type='chat_room', link_id=str(message.room_id),
            )
        except Exception:
            logger.exception('chat: eslatma bildirishnomasi yuborilmadi (message=%s, user=%s)', message.id, user.id)


def send_message(*, user: User, room_id, text='', **kwargs) -> Message:
    return send_message_ex(user=user, room_id=room_id, text=text, **kwargs)[0]


def post_assignment_card(assignment) -> Message | None:
    """Vazifa berilganda kurs guruhiga vazifa kartasi (`message_type=assignment`) tushadi. Xato bo'lsa vazifa
    berishni to'xtatmaydi."""
    try:
        room = ensure_course_room(assignment.course)
        message = Message.objects.create(
            room=room, sender=assignment.course.teacher, text=assignment.title,
            message_type=Message.Type.ASSIGNMENT, assignment=assignment,
        )
        room.save(update_fields=['updated_at'])
        transaction.on_commit(lambda: realtime.broadcast_message(message))
        return message
    except Exception:
        logger.exception('chat: vazifa kartasini yaratib bo\'lmadi (assignment=%s)', getattr(assignment, 'id', None))
        return None


@transaction.atomic
def set_group_image(*, teacher: User, room_id, image, request=None) -> ChatRoom:
    """Guruh (kurs) chat rasmini o'rnatadi — faqat kurs egasi o'qituvchi."""
    if not image:
        raise ValidationError({'image': _('Rasm fayli kerak.')})
    room = _get_room(room_id)
    if room.kind != ChatRoom.Kind.COURSE or room.course.teacher_id != teacher.id:
        raise PermissionDenied(_("Faqat kurs o'qituvchisi guruh rasmini o'zgartira oladi."))
    room.image = image
    room.save(update_fields=['image', 'updated_at'])
    audit.record(action='chat.group_image_set', actor=teacher, target=room, request=request)
    return room


# ---------------------------------------------------------------------------
# O'qilganlik
# ---------------------------------------------------------------------------
def _state(room: ChatRoom, user: User) -> RoomRead:
    """Foydalanuvchining shu xonadagi shaxsiy holati (o'qilgan vaqt, qadash, ovozsiz, yashirish)."""
    state, _created = RoomRead.objects.get_or_create(room=room, user=user, defaults={'last_read_at': EPOCH})
    return state


def mark_read(*, user: User, room: ChatRoom, up_to: Message | None = None) -> dict | None:
    """Xonani `up_to` xabarigacha (berilmasa — hozirgacha) o'qilgan deb belgilaydi. Faqat oldinga siljiydi.
    Yangi xabar o'qilgan bo'lsa WebSocket'ga `read` hodisasi tarqatiladi va u qaytariladi, aks holda None."""
    state = _state(room, user)
    target = up_to.created_at if up_to is not None else timezone.now()
    if target <= state.last_read_at:
        return None
    had_unread = room.messages.exclude(sender=user).filter(
        created_at__gt=state.last_read_at, created_at__lte=target, deleted_at__isnull=True,
    ).exists()
    state.last_read_at = target
    state.save(update_fields=['last_read_at', 'updated_at'])
    if not had_unread:
        return None
    last = room.messages.filter(created_at__lte=target).order_by('-created_at').values_list('id', flat=True).first()
    event = {
        'type': 'read', 'room': str(room.id), 'user_id': str(user.id),
        'last_message_id': str(last) if last else None, 'last_read_at': target,
    }
    sync = {'type': 'room_read', 'payload': {
        'room_id': str(room.id), 'user_id': str(user.id), 'last_read_message_id': event['last_message_id'],
    }}
    transaction.on_commit(lambda: realtime.broadcast_event(room.id, event))
    transaction.on_commit(lambda: realtime.broadcast_user_event(user.id, sync))  # boshqa qurilmalar uchun
    return event


def read_room(*, user: User, room_id, last_message_id=None) -> dict:
    """POST /rooms/{id}/read/ — `last_message_id` bo'lsa shu xabargacha, bo'lmasa hammasini o'qilgan deb belgilaydi."""
    room = _readable_room(user, room_id)
    up_to = None
    if last_message_id:
        try:
            up_to = Message.objects.get(pk=last_message_id, room=room)
        except (Message.DoesNotExist, *BAD_ID):
            raise ValidationError({'last_message_id': _('Xabar bu chatda topilmadi.')}) from None
    mark_read(user=user, room=room, up_to=up_to)
    return {'ok': True}


def peer_read_at(room: ChatRoom, user: User):
    """Boshqa a'zolar eng oxirgi o'qigan vaqt — o'z xabarlarimning `status`i uchun."""
    return RoomRead.objects.filter(room=room).exclude(user=user).aggregate(m=Max('last_read_at'))['m']


# ---------------------------------------------------------------------------
# Suhbat holati (qadash / ovozsiz / yashirish) — faqat o'ziga ta'sir qiladi
# ---------------------------------------------------------------------------
def set_room_pinned(*, user: User, room_id, pinned: bool) -> None:
    room = _readable_room(user, room_id)
    state = _state(room, user)
    state.is_pinned = pinned
    state.save(update_fields=['is_pinned', 'updated_at'])


def set_room_muted(*, user: User, room_id, muted: bool, until=None) -> None:
    room = _readable_room(user, room_id)
    moment = None
    if muted and until:
        moment = until if isinstance(until, datetime) else parse_datetime(str(until))
        if moment is None:
            raise ValidationError({'until': _("Noto'g'ri vaqt.")})
        if timezone.is_naive(moment):
            moment = timezone.make_aware(moment)
        if moment <= timezone.now():
            raise ValidationError({'until': _("Vaqt kelajakda bo'lishi kerak.")})
    state = _state(room, user)
    state.muted, state.muted_until = muted, moment
    state.save(update_fields=['muted', 'muted_until', 'updated_at'])


def hide_room(*, user: User, room_id) -> None:
    """"Suhbatni o'chirish / guruhdan chiqish" — ro'yxatdan yashiriladi (yangi xabar kelsa qaytadi).
    Kursdagi a'zolikka ta'sir qilmaydi: u o'qituvchi/to'lov bilan boshqariladi."""
    room = _readable_room(user, room_id)
    state = _state(room, user)
    state.hidden_at = timezone.now()
    state.save(update_fields=['hidden_at', 'updated_at'])


# ---------------------------------------------------------------------------
# Qadalgan xabar, e'lon rejimi, a'zolar
# ---------------------------------------------------------------------------
def _can_pin(user: User, room: ChatRoom) -> bool:
    return selectors.can_pin(user, room)


def pin_dict(pin: PinnedMessage) -> dict:
    message = pin.message
    name = message.sender.get_full_name() or message.sender.username
    return {
        'message_id': str(message.id), 'id': str(message.id), 'author_name': name, 'sender_name': name,
        'text': (message.text or message.file_name)[:200], 'message_type': message.message_type,
        'pinned_at': pin.created_at,
    }


def pin_rows(room: ChatRoom) -> list:
    return list(
        PinnedMessage.objects.filter(room=room, message__deleted_at__isnull=True)
        .select_related('message', 'message__sender').order_by('-created_at')
    )


def _pins_changed(room: ChatRoom) -> None:
    """Qadalganlar o'zgardi: eski (`pinned`, oxirgi qadalgan) va yangi (`room_pinned_changed`, hammasi) hodisa."""
    rows = [pin_dict(pin) for pin in pin_rows(room)]
    legacy = {'type': 'pinned', 'room': str(room.id), 'message': rows[0] if rows else None}
    new = {'type': 'room_pinned_changed', 'payload': {'room_id': str(room.id), 'pinned_messages': rows}}
    transaction.on_commit(lambda: realtime.broadcast_events(room.id, legacy, new))


def list_pins(*, user: User, room_id) -> list:
    room = _readable_room(user, room_id)
    return [pin_dict(pin) for pin in pin_rows(room)]


@transaction.atomic
def pin_message(*, user: User, room_id, message_id) -> ChatRoom:
    """Xabarni qadaydi (bir nechtasi mumkin, takror qadash xato emas). Guruhda faqat o'qituvchi, direct'da ikkala tomon."""
    room = _readable_room(user, room_id)
    if not _can_pin(user, room):
        raise PermissionDenied(_("Xabarni faqat o'qituvchi qadashi mumkin."))
    try:
        message = Message.objects.get(pk=message_id, room=room, deleted_at__isnull=True)
    except (Message.DoesNotExist, *BAD_ID):
        raise ValidationError({'message_id': _('Xabar bu chatda topilmadi.')}) from None
    _pin, created = PinnedMessage.objects.get_or_create(room=room, message=message, defaults={'pinned_by': user})
    if created:
        if PinnedMessage.objects.filter(room=room).count() > MAX_PINS:
            raise ValidationError({'message_id': _("Ko'pi bilan 20 ta xabar qadash mumkin.")})
        room.save(update_fields=['updated_at'])
        _pins_changed(room)
    return room


@transaction.atomic
def unpin_message(*, user: User, room_id, message_id=None) -> ChatRoom:
    """Qadashni olib tashlaydi. `message_id` berilmasa — eng oxirgi qadalgan (eski `DELETE pin/` shunday ishlaydi)."""
    room = _readable_room(user, room_id)
    if not _can_pin(user, room):
        raise PermissionDenied(_("Qadashni faqat o'qituvchi olib tashlashi mumkin."))
    pins = PinnedMessage.objects.filter(room=room)
    if message_id:
        try:
            pins = pins.filter(message_id=message_id)
        except BAD_ID:
            raise NotFound(_('Xabar topilmadi.')) from None
    else:
        pins = pins.filter(pk__in=PinnedMessage.objects.filter(room=room).order_by('-created_at').values('pk')[:1])
    deleted, _per_model = pins.delete()
    if deleted:
        room.save(update_fields=['updated_at'])
        _pins_changed(room)
    return room


def set_announcement_only(*, teacher: User, room_id, value: bool) -> ChatRoom:
    room = _get_room(room_id)
    if not selectors.is_room_teacher(teacher, room):
        raise PermissionDenied(_("Faqat kurs o'qituvchisi e'lon rejimini o'zgartira oladi."))
    room.announcement_only = bool(value)
    room.save(update_fields=['announcement_only', 'updated_at'])
    event = {'type': 'room_updated', 'room': str(room.id), 'announcement_only': room.announcement_only}
    transaction.on_commit(lambda: realtime.broadcast_event(room.id, event))
    return room


def room_members(*, user: User, room_id, request=None, query: str = '') -> list:
    room = _readable_room(user, room_id)
    ids = selectors.member_ids(room)
    online = presence.online_ids(ids)
    users = User.objects.filter(pk__in=ids)
    query = (query or '').strip()
    if query:  # @eslatish ro'yxati uchun: ism, familiya yoki login bo'yicha
        users = users.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query),
        )
    rows = [member_row(u, online, request) for u in users]
    # o'qituvchi birinchi, keyin onlayn, keyin ism bo'yicha
    rows.sort(key=lambda r: (r['role'] != User.Role.TEACHER, not r['is_online'], r['name'].lower()))
    return rows


# ---------------------------------------------------------------------------
# Xabar ustidagi amallar
# ---------------------------------------------------------------------------
def edit_message(*, user: User, message_id, text: str) -> Message:
    message = _get_message(user, message_id)
    if message.sender_id != user.id or message.kind != Message.Kind.USER:
        raise PermissionDenied(_("Faqat o'z xabaringizni tahrirlay olasiz."))
    if message.message_type in (Message.Type.VOICE, Message.Type.ASSIGNMENT):
        raise ValidationError({'detail': _("Bu turdagi xabarni tahrirlab bo'lmaydi.")})
    text = _check_text(text)
    if not text and not message.file:
        raise ValidationError({'text': _("Xabar bo'sh bo'lishi mumkin emas.")})
    message.text = text
    message.edited_at = timezone.now()
    message.save(update_fields=['text', 'edited_at', 'updated_at'])
    legacy = {'type': 'message_updated', 'message': realtime.message_payload(message)}
    new = {'type': 'message_edited', 'payload': {
        'id': str(message.id), 'room_id': str(message.room_id), 'text': message.text, 'edited_at': message.edited_at,
    }}
    transaction.on_commit(lambda: realtime.broadcast_events(message.room_id, legacy, new))
    return message


def _can_delete_for_everyone(user: User, message: Message) -> bool:
    return message.sender_id == user.id or selectors.is_room_teacher(user, message.room)


@transaction.atomic
def delete_messages(*, user: User, ids: list, scope: str) -> int:
    """`scope='me'` — faqat o'zingizdan yashiriladi; `scope='everyone'` — hamma uchun o'chadi (o'z xabaringiz yoki
    kurs o'qituvchisi istalganini). Hammasi yoki hech biri: bitta xabarga huquq bo'lmasa — hech narsa o'chmaydi."""
    if scope not in ('me', 'everyone'):
        raise ValidationError({'scope': _("'me' yoki 'everyone' bo'lishi kerak.")})
    ids = list(dict.fromkeys(str(i) for i in ids or []))
    if not ids:
        raise ValidationError({'ids': _("Xabarlar ro'yxati bo'sh.")})
    if len(ids) > MAX_BULK_DELETE:
        raise ValidationError({'ids': _("Bir martada ko'pi bilan 100 ta xabar.")})
    messages = [_get_message(user, i) for i in ids]
    by_room: dict = {}
    for message in messages:
        by_room.setdefault(message.room, []).append(message)
    if scope == 'everyone':
        for message in messages:
            if not _can_delete_for_everyone(user, message):
                raise PermissionDenied(_("Bu xabarni hamma uchun o'chirish huquqingiz yo'q."))
        now = timezone.now()
        for room, room_messages in by_room.items():
            room_ids = [str(m.id) for m in room_messages]
            for message in room_messages:
                message.deleted_at = now
                message.save(update_fields=['deleted_at', 'updated_at'])
            if PinnedMessage.objects.filter(room=room, message__in=room_messages).delete()[0]:
                _pins_changed(room)
            legacy = {'type': 'message_deleted', 'room': str(room.id), 'ids': room_ids}
            new = {'type': 'messages_removed', 'payload': {'room_id': str(room.id), 'message_ids': room_ids, 'scope': 'everyone'}}
            transaction.on_commit(lambda r=room.id, a=legacy, b=new: realtime.broadcast_events(r, a, b))
    else:
        for message in messages:
            MessageHide.objects.get_or_create(message=message, user=user)
        for room, room_messages in by_room.items():  # faqat shu foydalanuvchining boshqa qurilmalariga
            event = {'type': 'messages_removed', 'payload': {
                'room_id': str(room.id), 'message_ids': [str(m.id) for m in room_messages], 'scope': 'me',
            }}
            transaction.on_commit(lambda e=event: realtime.broadcast_user_event(user.id, e))
    return len(messages)


@transaction.atomic
def forward_messages(*, user: User, room_id, message_ids: list) -> list:
    """Xabarlarni (o'qiy oladigan chatlardan) `room_id` chatiga uzatadi — tartibi asl vaqt bo'yicha. Asl manba
    (xabar, muallif, chat) zanjir bo'ylab saqlanadi."""
    room = _get_room(room_id)
    if not selectors.can_write(user, room):
        raise PermissionDenied(_("Bu chatga yozish huquqingiz yo'q."))
    ids = list(dict.fromkeys(str(i) for i in message_ids or []))
    if not ids:
        raise ValidationError({'message_ids': _("Xabarlar ro'yxati bo'sh.")})
    if len(ids) > MAX_FORWARD:
        raise ValidationError({'message_ids': _("Bir martada ko'pi bilan 50 ta xabar.")})
    sources = sorted((_get_message(user, i) for i in ids), key=lambda m: m.created_at)
    created = []
    for source in sources:
        if source.kind != Message.Kind.USER or source.message_type == Message.Type.ASSIGNMENT:
            raise ValidationError({'message_ids': _("Tizim xabari va vazifa kartasini uzatib bo'lmaydi.")})
        origin = source.forwarded_from_name or source.sender.get_full_name() or source.sender.username
        created.append(Message.objects.create(
            room=room, sender=user, text=source.text, file=source.file.name if source.file else '',
            message_type=source.message_type, file_name=source.file_name, file_type=source.file_type,
            file_size=source.file_size, page_count=source.page_count, duration=source.duration,
            waveform=source.waveform, forwarded_from_name=origin[:150],
            forwarded_from_message=source.forwarded_from_message or source.id,
            forwarded_from_author_id=source.forwarded_from_author_id or source.sender_id,
            forwarded_from_room=source.forwarded_from_room or source.room_id,
        ))
    room.save(update_fields=['updated_at'])
    for message in created:
        transaction.on_commit(lambda m=message: realtime.broadcast_message(m))
    return created


@transaction.atomic
def forward_to_rooms(*, user: User, message_ids: list, room_ids: list) -> list:
    """Xabarlarni bir nechta chatga uzatadi (hammasi yoki hech biri). Qaytaradi: yaratilgan xabarlar."""
    room_ids = list(dict.fromkeys(str(i) for i in room_ids or []))
    if not room_ids:
        raise ValidationError({'target_room_ids': _("Chatlar ro'yxati bo'sh.")})
    if len(room_ids) > MAX_TARGET_ROOMS:
        raise ValidationError({'target_room_ids': _("Bir martada ko'pi bilan 10 ta chatga.")})
    created = []
    for room_id in room_ids:
        created.extend(forward_messages(user=user, room_id=room_id, message_ids=message_ids))
    return created


def reactions_with_users(message: Message) -> list:
    """Hamma uchun bir xil ko'rinish (WebSocket): har emoji uchun soni va kimlar qo'ygani — `reacted`ni mijoz
    o'z id'si bo'yicha aniqlaydi."""
    grouped: dict = {}
    for reaction in MessageReaction.objects.filter(message=message).order_by('created_at'):
        grouped.setdefault(reaction.emoji, []).append(str(reaction.user_id))
    return [{'emoji': e, 'count': len(users), 'user_ids': users} for e, users in grouped.items()]


@transaction.atomic
def toggle_reaction(*, user: User, message_id, emoji: str, mode: str = 'toggle') -> list:
    """Reaksiya. `mode='add'` — qo'yadi (allaqachon bo'lsa o'zgarmaydi), `'remove'` — olib tashlaydi (yo'q bo'lsa
    o'zgarmaydi), `'toggle'` — bor bo'lsa olib tashlaydi, yo'q bo'lsa qo'yadi. Qaytaradi: reaksiyalar ro'yxati."""
    message = _get_message(user, message_id)
    emoji = (emoji or '').strip()
    if not emoji or len(emoji) > 16 or emoji.isascii():  # emoji kamida bitta ASCII bo'lmagan belgidan iborat
        raise ValidationError({'emoji': _("Emoji noto'g'ri.")})
    existing = MessageReaction.objects.filter(message=message, user=user, emoji=emoji).first()
    changed, added = False, False
    if existing and mode in ('toggle', 'remove'):
        existing.delete()
        changed = True
    elif existing is None and mode in ('toggle', 'add'):
        distinct = MessageReaction.objects.filter(message=message).values('emoji').distinct().count()
        taken = MessageReaction.objects.filter(message=message, emoji=emoji).exists()
        if distinct >= MAX_EMOJIS_PER_MESSAGE and not taken:
            raise ValidationError({'emoji': _("Bu xabarga yana yangi emoji qo'shib bo'lmaydi.")})
        MessageReaction.objects.create(message=message, user=user, emoji=emoji)
        changed, added = True, True
    if changed:
        count = MessageReaction.objects.filter(message=message, emoji=emoji).count()
        legacy = {
            'type': 'reaction', 'room': str(message.room_id), 'message_id': str(message.id),
            'emoji': emoji, 'user_id': str(user.id), 'added': added, 'count': count,
        }
        new = {'type': 'message_reaction', 'payload': {
            'room_id': str(message.room_id), 'message_id': str(message.id), 'reactions': reactions_with_users(message),
        }}
        transaction.on_commit(lambda: realtime.broadcast_events(message.room_id, legacy, new))
    return reaction_list(message, user)


def reaction_list(message: Message, user: User) -> list:
    counts: dict = {}
    mine: set = set()
    for reaction in MessageReaction.objects.filter(message=message):
        counts[reaction.emoji] = counts.get(reaction.emoji, 0) + 1
        if reaction.user_id == user.id:
            mine.add(reaction.emoji)
    return [{'emoji': e, 'count': c, 'reacted': e in mine} for e, c in counts.items()]


def search_messages(*, user: User, room_id, q: str) -> dict:
    room = _readable_room(user, room_id)
    q = (q or '').strip()
    if not q:
        raise ValidationError({'q': _("Qidiruv so'zi kerak.")})
    qs = selectors.visible_messages(room, user).filter(text__icontains=q)
    total = qs.count()
    rows = qs.order_by('-created_at')[:SEARCH_LIMIT]
    return {
        'total': total,
        'items': [{'id': str(m.id), 'text': m.text, 'created_at': m.created_at} for m in rows],
    }


@transaction.atomic
def request_direct(*, student: User, teacher_ref: str, request=None) -> ChatRoom:
    """O'quvchi o'z o'qituvchisiga direct so'rov yuboradi (1 martalik).

    Faqat o'zi o'qiydigan kurs o'qituvchisiga. Blocklangan bo'lsa qayta so'rov
    yuborsa yana PENDING bo'ladi (o'qituvchi yana ko'rib chiqadi).
    """
    if student.role != User.Role.STUDENT:
        raise PermissionDenied(_("Faqat o'quvchi so'rov yuboradi."))
    teacher = User.objects.filter(role=User.Role.TEACHER)\
        .filter(pk=teacher_ref if _is_uuid(teacher_ref) else None).first() \
        or User.objects.filter(role=User.Role.TEACHER, username=teacher_ref).first()
    if teacher is None:
        raise NotFound(_("O'qituvchi topilmadi."))
    is_my_teacher = Enrollment.objects.filter(
        student=student, status=Enrollment.Status.APPROVED, course__teacher=teacher,
    ).exists()
    if not is_my_teacher:
        raise PermissionDenied(_("Faqat o'z o'qituvchingizga yozish so'rovi yuborishingiz mumkin."))

    room, created = ChatRoom.objects.get_or_create(
        kind=ChatRoom.Kind.DIRECT, teacher=teacher, student=student,
        defaults={'direct_status': ChatRoom.DirectStatus.PENDING},
    )
    if not created and room.direct_status == ChatRoom.DirectStatus.BLOCKED:
        room.direct_status = ChatRoom.DirectStatus.PENDING
        room.save(update_fields=['direct_status', 'updated_at'])
    audit.record(action='chat.direct_request', actor=student, target=room, request=request)
    return room


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


@transaction.atomic
def respond_direct(*, teacher: User, room_id, action: str, request=None) -> ChatRoom:
    """O'qituvchi so'rovga javob beradi: accept -> ACTIVE, block -> BLOCKED.

    Ochiq chatni ham istalgan payt block qila oladi.
    """
    room = _get_room(room_id)
    if room.kind != ChatRoom.Kind.DIRECT or room.teacher_id != teacher.id:
        raise PermissionDenied(_("Bu so'rov sizga tegishli emas."))
    if action == 'accept':
        room.direct_status = ChatRoom.DirectStatus.ACTIVE
    elif action == 'block':
        room.direct_status = ChatRoom.DirectStatus.BLOCKED
    else:
        raise ValidationError({'action': _("accept yoki block bo'lishi kerak.")})
    room.save(update_fields=['direct_status', 'updated_at'])
    audit.record(action=f'chat.direct_{action}', actor=teacher, target=room, request=request)
    return room
