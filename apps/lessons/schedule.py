"""`GET /schedule/?from=&to=` — jadval: darslar VA guruhga berilgan testlar bitta ro'yxatda (vaqt bo'yicha).

Frontend/mobil darslar va testlarni alohida so'rab birlashtirmasin. Har element `type` (`lesson` | `quiz`) bilan keladi.
Ko'rinish huquqi mavjud selektorlar bilan bir xil: `lessons_for` va `quizzes_for` (o'quvchi ochilmagan/o'ziga berilmagan testni
ko'rmaydi, ota-ona faqat tasdiqlangan farzandiniki, o'qituvchi faqat o'z guruhlariniki).
"""
from datetime import timedelta

from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.quizzes import selectors as quiz_selectors
from apps.quizzes.models import Quiz

from . import selectors
from .filters import allowed_student, parse_bound
from .models import Enrollment

MAX_RANGE = timedelta(days=100)  # javob cheksiz kattalashmasin


class ScheduleView(APIView):
    """`?from=` va `?to=` majburiy (sana `YYYY-MM-DD` yoki ISO sana-vaqt; oralig'i 100 kundan oshmasin).
    Ixtiyoriy: `?course=<uuid>`, `?student=<uuid>` (ota-ona: farzand)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = parse_bound(request.query_params.get('from'), end=False)
        end = parse_bound(request.query_params.get('to'), end=True)
        if start is None or end is None:
            raise ValidationError({'detail': _("`from` va `to` majburiy.")})
        if end < start:
            raise ValidationError({'detail': _("`to` `from`dan oldin bo'lmasin.")})
        if end - start > MAX_RANGE:
            raise ValidationError({'detail': _("Oraliq 100 kundan oshmasin.")})
        course = request.query_params.get('course')
        student = request.query_params.get('student')
        if student:
            allowed_student(request.user, student)

        lessons = selectors.lessons_for(request.user).filter(starts_at__gte=start, starts_at__lte=end)
        quizzes = quiz_selectors.quizzes_for(request.user).filter(
            course__isnull=False, status=Quiz.Status.PUBLISHED,  # bankdagi guruhsiz va qoralama testlar jadvalda yo'q
        ).annotate(
            sched_start=Coalesce('opens_at', 'created_at'),  # ochilish vaqti; belgilanmagan bo'lsa — berilgan payt
        ).annotate(
            sched_end=Coalesce('due_at', 'sched_start'),
        ).filter(sched_start__lte=end, sched_end__gte=start)
        if course:
            lessons, quizzes = lessons.filter(course_id=course), quizzes.filter(course_id=course)
        if student:
            lessons = lessons.filter(course__enrollments__student_id=student, course__enrollments__status=Enrollment.Status.APPROVED)
            quizzes = quizzes.filter(course__enrollments__student_id=student, course__enrollments__status=Enrollment.Status.APPROVED)

        rows = [{
            'type': 'lesson', 'id': str(lesson.id), 'title': lesson.title or lesson.course.title,
            'course': str(lesson.course_id), 'course_title': lesson.course.title,
            'starts_at': lesson.starts_at, 'ends_at': lesson.starts_at + timedelta(minutes=lesson.duration_min),
            'status': lesson.status,
        } for lesson in lessons.distinct()]
        rows += [{
            'type': 'quiz', 'id': str(quiz.id), 'title': quiz.title or quiz.topic,
            'course': str(quiz.course_id), 'course_title': quiz.course.title,
            'starts_at': quiz.sched_start, 'ends_at': quiz.sched_end if quiz.due_at else None,
            'opens_at': quiz.opens_at, 'due_at': quiz.due_at, 'status': quiz.status,
            'subject': quiz.subject, 'time_limit_minutes': quiz.time_limit_minutes,
        } for quiz in quizzes.select_related('course').distinct()]
        rows.sort(key=lambda row: (row['starts_at'], row['type']))
        return Response({'from': start, 'to': end, 'count': len(rows), 'results': rows})
