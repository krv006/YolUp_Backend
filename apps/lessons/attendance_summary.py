"""Kurs davomat hisoboti: har o'quvchi uchun davomat va fokus foizi (frontend barcha yozuvlarni olib o'zi hisoblamasin).

Ta'riflar (tugagan darslar bo'yicha, tanlangan davrda):
  - davomat % = o'quvchi qatnashgan (`Attendance.joined_at` bor) darslar / davrdagi tugagan darslar soni.
  - fokus % = qatnashgan vaqtning dars oynasidan chiqib ketmagan ulushi. Chiqish (`exit`) dan qaytishgacha (`return`),
    qaytmagan bo'lsa chiqish/dars oxirigacha bo'lgan vaqt "chetda" hisoblanadi. Hamma qatnashgan darslar vaqti
    bo'yicha tortilgan o'rtacha. Qatnashmagan bo'lsa — `null`.
"""
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import ParentChildLink, User

from .models import Attendance, Enrollment, FocusEvent, Lesson

RANGES = ('all', '30d', 'month')


def _name(user: User) -> str:
    return user.get_full_name() or user.username


def _lesson_end(lesson: Lesson):
    return (lesson.live_started_at or lesson.starts_at) + timedelta(minutes=lesson.duration_min)


def _percent(part: float, whole: float):
    return round(part * 100 / whole) if whole > 0 else None


def _students_for(course, viewer: User) -> list:
    students = User.objects.filter(
        enrollments__course=course, enrollments__status=Enrollment.Status.APPROVED,
    ).distinct()
    if viewer.role == User.Role.STUDENT:
        students = students.filter(pk=viewer.pk)
    elif viewer.role == User.Role.PARENT:
        students = students.filter(
            parent_links__parent=viewer, parent_links__status=ParentChildLink.Status.APPROVED,
        )
    return sorted(students, key=lambda u: _name(u).lower())


def _away_seconds(events: list, start, end) -> float:
    away, exited = 0.0, None
    for event in events:
        if event.kind == FocusEvent.Kind.EXIT and exited is None:
            exited = event.created_at
        elif event.kind == FocusEvent.Kind.RETURN and exited is not None:
            away += max(0.0, (min(event.created_at, end) - max(exited, start)).total_seconds())
            exited = None
    if exited is not None:
        away += max(0.0, (end - max(exited, start)).total_seconds())
    return away


def course_summary(*, course, viewer: User, range_key: str = 'all', now=None) -> dict:
    now = now or timezone.now()
    lessons = Lesson.objects.filter(course=course, is_deleted=False, status=Lesson.Status.FINISHED)
    if range_key == '30d':
        lessons = lessons.filter(starts_at__gte=now - timedelta(days=30))
    elif range_key == 'month':
        first = timezone.localtime(now).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        lessons = lessons.filter(starts_at__gte=first)
    lessons = list(lessons)
    students = _students_for(course, viewer)

    attendance = {
        (a.student_id, a.lesson_id): a
        for a in Attendance.objects.filter(
            lesson__in=lessons, student__in=students, joined_at__isnull=False,
        )
    }
    events: dict = {}
    for event in FocusEvent.objects.filter(lesson__in=lessons, student__in=students).order_by('created_at'):
        events.setdefault((event.student_id, event.lesson_id), []).append(event)

    rows, totals = [], {'attended': 0, 'present': 0.0, 'focused': 0.0}
    for student in students:
        attended, present, focused = 0, 0.0, 0.0
        for lesson in lessons:
            record = attendance.get((student.id, lesson.id))
            if record is None:
                continue
            attended += 1
            end = record.left_at or _lesson_end(lesson)
            seconds = max(0.0, (end - record.joined_at).total_seconds())
            away = min(seconds, _away_seconds(events.get((student.id, lesson.id), []), record.joined_at, end))
            present += seconds
            focused += seconds - away
        rows.append({
            'id': str(student.id), 'name': _name(student),
            'attendance_percent': _percent(attended, len(lessons)) if lessons else 0,
            'focus_percent': _percent(focused, present),
            'attended_count': attended,
        })
        totals['attended'] += attended
        totals['present'] += present
        totals['focused'] += focused
    return {
        'attendance_percent': _percent(totals['attended'], len(students) * len(lessons)) if lessons and students else 0,
        'focus_percent': _percent(totals['focused'], totals['present']),
        'lesson_count': len(lessons),
        'students': rows,
    }
