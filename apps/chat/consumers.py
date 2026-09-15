"""Chat WebSocket consumer — real vaqtda xabarlar va "yozmoqda..." indikatori.

Ulanish:  wss://<domain>/ws/chat/<room_id>/?token=<JWT access>
Yopilish kodlari: 4401 — token yaroqsiz, 4403 — xonaga a'zo emas.

Client -> server:
    {"type": "message", "text": "..."}   — xabar yuborish (REST POST bilan teng)
    {"type": "typing"}                    — "yozmoqda..." signali

Server -> client:
    {"type": "message", "message": {...}} — yangi xabar (MessageSerializer sxemasi);
        REST orqali yuborilgan xabarlar ham shu kanaldan keladi
    {"type": "typing", "user_id": "...", "name": "..."} — kimdir yozmoqda
        (o'zingizni user_id bo'yicha filtrlab tashlang)
    {"type": "lesson_live", "lesson": {"id", "title", "room_name"}} — kurs guruhida
        jonli dars boshlandi (Telegram uslubidagi guruh video chat chizig'i uchun)
    {"type": "lesson_ended", "lesson_id": "..."} — jonli dars tugadi
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


def group_name(room_id) -> str:
    return f'chat_{room_id}'


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        room_id = self.scope['url_route']['kwargs']['room_id']
        if not getattr(user, 'is_authenticated', False):
            await self.close(code=4401)
            return
        if not await self._can_read(user, room_id):
            await self.close(code=4403)
            return
        self.room_id = room_id
        self.group = group_name(room_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        # Ulanish paytida kurs darsi allaqachon LIVE bo'lsa — darhol xabar
        # beramiz. lesson_live signali BIR MARTA (dars boshlanganda) yuboriladi;
        # shu lahzada ulanmagan/qayta ulangan mijoz uni butunlay o'tkazib
        # yuborishi mumkin edi, sahifani yangilamaguncha bilmasdi.
        live_lesson = await self._live_lesson(room_id)
        if live_lesson:
            await self.send_json({'type': 'lesson_live', 'lesson': live_lesson})

    async def disconnect(self, code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        kind = content.get('type')
        user = self.scope['user']

        if kind == 'typing':
            await self.channel_layer.group_send(self.group, {
                'type': 'chat.typing',
                'user_id': str(user.id),
                'name': user.first_name or user.username,
            })
            return

        if kind == 'message':
            text = (content.get('text') or '').strip()
            if not text:
                return
            # services.send_message o'zi broadcast qiladi (realtime.py) —
            # shuning uchun bu yerda qayta yuborilmaydi
            error = await self._send_message(user, text)
            if error:
                await self.send_json({'type': 'error', 'detail': error})

    # ── channel layer eventlari ──
    async def chat_message(self, event):
        await self.send_json({'type': 'message', 'message': event['message']})

    async def chat_typing(self, event):
        await self.send_json({
            'type': 'typing', 'user_id': event['user_id'], 'name': event['name'],
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
        return {'id': str(lesson.id), 'title': lesson.course.title, 'room_name': lesson.room_name}

    @database_sync_to_async
    def _send_message(self, user, text):
        from rest_framework.exceptions import APIException

        from . import services

        try:
            services.send_message(user=user, room_id=self.room_id, text=text)
            return None
        except APIException as exc:
            return str(exc.detail)
