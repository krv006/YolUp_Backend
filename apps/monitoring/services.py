"""Monitoring service qatlami — psutil orqali o'lchash + eski namunalarni tozalash."""
from datetime import timedelta

import psutil
from django.conf import settings
from django.utils import timezone

from .models import ResourceSample

# Namunalar shu muddatdan uzoqroq saqlanmaydi — jadval cheksiz o'smasin.
_RETENTION_DAYS = 90


def disk_percent() -> float | None:
    """Yozuvlar papkasi turgan disk qancha to'lgan (foizda). O'lchab bo'lmasa None."""
    try:
        return round(float(psutil.disk_usage(str(settings.RECORDINGS_DIR)).percent), 1)
    except (OSError, TypeError, ValueError):
        return None


def record_sample() -> ResourceSample:
    # `interval=1` — 1 soniyalik haqiqiy o'lchov: `interval=None` bo'lsa
    # birinchi chaqiruv doim 0.0 qaytaradi (solishtirish uchun oldingi holat kerak).
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    sample = ResourceSample.objects.create(
        cpu_percent=cpu_percent,
        memory_percent=memory.percent,
        memory_used_mb=memory.used // (1024 * 1024),
        memory_total_mb=memory.total // (1024 * 1024),
        host=settings.SERVER_ROLE,
        disk_percent=disk_percent(),
    )
    ResourceSample.objects.filter(
        created_at__lt=timezone.now() - timedelta(days=_RETENTION_DAYS),
    ).delete()
    return sample
