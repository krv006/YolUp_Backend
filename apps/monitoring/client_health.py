"""Mijoz "salomatlik" hisobotlari (2026-11-12): jonli darsda brauzer yuboradi (`POST /live/lesson/<id>/client-health/`),
admin ko'radi (`GET /monitoring/client-health/`). Maqsad — kamera/ekran qotishi sababini (CPU, tarmoq) mijozdan o'lchash."""
from datetime import timedelta

from django.db.models import Count, Max, Min, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, ValidationError

from apps.lessons import selectors as lesson_selectors

from .models import ClientHealthReport

SOURCES = ('camera', 'screen_share', 'microphone', 'screen_share_audio')
REASONS = ('none', 'cpu', 'bandwidth', 'other')
QUALITIES = ('excellent', 'good', 'poor', 'lost', 'unknown')
_SEVERITY = {'': 0, 'none': 0, 'other': 1, 'bandwidth': 2, 'cpu': 3}
MAX_TRACKS = 8
MAX_EVENTS = 10
RETENTION_DAYS = 14


def _num(value, field, *, low=0, high=10 ** 9, integer=False):
    """None/bo'sh -> None; bool, matn va chegaradan chiqqan qiymat rad etiladi."""
    if value is None or value == '':
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError({field: _("Son bo'lishi kerak.")})
    if not low <= value <= high:
        raise ValidationError({field: _("Qiymat chegaradan tashqarida.")})
    return int(value) if integer else float(value)


def _clean_track(raw, index) -> dict:
    if not isinstance(raw, dict):
        raise ValidationError({'tracks': {str(index): _("Noto'g'ri element.")}})
    source = raw.get('source')
    if source not in SOURCES:
        raise ValidationError({'tracks': {str(index): {'source': _("Manba: %(s)s") % {'s': ', '.join(SOURCES)}}}})
    reason = raw.get('quality_limitation_reason') or 'none'
    if reason not in REASONS:
        raise ValidationError({'tracks': {str(index): {'quality_limitation_reason': _("Qiymat: %(s)s") % {'s': ', '.join(REASONS)}}}})
    track = {'source': source, 'quality_limitation_reason': reason}
    for key, high, integer in (
        ('fps', 240, False), ('width', 8192, True), ('height', 8192, True), ('target_bitrate', 100_000_000, True),
        ('bitrate', 100_000_000, True), ('packets_lost', 10 ** 9, True), ('jitter', 100_000, False), ('rtt', 100_000, False),
    ):
        value = _num(raw.get(key), f'tracks.{index}.{key}', high=high, integer=integer)
        if value is not None:
            track[key] = value
    return track


def clean_payload(data) -> dict:
    if not isinstance(data, dict):
        raise ValidationError({'detail': _("Hisobot obyekt bo'lishi kerak.")})
    tracks_raw = data.get('tracks') or []
    if not isinstance(tracks_raw, list) or len(tracks_raw) > MAX_TRACKS:
        raise ValidationError({'tracks': _("Ko'pi bilan %(n)s ta trek ro'yxati.") % {'n': MAX_TRACKS}})
    tracks = [_clean_track(item, i) for i, item in enumerate(tracks_raw)]
    events_raw = data.get('events') or []
    if not isinstance(events_raw, list) or len(events_raw) > MAX_EVENTS or any(not isinstance(e, str) for e in events_raw):
        raise ValidationError({'events': _("Ko'pi bilan %(n)s ta qisqa matn.") % {'n': MAX_EVENTS}})
    quality = data.get('connection_quality') or ''
    if quality and quality not in QUALITIES:
        raise ValidationError({'connection_quality': _("Qiymat: %(s)s") % {'s': ', '.join(QUALITIES)}})
    page_visible = data.get('page_visible')
    if page_visible is not None and not isinstance(page_visible, bool):
        raise ValidationError({'page_visible': _("true yoki false.")})
    cpu_flag = data.get('cpu_constrained')
    if cpu_flag is not None and not isinstance(cpu_flag, bool):
        raise ValidationError({'cpu_constrained': _("true yoki false.")})
    fps_values = [t['fps'] for t in tracks if t['source'] in ('camera', 'screen_share') and 'fps' in t]
    worst = max((t['quality_limitation_reason'] for t in tracks), key=lambda r: _SEVERITY[r], default='')
    return {
        'cpu_constrained': bool(cpu_flag) or worst == 'cpu',
        'limited_by': worst,
        'min_fps': min(fps_values) if fps_values else None,
        'hardware_concurrency': _num(data.get('hardware_concurrency'), 'hardware_concurrency', low=1, high=1024, integer=True),
        'device_memory_gb': _num(data.get('device_memory'), 'device_memory', low=0, high=1024),
        'connection_quality': quality,
        'page_visible': page_visible,
        'tracks': tracks,
        'events': [e[:40] for e in events_raw],
    }


def record(*, user, lesson_id, data, user_agent: str = '') -> ClientHealthReport:
    """Dars foydalanuvchiga ko'rinadigan bo'lsa (o'qituvchi yoki yozilgan o'quvchi) hisobotni saqlaydi."""
    import uuid

    try:
        uuid.UUID(str(lesson_id))
    except ValueError:
        raise NotFound(_('Dars topilmadi.')) from None
    lesson = lesson_selectors.lessons_for(user).filter(pk=lesson_id).first()
    if lesson is None:
        raise NotFound(_('Dars topilmadi.'))
    fields = clean_payload(data)
    return ClientHealthReport.objects.create(
        lesson=lesson, user=user, role=user.role, user_agent=(user_agent or '')[:300], **fields,
    )


def summary(*, hours: int = 24, lesson_id=None, user_id=None, limit: int = 50) -> dict:
    """Admin uchun: foydalanuvchilar kesimida xulosa + so'nggi hisobotlar."""
    since = timezone.now() - timedelta(hours=hours)
    qs = ClientHealthReport.objects.filter(created_at__gte=since)
    if lesson_id:
        qs = qs.filter(lesson_id=lesson_id)
    if user_id:
        qs = qs.filter(user_id=user_id)
    rows = (
        qs.values('user_id', 'user__username', 'role')
        .annotate(
            reports=Count('id'), cpu_limited=Count('id', filter=Q(limited_by='cpu')),
            bandwidth_limited=Count('id', filter=Q(limited_by='bandwidth')), min_fps=Min('min_fps'), last_at=Max('created_at'),
        ).order_by('-cpu_limited', '-reports')[:200]
    )
    users = []
    for row in rows:
        latest = qs.filter(user_id=row['user_id']).order_by('-created_at').first()
        users.append({
            'user_id': str(row['user_id']), 'username': row['user__username'], 'role': row['role'],
            'reports': row['reports'], 'cpu_limited_reports': row['cpu_limited'],
            'bandwidth_limited_reports': row['bandwidth_limited'], 'min_fps': row['min_fps'], 'last_at': row['last_at'],
            'hardware_concurrency': latest.hardware_concurrency if latest else None,
            'device_memory_gb': latest.device_memory_gb if latest else None,
            'user_agent': latest.user_agent if latest else '',
        })
    recent = [{
        'id': str(r.id), 'lesson_id': str(r.lesson_id), 'user_id': str(r.user_id), 'username': r.user.username, 'role': r.role,
        'created_at': r.created_at, 'cpu_constrained': r.cpu_constrained, 'limited_by': r.limited_by, 'min_fps': r.min_fps,
        'connection_quality': r.connection_quality, 'page_visible': r.page_visible, 'tracks': r.tracks, 'events': r.events,
    } for r in qs.select_related('user').order_by('-created_at')[:max(1, min(limit, 200))]]
    return {'hours': hours, 'total': qs.count(), 'cpu_limited_total': qs.filter(limited_by='cpu').count(), 'users': users, 'recent': recent}


def prune(*, days: int = RETENTION_DAYS) -> int:
    deleted, _unused = ClientHealthReport.objects.filter(created_at__lt=timezone.now() - timedelta(days=days)).delete()
    return deleted
