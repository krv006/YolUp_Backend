"""Haqiqatda bo'shab qolgan, lekin DB'da "live" bo'lib qolgan ovozli xonalarni yopadi.

    python manage.py close_stale_voice_rooms

Odatda xona o'zi yopiladi — oxirgi ishtirokchi `leave/` chaqirganda
(`apps.voice.services._maybe_close_if_empty`). Bu buyruq faqat xavfsizlik
to'ri: tarmoq uzilib `leave/` hech qachon chaqirilmagan hollar uchun (brauzer
qulab tushishi va h.k.) — LiveKit'ning HAQIQIY xona holatini tekshirib,
DB bilan mos kelmasa tuzatadi. `auto_finish_expired_lessons` bilan bir xil
kadrda (5 daqiqa) cron orqali ishga tushirilishi kifoya.
"""
import asyncio
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from livekit.api import LiveKitAPI
from livekit.protocol.room import ListParticipantsRequest

from apps.voice.models import VoiceRoom, VoiceRoomParticipant

logger = logging.getLogger('apps')


def _livekit_http_url() -> str:
    api_url = getattr(settings, 'LIVEKIT_API_URL', '')
    if api_url:
        return api_url
    return settings.LIVEKIT_URL.replace('wss://', 'https://').replace('ws://', 'http://')


def _has_live_participants(room: VoiceRoom) -> bool:
    async def _check():
        client = LiveKitAPI(
            url=_livekit_http_url(), api_key=settings.LIVEKIT_API_KEY, api_secret=settings.LIVEKIT_API_SECRET,
        )
        try:
            result = await client.room.list_participants(ListParticipantsRequest(room=room.room_name))
            return len(result.participants) > 0
        finally:
            await client.aclose()

    try:
        return asyncio.run(_check())
    except Exception:  # noqa: BLE001 — LiveKit'da xona umuman yo'q bo'lsa ham bo'sh deb hisoblanadi
        logger.info("close_stale_voice_rooms: %s uchun LiveKit holatini tekshirib bo'lmadi", room.room_name)
        return False


class Command(BaseCommand):
    help = "Haqiqatda bo'shab qolgan, lekin DB'da 'live' bo'lib qolgan ovozli xonalarni yopadi."

    def handle(self, *args, **options):
        closed = 0
        for room in VoiceRoom.objects.filter(status=VoiceRoom.Status.LIVE):
            if _has_live_participants(room):
                continue
            updated = VoiceRoom.objects.filter(pk=room.pk, status=VoiceRoom.Status.LIVE).update(
                status=VoiceRoom.Status.ENDED, ended_at=timezone.now(),
            )
            if updated:
                VoiceRoomParticipant.objects.filter(room_id=room.pk, left_at__isnull=True).update(
                    left_at=timezone.now(),
                )
                closed += 1
        self.stdout.write(self.style.SUCCESS(f"Yopilgan bo'sh xonalar: {closed}"))
