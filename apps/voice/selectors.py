"""Voice selector qatlami — "kim nimani ko'radi" qoidalari (apps.quizzes.selectors bilan bir xil naqsh)."""
from django.db.models import QuerySet

from apps.accounts.models import User
from apps.lessons.models import Enrollment

from .models import VoiceRoom

_ENROLLED = Enrollment.Status.APPROVED


def rooms_for(user: User, course_id=None) -> QuerySet[VoiceRoom]:
    qs = VoiceRoom.objects.select_related('course', 'created_by')
    if user.role == User.Role.TEACHER:
        qs = qs.filter(course__teacher=user)
    elif user.role == User.Role.STUDENT:
        qs = qs.filter(
            course__enrollments__student=user, course__enrollments__status=_ENROLLED,
        ).distinct()
    else:
        qs = qs.none()
    if course_id:
        qs = qs.filter(course_id=course_id)
    return qs
