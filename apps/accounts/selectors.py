"""Accounts selector layer — barcha o'quvchi (read-only) querylar shu yerda.

Qoida: ko'rish huquqi (kim nimani ko'radi) shu qatlamda kodlanadi, view'da emas.
"""
from django.db.models import Q, QuerySet

from .models import Consent, ParentChildLink, User


def links_for_user(user: User) -> QuerySet[ParentChildLink]:
    return ParentChildLink.objects.filter(
        Q(parent=user) | Q(student=user)
    ).select_related('parent', 'student')


def approved_children(parent: User) -> QuerySet[User]:
    return User.objects.filter(
        parent_links__parent=parent,
        parent_links__status=ParentChildLink.Status.APPROVED,
    )


def is_linked(parent: User, student) -> bool:
    return ParentChildLink.objects.filter(
        parent=parent, student=student, status=ParentChildLink.Status.APPROVED
    ).exists()


def consents_for_parent(parent: User) -> QuerySet[Consent]:
    return Consent.objects.filter(
        student__parent_links__parent=parent,
        student__parent_links__status=ParentChildLink.Status.APPROVED,
    ).select_related('student')


def teacher_rating_stats(teacher: User) -> dict:
    """O'qituvchining BARCHA darslari bo'yicha o'rtacha ball va baholar soni.

    apps.lessons ichidan lazy import — apps.accounts'ni apps.lessons'ga
    bog'lab qo'ymaslik uchun (LessonRating faqat shu funksiya ichida kerak).
    """
    from django.db.models import Avg, Count

    from apps.lessons.models import LessonRating

    agg = LessonRating.objects.filter(lesson__course__teacher=teacher).aggregate(
        avg_rating=Avg('stars'), rating_count=Count('id'),
    )
    avg = agg['avg_rating']
    return {
        'avg_rating': round(avg, 2) if avg is not None else None,
        'rating_count': agg['rating_count'],
    }


def teacher_detail_stats(teacher: User) -> dict:
    """Bitta o'qituvchi uchun to'liq statistika (admin panel) — reyting
    (`teacher_rating_stats`) ustiga kurslar/darslar/o'quvchilar soni va
    baholar taqsimoti (1-5 yulduz bo'yicha necha marta qo'yilgani) qo'shiladi.
    """
    from django.db.models import Count

    from apps.lessons.models import Course, Enrollment, Lesson, LessonRating

    course_ids = list(Course.objects.filter(teacher=teacher, is_active=True).values_list('id', flat=True))
    student_count = User.objects.filter(
        role=User.Role.STUDENT,
        enrollments__course_id__in=course_ids,
        enrollments__status=Enrollment.Status.APPROVED,
    ).distinct().count()

    lessons = Lesson.objects.filter(course_id__in=course_ids)
    finished = lessons.filter(status=Lesson.Status.FINISHED).count()
    cancelled = lessons.filter(status=Lesson.Status.CANCELLED).count()
    scheduled = lessons.filter(status=Lesson.Status.SCHEDULED).count()
    reliability = round(finished / (finished + cancelled) * 100, 1) if (finished + cancelled) else None

    breakdown = {str(i): 0 for i in range(1, 6)}
    for row in (
        LessonRating.objects.filter(lesson__course__teacher=teacher, lesson__is_deleted=False)
        .values('stars').annotate(count=Count('id'))
    ):
        breakdown[str(row['stars'])] = row['count']

    return {
        **teacher_rating_stats(teacher),
        'rating_breakdown': breakdown,
        'course_count': len(course_ids),
        'student_count': student_count,
        'lessons_finished': finished,
        'lessons_cancelled': cancelled,
        'lessons_scheduled': scheduled,
        'reliability': reliability,
    }


def teacher_list() -> QuerySet[User]:
    """Admin uchun: barcha o'qituvchilar (reyting statistikasi bilan, UserSerializer orqali)."""
    return User.objects.filter(role=User.Role.TEACHER).order_by('first_name', 'last_name')


def pending_teachers() -> QuerySet[User]:
    """Admin tasdig'ini kutayotgan (hali tasdiqlanmagan) o'qituvchilar."""
    return User.objects.filter(role=User.Role.TEACHER, is_approved=False).order_by('-created_at')


def linked_accounts(user: User) -> QuerySet[User]:
    """Xuddi shu telefon raqami bilan ro'yxatdan o'tgan BOSHQA akkauntlar
    (bitta real inson — o'qituvchi + ota-ona + o'quvchi kabi bir necha
    rol-akkaunt ochgan bo'lishi mumkin, `phone` UNIQUE emas — apps.accounts.models).
    `phone` bo'sh bo'lsa — bo'sh natija (bo'sh qiymat bo'yicha "bog'lash" mantiqsiz)."""
    if not user.phone:
        return User.objects.none()
    return User.objects.filter(phone=user.phone).exclude(pk=user.pk).order_by('role', 'username')
