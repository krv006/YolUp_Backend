"""Admin panel > Server monitoring modeli.

Docker socket ATAYLAB ulanmagan (production xavfsizlik chegarasini
o'zgartirmaslik uchun admin bilan kelishilgan) — shuning uchun boshqa
konteynerlar (db/redis/livekit/cron) bu yerda YO'Q, faqat `backend`
konteynerining o'z cgroup-chegaralangan CPU/RAM holati ko'rinadi
(`apps.monitoring.management.commands.record_resource_sample`, backend
konteynerining o'zi ichida davriy ishga tushiriladi — docker-compose.prod.yml).
"""
from django.conf import settings
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    FloatField,
    ForeignKey,
    Index,
    JSONField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
)

from apps.core.models import TimeStampedUUIDModel


class ResourceSample(TimeStampedUUIDModel):
    cpu_percent = FloatField()
    memory_percent = FloatField()
    memory_used_mb = PositiveIntegerField()
    memory_total_mb = PositiveIntegerField()
    # Ikki serverli joylashtirishda qaysi serverniki ('core' | 'media'); bitta serverda bo'sh.
    host = CharField(max_length=20, blank=True, default='', db_index=True)
    # Yozuvlar (yoki umuman) joylashgan disk to'lganligi, foizda
    disk_percent = FloatField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} · CPU {self.cpu_percent}% · RAM {self.memory_percent}%'


class ClientHealthReport(TimeStampedUUIDModel):
    """Jonli darsda mijozdan (brauzerdan) kelgan "salomatlik" hisoboti (2026-11-12): kamera/ekran FPS, o'lcham, `qualityLimitationReason`
    (cpu/bandwidth), kompyuter xususiyatlari. Maqsad — "kamera qotib qoldi" kabi muammolarning sababini mijozdan o'lchangan
    raqam bilan topish (serverda ko'rinmaydi). Eski hisobotlar `prune_client_health` bilan o'chiriladi."""

    lesson = ForeignKey('lessons.Lesson', CASCADE, related_name='client_health')
    user = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='client_health')
    role = CharField(max_length=16, blank=True, default='')
    # Qisqa xulosa (qidirish/filtr uchun); to'liq ma'lumot `tracks`da
    cpu_constrained = BooleanField(default=False)
    limited_by = CharField(max_length=12, blank=True, default='')  # none | cpu | bandwidth | other (eng og'iri)
    min_fps = FloatField(null=True, blank=True)
    hardware_concurrency = PositiveSmallIntegerField(null=True, blank=True)
    device_memory_gb = FloatField(null=True, blank=True)
    connection_quality = CharField(max_length=12, blank=True, default='')
    page_visible = BooleanField(null=True, blank=True)
    tracks = JSONField(default=list, blank=True)
    events = JSONField(default=list, blank=True)
    user_agent = CharField(max_length=300, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['lesson', '-created_at']),
            Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user_id} · {self.limited_by or "ok"} · {self.created_at:%Y-%m-%d %H:%M}'
