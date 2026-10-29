"""Bildirishnoma WebSocket — yangi xabar kelganda darhol push (badge/toast).

Ulanish: wss://<domain>/ws/notifications/?token=<JWT access>
Yopilish kodi: 4401 — token yaroqsiz.

Server -> client:
    {"type": "notification", "notification": {...}} — NotificationSerializer sxemasi
    {"type": "chat_activity", "room": "...", "message_id": "...", "sender_id": "...", "created_at": "..."}
        — chat xonasida yangi xabar (xona ochiq bo'lmasa ham; yuboruvchining o'ziga ham — boshqa qurilmalari uchun)
    {"type": "chat_typing", "room": "...", "user_id": "...", "name": "...", "kind": "text"|"voice"}
        — kimdir shu xonada yozmoqda (yozayotganning o'ziga kelmaydi; saqlanmaydi, 2 soniyada ko'pi bilan bir marta)
"""
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .realtime import group_name


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if not getattr(user, 'is_authenticated', False):
            # `accept()`dan OLDIN `close()` chaqirilsa, ASGI server ulanishni
            # qabul qilish o'rniga butunlay rad etadi (HTTP 403) — maxsus kod
            # (4401) brauzerga hech qachon yetib bormaydi, frontendning
            # "4401 kelsa tokenni yangila" mantig'i ishlamay qoladi (2026-09-30
            # production'da topilgan haqiqiy xato). Shuning uchun avval qabul
            # qilib, SHUNDAN KEYIN kod bilan yopamiz.
            await self.accept()
            await self.close(code=4401)
            return
        self.group = group_name(user.id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notification_new(self, event):
        await self.send_json({'type': 'notification', 'notification': event['notification']})

    async def chat_signal(self, event):
        """Chat ro'yxati uchun qisqa hodisalar (`chat_activity`, `chat_typing`) — tayyor JSON shu holicha uzatiladi."""
        await self.send_json(event['event'])
