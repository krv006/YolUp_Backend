"""Monitoring selector qatlami — Admin panel > Server monitoring uchun o'qish."""
from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from .models import ResourceSample


def latest_sample() -> ResourceSample | None:
    return ResourceSample.objects.first()  # Meta.ordering = ['-created_at']


def history(*, hours: int) -> QuerySet[ResourceSample]:
    since = timezone.now() - timedelta(hours=hours)
    return ResourceSample.objects.filter(created_at__gte=since).order_by('created_at')


def peak_sample(*, hours: int) -> ResourceSample | None:
    """Berilgan davr ichida eng band lahza — CPU foizi eng yuqori bo'lgan namuna."""
    since = timezone.now() - timedelta(hours=hours)
    return ResourceSample.objects.filter(created_at__gte=since).order_by('-cpu_percent').first()
