"""Chat WebSocket consumer — real vaqtda xabarlar va "yozmoqda..." indikatori.

Ulanish:  wss://<domain>/ws/chat/<room_id>/?token=<JWT access>
Yopilish kodlari: 4401 — token yaroqsiz, 4403 — xonaga a'zo emas.

Client -> server:
    {"type": "message", "text": "...", "reply_to_id": "...", "client_message_id": "..."}
        — xabar yuborish (REST POST bilan teng; fayl/ovoz faqat REST orqali)
    {"type": "typing", "kind": "text"|"voice"} — "yozmoqda..." signali (`kind` standart `text`: matn yoki ovozli xabar yozilmoqda)

Server -> client:
    {"type": "message", "message": {...}} — yangi xabar (MessageSerializer sxemasi);
        REST orqali yuborilgan xabarlar ham shu kanaldan keladi
    {"type": "typing", "user_id": "...", "name": "...", "kind": "text"|"voice"} — kimdir yozmoqda
        (o'zingizni user_id bo'yicha filtrlab tashlang)
    {"type": "lesson_live", "lesson": {"id", "title", "room_name"}} — kurs guruhida
        jonli dars boshlandi (Telegram uslubidagi guruh video chat chizig'i uchun)
    {"type": "lesson_ended", "lesson_id": "..."} — jonli dars tugadi
    {"type": "read", "room": "...", "user_id": "...", "last_message_id": "...", "last_read_at": "..."}
        — kimdir xonani shu xabargacha o'qidi (o'z xabarlarimdagi galochka uchun)
    {"type": "delivered", "room": "...", "user_id": "...", "last_message_id": "...", "last_delivered_at": "..."}
        — (faqat 1:1 chat) suhbatdosh qurilmasi xabarlarni shu xabargacha qabul qildi ("yetib bordi")
    {"type": "message_updated", "message": {...}} — xabar tahrirlandi
    {"type": "message_deleted", "room": "...", "ids": ["..."]} — xabar(lar) hamma uchun o'chirildi
    {"type": "pinned", "room": "...", "message": {id, sender_name, text, message_type} | null}
    {"type": "reaction", "room": "...", "message_id": "...", "emoji": "...", "user_id": "...",
        "added": true, "count": 2} — reaksiya qo'shildi/olindi (`reacted`ni o'z user_id'ingiz bo'yicha yangilang)
    {"type": "room_updated", "room": "...", "announcement_only": true}
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

TYPING_KINDS = ('text', 'voice')
TYPING_FANOUT_SECONDS = 2        # bir kishining "yozmoqda"si chat ro'yxatiga shuncha soniyada bir marta uzatiladi
TYPING_FANOUT_MAX_MEMBERS = 100  # undan katta guruhlarda ro'yxatga uzatilmaydi
TYPING_MEMBERS_TTL = 30          # a'zolar ro'yxati keshi (soniya)


def group_name(room_id) -> str:
    return f'chat_{room_id}'


def user_group_name(user_id) -> str:
    """Foydalanuvchining hamma ochiq ulanishlari (qurilmalari) — faqat unga tegishli hodisalar uchun."""
    return f'chat_user_{user_id}'


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        room_id = self.scope['url_route']['kwargs']['room_id']
        # `accept()`dan OLDIN `close()` chaqirilsa, ASGI server ulanishni
        # qabul qilish o'rniga butunlay rad etadi (HTTP 403) — maxsus kod
        # (4401/4403) brauzerga hech qachon yetib bormaydi, frontendning
        # "4401 kelsa tokenni yangila" mantig'i ishlamay qoladi (2026-09-30
        # production'da topilgan haqiqiy xato). Shuning uchun avval qabul
        # qilib, SHUNDAN KEYIN kod bilan yopamiz.
        if not getattr(user, 'is_authenticated', False):
            await self.accept()
            await self.close(code=4401)
            return
        if not await self._can_read(user, room_id):
            await self.accept()
            await self.close(code=4403)
            return
        self.room_id = room_id
        self.group = group_name(room_id)
        self.is_teacher, self.can_pin, self.is_direct = await self._room_flags(user, room_id)
        self.user_group = user_group_name(user.id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()
        # Ulanish paytida kurs darsi allaqachon LIVE bo'lsa — darhol xabar
        # beramiz. lesson_live signali BIR MARTA (dars boshlanganda) yuboriladi;
        # shu lahzada ulanmagan/qayta ulangan mijoz uni butunlay o'tkazib
        # yuborishi mumkin edi, sahifani yangilamaguncha bilmasdi.
        live_lesson = await self._live_lesson(room_id)
        if live_lesson:
            await self.send_json({'type': 'lesson_live', 'lesson': live_lesson})
        # onlayn belgisi eng oxirida: bu qo'shimcha kutish ulanishni sekinlashtirib, yuqoridagi
        # "LIVE dars" tekshiruvi bilan guruh signali orasida poyga hosil qilmasin
        await self._presence(user, online=True)
        if self.is_direct:
            await self._deliver_backlog(user)  # oflayn paytda kelgan xabarlar endi "yetib bordi"

    async def disconnect(self, code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
            await self._presence(self.scope['user'], online=False)

    async def receive_json(self, content, **kwargs):
        kind = content.get('type')
        user = self.scope['user']

        if kind == 'typing':
            typing_kind = content.get('kind') if content.get('kind') in TYPING_KINDS else 'text'
            name = user.first_name or user.username
            await self.channel_layer.group_send(self.group, {
                'type': 'chat.typing',
                'user_id': str(user.id),
                'name': name,
                'kind': typing_kind,
            })
            # Xona ochiq bo'lmagan a'zolarning chat ro'yxatida ham ko'rinsin (`ws/notifications/` orqali)
            targets = await self._typing_targets(user)
            if targets:
                from apps.notifications.realtime import group_name as notice_group

                signal = {'type': 'chat_typing', 'room': str(self.room_id), 'user_id': str(user.id), 'name': name, 'kind': typing_kind}
                for target in targets:
                    await self.channel_layer.group_send(notice_group(target), {'type': 'chat.signal', 'event': signal})
            return

        if kind == 'message':
            text = (content.get('text') or '').strip()
            if not text:
                return
            # services.send_message o'zi broadcast qiladi (realtime.py) —
            # shuning uchun bu yerda qayta yuborilmaydi
            error = await self._send_message(
                user, text, content.get('reply_to_id'), str(content.get('client_message_id') or ''),
            )
            if error:
                await self.send_json({'type': 'error', 'detail': error})

    # ── channel layer eventlari ──
    def _with_capabilities(self, message: dict) -> dict:
        """Hamma uchun bir xil tarqatilgan xabarga SHU ulanish egasining huquqlari qo'shiladi (HTTP javobidagi `capabilities` bilan bir xil qoida)."""
        user = self.scope['user']
        user_message = message.get('kind') == 'user'
        own = str((message.get('sender') or {}).get('id')) == str(user.id)
        message_type = message.get('message_type')
        message['capabilities'] = {
            'edit': own and user_message and message_type in ('text', 'file', 'image', 'video'),
            'delete': True,
            'delete_everyone': own or self.is_teacher,
            'pin': self.can_pin,
            'react': True,
            'forward': user_message and message_type != 'assignment',
        }
        return message

    async def chat_message(self, event):
        message = dict(event['message'])
        await self.send_json({'type': 'message', 'message': self._with_capabilities(message)})
        if self.is_direct and str((message.get('sender') or {}).get('id')) != str(self.scope['user'].id):
            await self._deliver(message.get('id'))  # yuboruvchiga "yetib bordi" belgisi

    async def chat_event(self, event):
        payload = dict(event['event'])
        if payload.get('type') == 'message_updated' and isinstance(payload.get('message'), dict):
            payload['message'] = self._with_capabilities(dict(payload['message']))
        await self.send_json(payload)

    async def chat_typing(self, event):
        await self.send_json({
            'type': 'typing', 'user_id': event['user_id'], 'name': event['name'], 'kind': event.get('kind', 'text'),
        })

    async def chat_lesson_live(self, event):
        await self.send_json({'type': 'lesson_live', 'lesson': event['lesson']})

    async def chat_lesson_ended(self, event):
        await self.send_json({'type': 'lesson_ended', 'lesson_id': event['lesson_id']})

    async def chat_member_removed(self, event):
        """Kursdan chiqarilgan o'quvchining o'zi bo'lsa — ulanishni yopadi
        (boshqalarga bu event kelsa ham, o'zi bo'lmaganlar jim o'tkazib yuboradi)."""
        if event['user_id'] != str(self.scope['user'].id):
            return
        await self.send_json({'type': 'removed'})
        await self.close(code=4403)

    # ── sync DB yordamchilari ──
    @database_sync_to_async
    def _can_read(self, user, room_id) -> bool:
        from . import selectors
        from .models import ChatRoom

        try:
            room = ChatRoom.objects.select_related('course', 'teacher', 'student').get(pk=room_id)
        except ChatRoom.DoesNotExist:
            return False
        return selectors.can_read(user, room)

    @database_sync_to_async
    def _live_lesson(self, room_id):
        from apps.lessons.models import Lesson

        from .models import ChatRoom

        try:
            room = ChatRoom.objects.select_related('course').get(pk=room_id)
        except ChatRoom.DoesNotExist:
            return None
        if room.kind != ChatRoom.Kind.COURSE or room.course_id is None:
            return None
        lesson = room.course.lessons.filter(status=Lesson.Status.LIVE).first()
        if lesson is None:
            return None
        return {'id': str(lesson.id), 'title': lesson.title or lesson.course.title, 'room_name': lesson.room_name}

    @database_sync_to_async
    def _room_flags(self, user, room_id):
        from . import selectors
        from .models import ChatRoom

        room = ChatRoom.objects.select_related('course').get(pk=room_id)
        return selectors.is_room_teacher(user, room), selectors.can_pin(user, room), room.kind == ChatRoom.Kind.DIRECT

    @database_sync_to_async
    def _typing_targets(self, user) -> list:
        """Chat ro'yxatiga "yozmoqda" yuboriladigan a'zolar (yozayotgan o'zi chiqarib tashlanadi). "Yozmoqda" tez-tez keladi,
        shuning uchun bir kishi uchun 2 soniyada ko'pi bilan bir marta uzatiladi; a'zolar ro'yxati qisqa muddat keshlanadi;
        juda katta guruhlarda (`TYPING_FANOUT_MAX_MEMBERS` dan ko'p) uzatilmaydi — har tugma bosilishi yuzlab yuborishga aylanmasin."""
        from django.core.cache import cache

        from . import selectors
        from .models import ChatRoom

        if not cache.add(f'chat:typing:{self.room_id}:{user.id}', 1, TYPING_FANOUT_SECONDS):
            return []
        key = f'chat:members:{self.room_id}'
        ids = cache.get(key)
        if ids is None:
            room = ChatRoom.objects.select_related('course').get(pk=self.room_id)
            ids = [str(i) for i in selectors.member_ids(room)]
            cache.set(key, ids, TYPING_MEMBERS_TTL)
        if len(ids) > TYPING_FANOUT_MAX_MEMBERS:
            return []
        return [i for i in ids if i != str(user.id)]

    @database_sync_to_async
    def _deliver(self, message_id):
        from . import services

        try:
            services.deliver_message(user=self.scope['user'], message_id=message_id)
        except Exception:  # noqa: BLE001 — "yetib bordi" belgisi xabar oqimini buzmasin
            pass

    @database_sync_to_async
    def _deliver_backlog(self, user):
        from . import services

        try:
            services.deliver_room(user=user, room_id=self.room_id)
        except Exception:  # noqa: BLE001 — belgi ulanishni buzmasin
            pass

    @database_sync_to_async
    def _presence(self, user, online: bool):
        from . import presence

        if online:
            presence.mark_online(user.id)
        else:
            presence.mark_offline(user.id)
            presence.touch_last_seen(user.id, force=True)

    @database_sync_to_async
    def _send_message(self, user, text, reply_to_id=None, client_message_id=''):
        from rest_framework.exceptions import APIException

        from . import services

        try:
            services.send_message(
                user=user, room_id=self.room_id, text=text,
                reply_to_id=reply_to_id, client_message_id=client_message_id,
            )
            return None
        except APIException as exc:
            return str(exc.detail)
