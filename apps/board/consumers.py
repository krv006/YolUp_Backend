"""Doska WebSocket consumer — real vaqtda chizish (polling o'rniga).

Ulanish:  wss://<domain>/ws/board/<lesson_id>/?token=<JWT access>
Yopilish: 4401 — token yaroqsiz, 4403 — darsga a'zo emas.

Client -> server:
    {"type": "stroke", "sheet": 0, "stroke": {...}}  — element qo'shish
        (REST POST .../stroke/ bilan teng kuchli; ruxsat/validatsiya bir xil)

Server -> client (barcha ishtirokchilarga):
    {"type": "stroke", "sheet": 0, "stroke": {...}}     — yangi element
    {"type": "erase", "sheet": 0, "stroke_ids": [...], "by", "reason"}
    {"type": "sheet", "index": 2}                        — yangi sheet
    {"type": "error", "detail": "..."}                   — faqat yuboruvchiga
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .realtime import group_name


class BoardConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        lesson_id = self.scope['url_route']['kwargs']['lesson_id']
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
        if not await self._can_view(user, lesson_id):
            await self.accept()
            await self.close(code=4403)
            return
        self.lesson_id = lesson_id
        self.group = group_name(lesson_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get('type') != 'stroke':
            return
        error = await self._add_stroke(
            self.scope['user'],
            content.get('sheet', 0),
            content.get('stroke') or {},
        )
        if error:
            await self.send_json({'type': 'error', 'detail': error})

    async def board_event(self, message):
        await self.send_json(message['event'])

    # ── sync DB yordamchilari ──
    @database_sync_to_async
    def _can_view(self, user, lesson_id) -> bool:
        from . import services

        try:
            lesson = services._get_lesson(lesson_id)  # noqa: SLF001 — modul ichki API
        except Exception:
            return False
        return services.can_view(user, lesson)

    @database_sync_to_async
    def _add_stroke(self, user, sheet_index, stroke):
        from rest_framework.exceptions import APIException

        from . import services

        try:
            services.add_stroke(
                user=user, lesson_id=self.lesson_id,
                sheet_index=sheet_index, stroke=stroke,
            )
            return None
        except APIException as exc:
            return str(exc.detail)
