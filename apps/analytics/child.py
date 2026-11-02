"""Ota-ona uchun farzand statistikasi (BACKEND_OTA_ONA.md 2, 9, 17-bandlar).

Ta'riflar — bir joyda, ota-ona va o'quvchi bir xil raqamni ko'rsin:
  - davomat % = davrda tugagan (FINISHED) darslardan o'quvchi qatnashgani (`Attendance.joined_at` bor). Dars o'quvchi
    tasdiqlangan yozilgan kurslardan.
  - ball (10 ballik) = tasdiqlangan (DONE) uy vazifalarining ENG SO'NGGI topshirig'i `overall_score` (0-100) / 10.
    Mock/test/imtihon natijalari ballga KIRMAYDI. Davrga o'qituvchi tasdiqlagan payt (`reviewed_at`, bo'lmasa `checked_at`/
    `created_at`) bo'yicha joylanadi.
  - vazifalar = davrda muddati (`due_at`, yo'q bo'lsa yaratilgan sana) tushgan FAOL vazifalar; topshirilgan = o'quvchida
    topshirig'i bor. `due_soon` — keyingi 24 soatda muddati keladigan, hali topshirilmagan vazifalar.
  - "darsda" vaqti = shu haftada qatnashgan darslarda kirgan-chiqqan oralig'i (chiqmagan bo'lsa dars oxirigacha).
Davomat/faollik bilan bog'liq maydonlar `analytics` roziligi o'chiq bo'lsa yopiladi (403 `consent_required` yoki `restricted`).
"""
import math
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.accounts import consent
from apps.accounts.models import Consent, ParentChildLink, User
from apps.homework.models import Assignment, Submission
from apps.lessons.models import Attendance, Enrollment, Lesson

SCALE = 10
TREND_WEEKS = 6
DUE_SOON_HOURS = 24


# ── vaqt oraliqlari (mahalliy vaqt bo'yicha) ───────────────────────────────

def _local_midnight(dt):
    return timezone.localtime(dt).replace(hour=0, minute=0, second=0, microsecond=0)


def month_start(now, offset: int = 0):
    """Oyning birinchi kuni 00:00 (mahalliy); `offset=-1` — o'tgan oy."""
    local = _local_midnight(now).replace(day=1)
    index = local.year * 12 + (local.month - 1) + offset
    return local.replace(year=index // 12, month=index % 12 + 1)


def week_start(now, offset: int = 0):
    """Dushanba 00:00 (mahalliy); `offset=-1` — o'tgan hafta."""
    local = _local_midnight(now)
    return local - timedelta(days=local.weekday()) + timedelta(weeks=offset)


def bounds(period: str, now, offset: int = 0):
    if period == 'week':
        start = week_start(now, offset)
        return start, start + timedelta(weeks=1)
    start = month_start(now, offset)
    return start, month_start(now, offset + 1)


# ── hisoblash qismlari ─────────────────────────────────────────────────────

def _lesson_end(lesson: Lesson):
    return (lesson.live_started_at or lesson.starts_at) + timedelta(minutes=lesson.duration_min)


def _finished_lessons(student: User, start, end):
    return Lesson.objects.filter(
        is_deleted=False, status=Lesson.Status.FINISHED, starts_at__gte=start, starts_at__lt=end,
        course__enrollments__student=student, course__enrollments__status=Enrollment.Status.APPROVED,
    ).distinct()


def attendance_in(student: User, start, end) -> dict:
    lessons = list(_finished_lessons(student, start, end).values_list('id', flat=True))
    attended = (
        Attendance.objects.filter(student=student, lesson_id__in=lessons, joined_at__isnull=False).values('lesson_id').distinct().count()
        if lessons else 0
    )
    return {'attended': attended, 'total': len(lessons), 'percent': round(attended * 100 / len(lessons)) if lessons else None}


def _latest_done_scores(student: User, course_id=None) -> list:
    """[(vaqt, ball_10lik, assignment_id, course_id)] — har vazifaning ENG SO'NGGI tasdiqlangan topshirig'i."""
    qs = Submission.objects.filter(student=student).order_by('assignment_id', '-created_at').values(
        'assignment_id', 'assignment__course_id', 'status', 'overall_score', 'reviewed_at', 'checked_at', 'created_at',
    )
    if course_id:
        qs = qs.filter(assignment__course_id=course_id)
    latest, rows = set(), []
    for row in qs:
        if row['assignment_id'] in latest:
            continue
        latest.add(row['assignment_id'])
        if row['status'] == Submission.Status.DONE and row['overall_score'] is not None:
            rows.append((row['reviewed_at'] or row['checked_at'] or row['created_at'], row['overall_score'] / 10, row['assignment_id'], row['assignment__course_id']))
    return rows


def _average(scores, start=None, end=None):
    values = [score for at, score, *_rest in scores if (start is None or start <= at < end)]
    return round(sum(values) / len(values), 1) if values else None


def _assignments_in(student: User, start, end):
    """Davrda muddati tushgan faol vazifalar: [(id, due)] + topshirilganlar to'plami."""
    courses = Enrollment.objects.filter(student=student, status=Enrollment.Status.APPROVED).values('course_id')
    due_here = Q(due_at__gte=start, due_at__lt=end) | Q(due_at__isnull=True, created_at__gte=start, created_at__lt=end)
    assignments = list(Assignment.objects.filter(course_id__in=courses, status=Assignment.Status.ACTIVE).filter(due_here).values_list('id', flat=True))
    submitted = set(Submission.objects.filter(student=student, assignment_id__in=assignments).values_list('assignment_id', flat=True))
    return assignments, submitted


def _due_soon(student: User, now) -> int:
    courses = Enrollment.objects.filter(student=student, status=Enrollment.Status.APPROVED).values('course_id')
    ids = list(Assignment.objects.filter(
        course_id__in=courses, status=Assignment.Status.ACTIVE, due_at__gt=now, due_at__lte=now + timedelta(hours=DUE_SOON_HOURS),
    ).values_list('id', flat=True))
    if not ids:
        return 0
    return len(set(ids) - set(Submission.objects.filter(student=student, assignment_id__in=ids).values_list('assignment_id', flat=True)))


def week_minutes(student: User, now) -> int:
    start, end = bounds('week', now)
    total = 0.0
    for record in Attendance.objects.filter(student=student, joined_at__gte=start, joined_at__lt=end).select_related('lesson'):
        stop = record.left_at or min(now, _lesson_end(record.lesson))
        total += max(0.0, (stop - record.joined_at).total_seconds())
    return round(total / 60)


def score_trend(scores, now, weeks: int = TREND_WEEKS) -> list:
    result = []
    for back in range(weeks - 1, -1, -1):
        start, end = bounds('week', now, -back)
        result.append({'week_start': timezone.localtime(start).date().isoformat(), 'average': _average(scores, start, end)})
    return result


# ── ochiq funksiyalar ──────────────────────────────────────────────────────

def child_summary(*, viewer: User, student_id, now=None) -> dict:
    """GET /analytics/child/<id>/summary/ — to'rt kartochka + 6 haftalik ball dinamikasi."""
    student = consent.approved_child(viewer, student_id)
    consent.require(student, Consent.Kind.ANALYTICS)
    now = now or timezone.now()
    this_start, this_end = bounds('month', now)
    prev_start, prev_end = bounds('month', now, -1)
    this_att, prev_att = attendance_in(student, this_start, this_end), attendance_in(student, prev_start, prev_end)
    scores = _latest_done_scores(student)
    average, previous = _average(scores, this_start, this_end), _average(scores, prev_start, prev_end)
    assignments, submitted = _assignments_in(student, this_start, this_end)
    return {
        'student_id': str(student.pk),
        'attendance': {
            'month_percent': this_att['percent'], 'attended': this_att['attended'], 'total': this_att['total'],
            'delta_percent': (this_att['percent'] - prev_att['percent']) if this_att['percent'] is not None and prev_att['percent'] is not None else None,
        },
        'score': {
            'average': average, 'scale': SCALE,
            'delta': round(average - previous, 1) if average is not None and previous is not None else None,
        },
        'homework': {'total': len(assignments), 'submitted': len(submitted), 'due_soon': _due_soon(student, now)},
        'week_minutes': week_minutes(student, now),
        'score_trend': score_trend(scores, now),
    }


def children_summary(*, viewer: User, period: str, now=None) -> list:
    """GET /analytics/children/summary/?period=week|month — barcha tasdiqlangan farzandlar bitta javobda (N+1 yo'q)."""
    now = now or timezone.now()
    start, end = bounds(period, now)
    month_from, month_to = bounds('month', now)
    links = (
        ParentChildLink.objects.filter(parent=viewer, status=ParentChildLink.Status.APPROVED)
        .select_related('student').order_by('student__first_name', 'student__username')
    )
    students = [link.student for link in links]
    denied = consent.denied_student_ids([s.pk for s in students], Consent.Kind.ANALYTICS)
    rows = []
    for student in students:
        restricted = student.pk in denied
        scores = _latest_done_scores(student)
        assignments, submitted = _assignments_in(student, start, end)
        row = {
            'student_id': str(student.pk),
            'groups_count': Enrollment.objects.filter(student=student, status=Enrollment.Status.APPROVED).count(),
            'restricted': restricted,
            'attendance': None, 'last_visit': None,
            'homework': {'period_submitted': len(submitted), 'period_total': len(assignments)},
            'score': {'average': _average(scores), 'period_average': _average(scores, start, end), 'scale': SCALE},
        }
        if not restricted:
            month_att, period_att = attendance_in(student, month_from, month_to), attendance_in(student, start, end)
            attended_total = Attendance.objects.filter(student=student, joined_at__isnull=False).values('lesson_id').distinct().count()
            row['attendance'] = {'month_percent': month_att['percent'], 'period_percent': period_att['percent'], 'attended_total': attended_total}
            last = (
                Attendance.objects.filter(student=student, joined_at__isnull=False).select_related('lesson', 'lesson__course')
                .order_by('-joined_at').first()
            )
            if last is not None:
                row['last_visit'] = {
                    'lesson_id': str(last.lesson_id), 'course_title': last.lesson.course.title,
                    'lesson_title': last.lesson.title, 'joined_at': last.joined_at,
                }
        rows.append(row)
    return rows


def _course_scores(course_id, start=None, end=None) -> dict:
    """{student_id: o'rtacha ball} — shu kursning har bir o'quvchisi (tasdiqlangan yozilgan) uchun; ballsizlar kirmaydi."""
    result = {}
    for student in User.objects.filter(enrollments__course_id=course_id, enrollments__status=Enrollment.Status.APPROVED).distinct():
        average = _average(_latest_done_scores(student, course_id), start, end)
        if average is not None:
            result[student.pk] = average
    return result


def _rank_of(scores: dict, student_pk):
    if student_pk not in scores:
        return None
    return 1 + sum(1 for value in scores.values() if value > scores[student_pk])  # teng ballar bir xil o'rin


def child_rank(*, viewer: User, student_id, course_id, month=None, now=None) -> dict:
    """GET /analytics/child/<id>/rank/?course=&month=YYYY-MM — guruhdagi o'rin (faqat ball bo'yicha; boshqalarning ballari chiqmaydi)."""
    from rest_framework.exceptions import NotFound, ValidationError

    student = consent.approved_child(viewer, student_id)
    if not Enrollment.objects.filter(student=student, course_id=course_id, status=Enrollment.Status.APPROVED).exists():
        raise NotFound('Kurs topilmadi.')
    now = now or timezone.now()
    if month:
        try:
            year, mon = (int(part) for part in month.split('-'))
            anchor = timezone.localtime(now).replace(year=year, month=mon, day=1, hour=0, minute=0, second=0, microsecond=0)
        except (ValueError, TypeError):
            raise ValidationError({'month': "YYYY-MM ko'rinishida bo'lishi kerak."})
    else:
        anchor = month_start(now)
    this_from, this_to = anchor, month_start(anchor, 1)
    prev_from, prev_to = month_start(anchor, -1), anchor
    now_scores = _course_scores(course_id, this_from, this_to)
    rank = _rank_of(now_scores, student.pk)
    prev_rank = _rank_of(_course_scores(course_id, prev_from, prev_to), student.pk)
    total = len(now_scores)
    return {
        'student_id': str(student.pk), 'course_id': str(course_id), 'month': timezone.localtime(anchor).strftime('%Y-%m'),
        'rank': rank, 'total': total,
        'top_percent': math.ceil(rank * 100 / total) if rank and total else None,          # "Top 25%"
        'percentile': round((total - rank) * 100 / total) if rank and total else None,      # shundan pastroq o'quvchilar ulushi
        'delta': (prev_rank - rank) if rank is not None and prev_rank is not None else None,  # musbat = yuqoriga ko'tarildi
    }
