"""Quizzes views — yupqa qatlam: HTTP <-> service/selector.

Biznes-logika services.py da, ko'rish huquqi selectors.py da, ruxsatlar
apps.core.permissions registry'sida.
"""
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.permissions import RequirePerm

from . import selectors, services
from .models import Quiz
from .serializers import (
    AttemptListSerializer,
    AttemptResultSerializer,
    AttemptSubmitSerializer,
    QuizCreateSerializer,
    QuizDetailSerializer,
    QuizListSerializer,
    QuizTakeSerializer,
)

_STAFF_ROLES = (User.Role.TEACHER, User.Role.ADMIN, User.Role.SUPER_ADMIN)


def _get_quiz(user: User, pk) -> Quiz:
    """Faqat foydalanuvchi ko'rishga haqli test qaytariladi — aks holda
    boshqa kursning testi ko'rinmasin (queryset scoped, 404, apps.lessons
    bilan bir xil naqsh)."""
    try:
        return selectors.quizzes_for(user).get(pk=pk)
    except (Quiz.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Test topilmadi.'))


class QuizListCreateView(generics.ListCreateAPIView):
    filterset_fields = ['course', 'lesson']
    ordering_fields = ['created_at', 'due_at', 'opens_at']

    def get_permissions(self):
        perm = 'quiz.create' if self.request.method == 'POST' else 'quiz.view'
        return [RequirePerm(perm)()]

    def get_queryset(self):
        return selectors.quizzes_for(self.request.user)

    def get_serializer_class(self):
        return QuizListSerializer

    def create(self, request, *args, **kwargs):
        serializer = QuizCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        quiz = services.create_quiz(
            teacher=request.user, course=data.get('course'), subject=data.get('subject', ''),
            lesson=data.get('lesson'),
            title=data['title'], description=data.get('description', ''),
            due_at=data.get('due_at'), opens_at=data.get('opens_at'), questions=data['questions'],
        )
        return Response(QuizDetailSerializer(quiz).data, status=status.HTTP_201_CREATED)


class QuizImportView(APIView):
    """`.docx` yoki `.xlsx` fayldan test savollarini parse qilib preview
    qaytaradi — hech narsa saqlanmaydi. O'qituvchi ko'rib chiqib,
    `QuizListCreateView` orqali (course/title bilan birga) haqiqiy testni
    yaratadi."""

    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def post(self, request):
        result = services.import_quiz_file(upload=request.FILES.get('file'))
        return Response(result)


_TEMPLATE_CONTENT_TYPES = {
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}


class QuizTemplateView(APIView):
    """Bo'sh shablon faylni yuklab olish — `?type=docx|xlsx&count=10`.

    E'TIBOR: query parametr ataylab `type` (`format` EMAS) — DRF'ning o'zi
    `format` nomli query parametrni content-negotiation uchun band qilib
    qo'ygan (mos renderer topilmasa, 404 qaytaradi — `format=docx` ishlatilsa
    shu tuzoqqa tushib qolamiz).

    Qaytgan fayl `QuizImportView` orqali to'ldirib qaytadan import qilinishi
    uchun mo'ljallangan (`apps.quizzes.template_export`)."""

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def get(self, request):
        fmt = (request.query_params.get('type') or 'docx').lower()
        content = services.build_quiz_template(fmt=fmt, count=request.query_params.get('count'))
        content_type = _TEMPLATE_CONTENT_TYPES.get(fmt, 'application/octet-stream')
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="test_shabloni.{fmt}"'
        return response


class QuizDetailView(APIView):
    def get_permissions(self):
        perm = 'quiz.create' if self.request.method == 'DELETE' else 'quiz.view'
        return [RequirePerm(perm)()]

    def get(self, request, pk):
        quiz = _get_quiz(request.user, pk)
        if request.user.role in _STAFF_ROLES:
            return Response(QuizDetailSerializer(quiz).data)
        return Response(QuizTakeSerializer(quiz).data)

    def delete(self, request, pk):
        quiz = _get_quiz(request.user, pk)
        services.delete_quiz(teacher=request.user, quiz=quiz)
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuizAttemptListCreateView(APIView):
    def get_permissions(self):
        perm = 'quiz.attempt' if self.request.method == 'POST' else 'quiz.view'
        return [RequirePerm(perm)()]

    def get(self, request, pk):
        quiz = _get_quiz(request.user, pk)
        attempts = selectors.attempts_for(request.user, quiz)
        return Response(AttemptListSerializer(attempts, many=True).data)

    def post(self, request, pk):
        quiz = _get_quiz(request.user, pk)
        serializer = AttemptSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = services.submit_attempt(
            student=request.user, quiz=quiz, answers=serializer.validated_data['answers'],
        )
        return Response(AttemptResultSerializer(attempt).data, status=status.HTTP_201_CREATED)
