"""Exams views — yupqa qatlam: HTTP <-> service/selector.

Biznes-logika services.py da, ko'rish huquqi selectors.py da, ruxsatlar
apps.core.permissions registry'sida (`exam.manage` / `exam.view` / `exam.take`).
"""
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RequirePerm

from . import selectors, services, writing
from .models import Exam
from .serializers import (
    AIApproveSerializer,
    AnswersSerializer,
    ExamCreateSerializer,
    ExamUpdateSerializer,
    ManualScoresSerializer,
    TemplateWriteSerializer,
    current_response,
    exam_detail,
    exam_summary,
)


def _get_exam(user, pk) -> Exam:
    """Faqat foydalanuvchi ko'rishga haqli imtihon (boshqa guruhniki — 404)."""
    try:
        return selectors.exams_for(user).get(pk=pk)
    except (Exam.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Imtihon topilmadi.'))


class TemplateListCreateView(APIView):
    def get_permissions(self):
        perm = 'exam.manage' if self.request.method == 'POST' else 'exam.view'
        return [RequirePerm(perm)()]

    def get(self, request):
        return Response(services.list_templates(request.user))

    def post(self, request):
        serializer = TemplateWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = services.create_template(owner=request.user, **serializer.validated_data)
        return Response({
            'id': str(template.id), 'kind': 'custom', 'name': template.name,
            'description': template.description, 'items': template.items, 'scoring': template.scoring,
        }, status=status.HTTP_201_CREATED)


class TemplateDeleteView(APIView):
    permission_classes = [RequirePerm('exam.manage')]

    def delete(self, request, pk):
        services.delete_template(owner=request.user, template_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExamListCreateView(APIView):
    def get_permissions(self):
        perm = 'exam.manage' if self.request.method == 'POST' else 'exam.view'
        return [RequirePerm(perm)()]

    def get(self, request):
        now = timezone.now()
        exams = selectors.exams_for(request.user)
        course = request.query_params.get('course')
        if course:
            exams = exams.filter(course_id=course)
        return Response([exam_summary(exam, now) for exam in exams])

    def post(self, request):
        serializer = ExamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        exam = services.create_exam(
            teacher=request.user, course=data['course'], template_ref=data['template'],
            title=data['title'], starts_at=data['starts_at'], sections=data['sections'],
        )
        return Response(exam_detail(exam, request.user), status=status.HTTP_201_CREATED)


class ExamDetailView(APIView):
    def get_permissions(self):
        perm = 'exam.view' if self.request.method == 'GET' else 'exam.manage'
        return [RequirePerm(perm)()]

    def get(self, request, pk):
        return Response(exam_detail(_get_exam(request.user, pk), request.user))

    def patch(self, request, pk):
        exam = _get_exam(request.user, pk)
        serializer = ExamUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam = services.update_exam(teacher=request.user, exam=exam, **serializer.validated_data)
        return Response(exam_detail(exam, request.user))

    def delete(self, request, pk):
        services.delete_exam(teacher=request.user, exam=_get_exam(request.user, pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExamCurrentView(APIView):
    """O'quvchining joriy holati — qaysi bo'lim/tanaffus, server vaqti,
    savollar (javob kalitisiz) va oldin saqlangan javoblar. Sahifa yangilansa
    ham shu endpoint holatni tiklaydi."""

    permission_classes = [RequirePerm('exam.take')]

    def get(self, request, pk):
        exam = _get_exam(request.user, pk)
        return Response(current_response(
            services.current_payload(student=request.user, exam=exam), request=request,
        ))


class ExamAnswersView(APIView):
    """Avtosaqlash: joriy bo'lim javoblari. Qayta yuborsa ustiga yozadi."""

    permission_classes = [RequirePerm('exam.take')]

    def put(self, request, pk):
        exam = _get_exam(request.user, pk)
        serializer = AnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saved = services.save_answers(
            student=request.user, exam=exam, answers=serializer.validated_data['answers'],
        )
        return Response({'saved': saved, 'server_now': timezone.now()})


class ExamFinishView(APIView):
    """Imtihonni muddatidan oldin yakunlash (qaytib kirib bo'lmaydi)."""

    permission_classes = [RequirePerm('exam.take')]

    def post(self, request, pk):
        exam = _get_exam(request.user, pk)
        attempt = services.finish_attempt(student=request.user, exam=exam)
        return Response({'finished_at': attempt.finished_at})


class ExamResultsView(APIView):
    permission_classes = [RequirePerm('exam.view')]

    def get(self, request, pk):
        exam = _get_exam(request.user, pk)
        return Response(services.list_results(user=request.user, exam=exam))


class ExamResultDetailView(APIView):
    permission_classes = [RequirePerm('exam.view')]

    def get(self, request, pk, student_id):
        exam = _get_exam(request.user, pk)
        return Response(services.student_detail(user=request.user, exam=exam, student_id=student_id))


class ExamManualScoreView(APIView):
    """O'qituvchi qo'lda baholaydigan bo'limlar (IELTS Writing/Speaking va h.k.)."""

    permission_classes = [RequirePerm('exam.manage')]

    def put(self, request, pk, student_id):
        exam = _get_exam(request.user, pk)
        serializer = ManualScoresSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.set_manual_scores(
            teacher=request.user, exam=exam, student_id=student_id,
            scores=serializer.validated_data['scores'],
        )
        return Response(result)


class ExamAIGradeView(APIView):
    """IELTS Writing'ni AI bilan baholashni boshlaydi (yoki xatodan keyin qayta uradi).
    Odatda cron o'zi boshlaydi; bu — qo'lda ishga tushirish. Fon oqimida ishlaydi:
    `202` va keyin natijani `results/{student_id}/` dan `ai.writing.status` bilan kuzating."""

    permission_classes = [RequirePerm('exam.manage')]

    def post(self, request, pk, student_id):
        exam = _get_exam(request.user, pk)
        data = writing.request_check(teacher=request.user, exam=exam, student_id=student_id)
        return Response(data, status=status.HTTP_202_ACCEPTED)


class ExamAIApproveView(APIView):
    """O'qituvchi AI taklifini tasdiqlaydi (ixtiyoriy `band` bilan o'zgartirib)."""

    permission_classes = [RequirePerm('exam.manage')]

    def post(self, request, pk, student_id):
        exam = _get_exam(request.user, pk)
        serializer = AIApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        writing.approve(
            teacher=request.user, exam=exam, student_id=student_id, band=serializer.validated_data.get('band'),
        )
        return Response(services.student_detail(user=request.user, exam=exam, student_id=student_id))
