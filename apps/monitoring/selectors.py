"""Monitoring selector qatlami — Admin panel > Server monitoring uchun o'qish."""
from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from .models import ResourceSample


def _scope(host: str | None) -> QuerySet[ResourceSample]:
    """`host` berilmasa — asosiy server ('core' yoki bitta serverdagi eski bo'sh nom); 'all' — hammasi; aks holda aynan shu server."""
    qs = ResourceSample.objects.all()
    if host == 'all':
        return qs
    if not host or host == 'core':
        return qs.filter(host__in=('', 'core'))
    return qs.filter(host=host)


def latest_sample(host: str | None = None) -> ResourceSample | None:
    return _scope(host).order_by('-created_at').first()


def history(*, hours: int, host: str | None = None) -> QuerySet[ResourceSample]:
    since = timezone.now() - timedelta(hours=hours)
    return _scope(host).filter(created_at__gte=since).order_by('created_at')


def peak_sample(*, hours: int, host: str | None = None) -> ResourceSample | None:
    """Berilgan davr ichida eng band lahza — CPU foizi eng yuqori bo'lgan namuna."""
    since = timezone.now() - timedelta(hours=hours)
    return _scope(host).filter(created_at__gte=since).order_by('-cpu_percent').first()
