"""Exams views — yupqa qatlam: HTTP <-> service/selector.

Biznes-logika services.py da, ko'rish huquqi selectors.py da, ruxsatlar
apps.core.permissions registry'sida (`exam.manage` / `exam.view` / `exam.take`).
"""
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RequirePerm

from . import selectors, services
from .models import Exam
from .serializers import (
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


class ExamReminderView(APIView):
    """Shaxsiy eslatma: `POST {minutes_before?}` / `DELETE` — imtihon boshlanishidan oldin bildirishnoma."""

    permission_classes = [RequirePerm('exam.view')]

    def post(self, request, pk):
        from apps.lessons import services as lesson_services
        from apps.lessons.models import ReminderPref

        exam = selectors.exams_for(request.user).filter(pk=pk).first()
        if exam is None:
            raise NotFound(_('Imtihon topilmadi.'))
        if exam.starts_at <= timezone.now():
            raise ValidationError({'detail': _("Faqat boshlanmagan imtihonga eslatma qo'yiladi.")})
        minutes = lesson_services._reminder_minutes(request.data.get('minutes_before'), request.user)
        pref, _created = ReminderPref.objects.update_or_create(
            user=request.user, kind=ReminderPref.Kind.EXAM, target_id=exam.id, defaults={'minutes_before': minutes, 'sent_at': None},
        )
        return Response({'has_reminder': True, 'minutes_before': pref.minutes_before})

    def delete(self, request, pk):
        from apps.lessons.models import ReminderPref

        ReminderPref.objects.filter(user=request.user, kind=ReminderPref.Kind.EXAM, target_id=pk).delete()
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
        rows = [exam_summary(exam, now) for exam in exams]
        from apps.lessons.models import ReminderPref

        mine = dict(ReminderPref.objects.filter(
            user=request.user, kind=ReminderPref.Kind.EXAM, target_id__in=[exam.id for exam in exams],
        ).values_list('target_id', 'minutes_before'))
        is_student = request.user.role == 'student'
        for exam, row in zip(exams, rows):
            row['has_reminder'] = exam.id in mine
            row['reminder_minutes'] = mine.get(exam.id)
            if is_student:
                row['my_total'] = services.my_total(exam, request.user) if row.get('state') == 'finished' else None
        return Response(rows)

    def post(self, request):
        serializer = ExamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        exam = services.create_exam(
            teacher=request.user, course=data['course'], template_ref=data['template'],
            title=data['title'], starts_at=data.get('starts_at'), sections=data['sections'],
            start_now=data.get('start_now', False),
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


class ExamNextSectionView(APIView):
    """O'quvchi joriy bo'limni muddatidan oldin tugatib keyingisiga o'tadi (orqaga qaytish yo'q)."""

    permission_classes = [RequirePerm('exam.take')]

    def post(self, request, pk):
        exam = _get_exam(request.user, pk)
        return Response(current_response(
            services.next_section(student=request.user, exam=exam), request=request,
        ))


class ExamFocusView(APIView):
    """Imtihon davomida oynadan chiqish / tashqaridan nusxa qo'yishga urinishni qayd etadi."""

    permission_classes = [RequirePerm('exam.take')]

    def post(self, request, pk):
        exam = _get_exam(request.user, pk)
        count = services.record_focus(student=request.user, exam=exam, kind=str(request.data.get('kind') or ''))
        return Response({'recorded': count})


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


class ExamResultPdfView(APIView):
    """`GET /exams/{id}/results/{student_id}/pdf/` — o'quvchi natijasi PDF (o'quvchi o'zi, ota-onasi, o'qituvchi)."""

    permission_classes = [RequirePerm('exam.view')]

    def get(self, request, pk, student_id):
        from django.http import HttpResponse

        from . import report

        exam = _get_exam(request.user, pk)
        item = services.student_detail(user=request.user, exam=exam, student_id=student_id)
        if item.get('hidden'):
            raise ValidationError({'detail': _("Natijalar imtihon tugagach ko'rinadi.")})
        if not item.get('participated'):
            raise NotFound(_("Bu o'quvchi imtihonda qatnashmagan."))
        response = HttpResponse(report.build_pdf(exam, item), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="natija-{exam.id}.pdf"'
        return response


class ExamMistakesPracticeView(APIView):
    """O'quvchi: imtihondagi xato savollar bo'yicha AI mashq (`POST {count?, language?}`) — saqlanmaydi, to'g'ridan-to'g'ri qaytadi."""

    permission_classes = [RequirePerm('exam.take')]

    def post(self, request, pk):
        from apps.quizzes import student_ai

        exam = _get_exam(request.user, pk)
        attempt = exam.attempts.filter(student=request.user).first()
        if attempt is None or services.list_results(user=request.user, exam=exam)['results'][0].get('hidden'):
            raise ValidationError({'detail': _("Natijalar imtihon tugagach ko'rinadi.")})
        wrong = [
            answer.question for answer in attempt.answers.select_related('question').prefetch_related('question__options')
            if answer.earned_points < answer.question.points
        ]
        if not wrong:
            raise ValidationError({'detail': _("Xato savol topilmadi — mashq kerak emas.")})
        material = '\n'.join(
            f"{index}. {' '.join(question.text.split())}" for index, question in enumerate(wrong[:15], 1)
        )
        return Response(student_ai.practice(
            request.user, topic=f'{exam.title}: xato qilingan mavzular', count=request.data.get('count') or 5,
            material=material, language=request.data.get('language') or '',
        ))


class ExamShareResultsView(APIView):
    """`{to: "group_chat"}` — natijalar jadvali guruh chatiga xabar bo'lib boradi (imtihon tugagach, faqat o'qituvchi)."""

    permission_classes = [RequirePerm('exam.manage')]

    def post(self, request, pk):
        exam = _get_exam(request.user, pk)
        return Response(services.share_results(
            teacher=request.user, exam=exam, to=request.data.get('to') or 'group_chat',
        ))


class ExamResultDetailView(APIView):
    permission_classes = [RequirePerm('exam.view')]

    def get(self, request, pk, student_id):
        exam = _get_exam(request.user, pk)
        return Response(services.student_detail(user=request.user, exam=exam, student_id=student_id))


class ExamWritingAiView(APIView):
    """O'qituvchi IELTS Writing uchun AI tahlilini so'raydi (natija birozdan keyin `results/<student>/` da)."""

    permission_classes = [RequirePerm('exam.manage')]

    def post(self, request, pk, student_id):
        exam = _get_exam(request.user, pk)
        return Response(services.request_writing_ai(teacher=request.user, exam=exam, student_id=student_id))


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
