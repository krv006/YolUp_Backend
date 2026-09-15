"""Quizzes selector qatlami — "kim nimani ko'radi" qoidalari bitta joyda
(apps.lessons.selectors.lessons_for bilan bir xil naqsh)."""
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Enrollment

from .models import Quiz, QuizAttempt

_ENROLLED = Enrollment.Status.APPROVED
_APPROVED = ParentChildLink.Status.APPROVED


def quizzes_for(user: User) -> QuerySet[Quiz]:
    qs = Quiz.objects.select_related('course', 'lesson')
    if user.role == User.Role.TEACHER:
        return qs.filter(course__teacher=user)
    # O'quvchi/ota-ona hali "ochilish kuni" kelmagan testni ko'rmaydi —
    # o'qituvchi esa tayyorlash uchun har doim ko'radi (yuqorida qaytdi).
    not_yet_opened = Q(opens_at__isnull=False, opens_at__gt=timezone.now())
    if user.role == User.Role.STUDENT:
        return qs.filter(
            course__enrollments__student=user, course__enrollments__status=_ENROLLED,
        ).exclude(not_yet_opened)
    if user.role == User.Role.PARENT:
        return qs.filter(
            course__enrollments__status=_ENROLLED,
            course__enrollments__student__parent_links__parent=user,
            course__enrollments__student__parent_links__status=_APPROVED,
        ).exclude(not_yet_opened).distinct()
    return qs


def attempts_for(user: User, quiz: Quiz) -> QuerySet[QuizAttempt]:
    qs = QuizAttempt.objects.filter(quiz=quiz).select_related('student')
    if user.role == User.Role.STUDENT:
        return qs.filter(student=user)
    if user.role == User.Role.PARENT:
        return qs.filter(
            student__parent_links__parent=user,
            student__parent_links__status=_APPROVED,
        )
    # TEACHER (kursi tekshirilgan — views.py) / ADMIN / SUPER_ADMIN — hammasi.
    return qs
