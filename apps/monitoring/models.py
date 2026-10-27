"""Admin panel > Server monitoring modeli.

Docker socket ATAYLAB ulanmagan (production xavfsizlik chegarasini
o'zgartirmaslik uchun admin bilan kelishilgan) — shuning uchun boshqa
konteynerlar (db/redis/livekit/cron) bu yerda YO'Q, faqat `backend`
konteynerining o'z cgroup-chegaralangan CPU/RAM holati ko'rinadi
(`apps.monitoring.management.commands.record_resource_sample`, backend
konteynerining o'zi ichida davriy ishga tushiriladi — docker-compose.prod.yml).
"""
from django.db.models import CharField, FloatField, PositiveIntegerField

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
