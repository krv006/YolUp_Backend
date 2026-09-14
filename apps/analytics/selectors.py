"""Admin boshqaruv paneli uchun agregatsiya — bu app'da model yo'q, faqat
o'qish. Faqat `audit.view` ruxsati bor rol (ADMIN/SUPER_ADMIN) chaqiradi.

Barcha "faol"/"tugagan" filtrlar `Course.objects`/`Lesson.objects` (soft-delete'ni
hisobga oladigan standart manager) orqali boshlanadi — `User.objects.filter(
courses__is_active=True)` kabi teskari-FK filtrlash soft-delete'ni chetlab
o'tishi mumkin, shuning uchun avval xavfsiz ID ro'yxati olinadi.
"""
from datetime import timedelta

from django.db.models import Avg, Count, F, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment, Lesson, LessonRating
from apps.quizzes.models import QuizAttempt

_ENROLLED = Enrollment.Status.APPROVED
_FINISHED = Lesson.Status.FINISHED
_CANCELLED = Lesson.Status.CANCELLED

PERIOD_BUCKET_COUNTS = {'day': 14, 'week': 8, 'month': 12, 'year': 4}

_UZ_MONTHS = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun', 'Iyul', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']


def _add_months(dt, n: int):
    month = dt.month - 1 + n
    year = dt.year + month // 12
    month = month % 12 + 1
    return dt.replace(year=year, month=month)


def _period_edges(period: str, count: int, now):
    """`count`+1 ta chegara vaqti qaytaradi — i-bucket = [edges[i], edges[i+1])."""
    if period == 'day':
        anchor = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return [anchor - timedelta(days=count - i) for i in range(count + 1)]
    if period == 'week':
        this_monday = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        anchor = this_monday + timedelta(days=7)
        return [anchor - timedelta(weeks=count - i) for i in range(count + 1)]
    if period == 'month':
        anchor = _add_months(now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), 1)
        return [_add_months(anchor, -(count - i)) for i in range(count + 1)]
    if period == 'year':
        anchor = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        anchor = anchor.replace(year=anchor.year + 1)
        return [anchor.replace(year=anchor.year - (count - i)) for i in range(count + 1)]
    raise ValueError(f"Noma'lum davr: {period}")


def _format_label(period: str, start) -> str:
    if period == 'day':
        return f'{start.day} {_UZ_MONTHS[start.month - 1]}'
    if period == 'week':
        end = start + timedelta(days=6)
        return f'{start.day}-{end.day} {_UZ_MONTHS[end.month - 1]}'
    if period == 'month':
        return _UZ_MONTHS[start.month - 1]
    return str(start.year)


def _attendance_rate(course_ids=None, start=None, end=None):
    """Kutilgan (yozilgan o'quvchi soni x tugagan dars) va haqiqiy qatnashgan
    (kamida bir marta kirgan) o'quvchilar nisbati, foizda. Ma'lumot bo'lmasa None."""
    lessons = Lesson.objects.filter(status=_FINISHED)
    if course_ids is not None:
        lessons = lessons.filter(course_id__in=course_ids)
    if start is not None:
        lessons = lessons.filter(starts_at__gte=start)
    if end is not None:
        lessons = lessons.filter(starts_at__lt=end)
    lessons = lessons.annotate(
        enrolled_count=Count(
            'course__enrollments', filter=Q(course__enrollments__status=_ENROLLED), distinct=True,
        ),
        attended_count=Count(
            'attendances', filter=Q(attendances__joined_at__isnull=False), distinct=True,
        ),
    )
    expected = sum(lesson.enrolled_count for lesson in lessons)
    actual = sum(lesson.attended_count for lesson in lessons)
    return round(actual / expected * 100, 1) if expected else None


def _top_courses(limit: int = 5) -> list:
    courses = Course.objects.filter(is_active=True).select_related('teacher').annotate(
        student_count=Count('enrollments', filter=Q(enrollments__status=_ENROLLED), distinct=True),
    ).order_by('-student_count')[:limit]

    result = []
    for course in courses:
        rating = LessonRating.objects.filter(
            lesson__course_id=course.id, lesson__is_deleted=False,
        ).aggregate(avg=Avg('stars'))['avg']
        result.append({
            'id': str(course.id),
            'title': course.title,
            'teacher_name': course.teacher.get_full_name() or course.teacher.username,
            'student_count': course.student_count,
            'avg_rating': round(rating, 1) if rating is not None else None,
            'attendance_rate': _attendance_rate(course_ids=[course.id]),
        })
    return result


def _top_teachers(limit: int = 5) -> list:
    teacher_ids = Course.objects.filter(is_active=True).values_list('teacher_id', flat=True).distinct()
    now = timezone.localtime(timezone.now())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    scored = []
    for teacher in User.objects.filter(id__in=teacher_ids):
        course_ids = list(Course.objects.filter(teacher=teacher, is_active=True).values_list('id', flat=True))
        lessons_this_month = Lesson.objects.filter(
            course_id__in=course_ids, status=_FINISHED, starts_at__gte=month_start, starts_at__lte=now,
        ).count()
        held_or_cancelled = Lesson.objects.filter(course_id__in=course_ids, status__in=[_FINISHED, _CANCELLED])
        finished = held_or_cancelled.filter(status=_FINISHED).count()
        cancelled = held_or_cancelled.filter(status=_CANCELLED).count()
        reliability = round(finished / (finished + cancelled) * 100, 1) if (finished + cancelled) else None
        rating = LessonRating.objects.filter(
            lesson__course_id__in=course_ids, lesson__is_deleted=False,
        ).aggregate(avg=Avg('stars'))['avg']
        scored.append({
            'id': str(teacher.id),
            'name': teacher.get_full_name() or teacher.username,
            'course_count': len(course_ids),
            'lessons_this_month': lessons_this_month,
            'avg_rating': round(rating, 1) if rating is not None else None,
            'reliability': reliability,
        })
    scored.sort(key=lambda row: row['avg_rating'] or 0, reverse=True)
    return scored[:limit]


def dashboard_summary() -> dict:
    from apps.lessons.models import LessonRecording

    active_course_ids = list(Course.objects.filter(is_active=True).values_list('id', flat=True))
    active_teacher_ids = Course.objects.filter(is_active=True).values_list('teacher_id', flat=True).distinct()

    active_students = User.objects.filter(
        role=User.Role.STUDENT,
        enrollments__status=_ENROLLED,
        enrollments__course_id__in=active_course_ids,
    ).distinct().count()
    active_teachers = User.objects.filter(id__in=active_teacher_ids).count()

    rating_agg = LessonRating.objects.filter(lesson__is_deleted=False).aggregate(
        avg=Avg('stars'), count=Count('id'),
    )
    total_videos = LessonRecording.objects.filter(
        status=LessonRecording.Status.COMPLETED, lesson__is_deleted=False,
    ).count()

    return {
        'active_students': active_students,
        'active_teachers': active_teachers,
        'active_courses': len(active_course_ids),
        'avg_rating': round(rating_agg['avg'], 1) if rating_agg['avg'] is not None else None,
        'rating_count': rating_agg['count'],
        'total_videos': total_videos,
        'top_courses': _top_courses(),
        'top_teachers': _top_teachers(),
    }


def _attempt_summary(attempts) -> dict:
    """`QuizAttempt` queryset'idan urinishlar soni va o'rtacha foiz."""
    total = attempts.count()
    avg_pct = attempts.annotate(pct=F('score') * 100.0 / F('max_score')).aggregate(avg=Avg('pct'))['avg']
    return {
        'attempt_count': total,
        'avg_percentage': round(avg_pct, 1) if avg_pct is not None else None,
    }


def student_own_stats(student: User) -> dict:
    """O'quvchining Workspace > Tahlil bo'limi uchun shaxsiy statistikasi —
    test natijalari tarixi, o'rtacha foiz va so'nggi urinishlar."""
    attempts = QuizAttempt.objects.filter(
        student=student, max_score__gt=0,
    ).select_related('quiz', 'quiz__course').order_by('-created_at')

    recent = [
        {
            'quiz_id': str(attempt.quiz_id),
            'quiz_title': attempt.quiz.title,
            'course_title': attempt.quiz.course.title,
            'score': attempt.score,
            'max_score': attempt.max_score,
            'percentage': round(attempt.score / attempt.max_score * 100, 1),
            'taken_at': attempt.created_at,
        }
        for attempt in attempts[:20]
    ]
    return {**_attempt_summary(attempts), 'recent_attempts': recent}


def teacher_course_breakdown(teacher: User) -> list[dict]:
    """O'qituvchining har bir kursi ("sinf") bo'yicha solishtiruv
    statistikasi — Workspace > Tahlil'da kurslar orasidagi farqni ko'rish uchun."""
    courses = Course.objects.filter(teacher=teacher, is_active=True)

    result = []
    for course in courses:
        student_count = Enrollment.objects.filter(course=course, status=_ENROLLED).count()
        lessons = Lesson.objects.filter(course=course)
        finished = lessons.filter(status=_FINISHED).count()
        cancelled = lessons.filter(status=_CANCELLED).count()
        reliability = round(finished / (finished + cancelled) * 100, 1) if (finished + cancelled) else None
        rating = LessonRating.objects.filter(
            lesson__course=course, lesson__is_deleted=False,
        ).aggregate(avg=Avg('stars'))['avg']
        quiz_stats = _attempt_summary(
            QuizAttempt.objects.filter(quiz__course=course, max_score__gt=0)
        )
        result.append({
            'course_id': str(course.id),
            'course_title': course.title,
            'student_count': student_count,
            'avg_rating': round(rating, 1) if rating is not None else None,
            'reliability': reliability,
            'quiz_avg_percentage': quiz_stats['avg_percentage'],
            'quiz_attempt_count': quiz_stats['attempt_count'],
            'attendance_rate': _attendance_rate(course_ids=[course.id]),
        })
    result.sort(key=lambda row: row['student_count'], reverse=True)
    return result


def teacher_own_stats(teacher: User) -> dict:
    """O'qituvchining Workspace > Tahlil bo'limi uchun shaxsiy statistikasi —
    umumiy ko'rsatkichlar (apps.accounts.selectors.teacher_detail_stats bilan
    bir xil, admin panelida ham shu funksiya ishlatiladi) + kurslar orasidagi
    solishtiruv."""
    from apps.accounts import selectors as account_selectors

    return {
        'overall': account_selectors.teacher_detail_stats(teacher),
        'courses': teacher_course_breakdown(teacher),
    }


def dashboard_trends(period: str) -> dict:
    if period not in PERIOD_BUCKET_COUNTS:
        raise ValueError(f"Noma'lum davr: {period}")
    count = PERIOD_BUCKET_COUNTS[period]
    now = timezone.localtime(timezone.now())
    edges = _period_edges(period, count, now)

    labels, enrollments, completed, cancelled, quiz_avg, attendance = [], [], [], [], [], []
    for i in range(count):
        start, end = edges[i], edges[i + 1]
        labels.append(_format_label(period, start))
        enrollments.append(
            Enrollment.objects.filter(status=_ENROLLED, created_at__gte=start, created_at__lt=end).count()
        )
        bucket_lessons = Lesson.objects.filter(starts_at__gte=start, starts_at__lt=end)
        completed.append(bucket_lessons.filter(status=_FINISHED).count())
        cancelled.append(bucket_lessons.filter(status=_CANCELLED).count())
        avg_score = QuizAttempt.objects.filter(
            created_at__gte=start, created_at__lt=end, max_score__gt=0,
        ).annotate(pct=F('score') * 100.0 / F('max_score')).aggregate(avg=Avg('pct'))['avg']
        quiz_avg.append(round(avg_score, 1) if avg_score is not None else None)
        attendance.append(_attendance_rate(start=start, end=end))

    return {
        'period': period,
        'labels': labels,
        'enrollments': enrollments,
        'lessons_completed': completed,
        'lessons_cancelled': cancelled,
        'quiz_avg_score': quiz_avg,
        'attendance_rate': attendance,
    }
