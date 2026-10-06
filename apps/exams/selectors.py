"""Exams selector qatlami — "kim qaysi imtihonni ko'radi" (apps.quizzes.selectors bilan bir xil naqsh)."""
from django.db.models import Q, QuerySet

from apps.accounts.models import ParentChildLink, User
from apps.lessons.models import Enrollment

from .models import Exam

_ENROLLED = Enrollment.Status.APPROVED
_APPROVED = ParentChildLink.Status.APPROVED


def exams_for(user: User) -> QuerySet[Exam]:
    qs = Exam.objects.select_related('course')
    if user.role == User.Role.TEACHER:
        return qs.filter(Q(course__teacher=user) | Q(created_by=user)).distinct()
    if user.role == User.Role.STUDENT:
        return qs.filter(
            course__enrollments__student=user, course__enrollments__status=_ENROLLED,
        ).distinct()
    if user.role == User.Role.PARENT:
        return qs.filter(
            course__enrollments__status=_ENROLLED,
            course__enrollments__student__parent_links__parent=user,
            course__enrollments__student__parent_links__status=_APPROVED,
        ).distinct()
    return qs  # ADMIN / SUPER_ADMIN


def enrolled_students(exam: Exam) -> QuerySet[User]:
    return User.objects.filter(
        enrollments__course=exam.course, enrollments__status=_ENROLLED,
    ).distinct().order_by('first_name', 'last_name', 'username')


def children_of(parent: User) -> QuerySet[User]:
    return User.objects.filter(
        parent_links__parent=parent, parent_links__status=_APPROVED,
    )
