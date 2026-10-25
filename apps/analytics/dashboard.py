"""O'qituvchi bosh sahifasi uchun bitta so'rovli ko'rsatkichlar va "So'nggi faollik" ro'yxati."""
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.homework.models import Submission
from apps.lessons.models import Course, Enrollment, Lesson
from apps.notifications.models import NotificationRecipient
from apps.notifications.serializers import category_of, title_of
from apps.notifications.services import strip_html

from . import selectors

MAX_ACTIVITY = 50


def teacher_overview(teacher: User) -> dict:
    """`lessons_today` (bekor qilinmaganlar) va shundan tugaganlari; tekshiruvni kutayotgan topshiriqlar va ular
    tegishli vazifalar soni; faol guruhlar va ulardagi (takrorlanmas) o'quvchilar; oxirgi 7 kunlik davomat foizi
    (tugagan darslar bo'yicha; ma'lumot bo'lmasa `null`)."""
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today = Lesson.objects.filter(
        course__teacher=teacher, starts_at__gte=start, starts_at__lt=start + timedelta(days=1),
    ).exclude(status=Lesson.Status.CANCELLED)
    pending = Submission.objects.filter(
        assignment__course__teacher=teacher, status=Submission.Status.PENDING_REVIEW,
    )
    courses = list(Course.objects.filter(teacher=teacher, is_active=True).values_list('id', flat=True))
    rate = selectors._attendance_rate(course_ids=courses, start=now - timedelta(days=7), end=now) if courses else None
    return {
        'lessons_today': today.count(),
        'lessons_today_finished': today.filter(status=Lesson.Status.FINISHED).count(),
        'submissions_pending': pending.count(),
        'assignments_pending': pending.values('assignment_id').distinct().count(),
        'students_total': Enrollment.objects.filter(
            course_id__in=courses, status=Enrollment.Status.APPROVED,
        ).values('student_id').distinct().count(),
        'courses_total': len(courses),
        'attendance_rate_week': round(rate) if rate is not None else None,
    }


def recent_activity(user: User, limit=10) -> list:
    """Foydalanuvchining oxirgi bildirishnomalari — ro'yxat kartasi shaklida (sarlavha va oddiy matn alohida)."""
    try:
        limit = max(1, min(int(limit), MAX_ACTIVITY))
    except (TypeError, ValueError):
        limit = 10
    rows = NotificationRecipient.objects.filter(user=user).select_related('notification').order_by('-created_at')[:limit]
    return [{
        'id': str(row.notification_id),
        'category': category_of(row.notification.kind, row.notification.link_type),
        'title': title_of(row.notification.kind, row.notification.link_type),
        'body': strip_html(row.notification.description or ''),
        'link_type': row.notification.link_type,
        'link_id': row.notification.link_id,
        'is_read': row.read_at is not None,
        'created_at': row.created_at,
    } for row in rows]
