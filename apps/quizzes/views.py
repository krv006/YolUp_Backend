"""Quizzes views — yupqa qatlam: HTTP <-> service/selector.

Biznes-logika services.py da, ko'rish huquqi selectors.py da, ruxsatlar
apps.core.permissions registry'sida.
"""
from django.db.models import Count, F, IntegerField, OuterRef, Prefetch, Q, Subquery, Window
from django.db.models.functions import Coalesce
from django.db.models.functions import RowNumber
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.permissions import RequirePerm

from . import ai_jobs, attempts_export, export, selectors, services
from .models import AiQuizJob, AnswerResponse, Question, Quiz
from .serializers import (
    AiQuizCreateSerializer,
    AiQuizJobSerializer,
    GroupReadSerializer,
    ImportSaveSerializer,
    AttemptListSerializer,
    AttemptResultSerializer,
    AttemptSubmitSerializer,
    QuizCreateSerializer,
    QuizDetailSerializer,
    QuizListSerializer,
    QuizTakeSerializer,
    QuizUpdateSerializer,
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


def _import_response(request, preview: dict) -> Response:
    """Import so'rovida `topic` bo'lsa — natija DARHOL doimiy `draft` test
    sifatida saqlanadi (201, to'liq test tafsiloti + `warnings`); aks holda
    eski xatti-harakat: hech narsa saqlanmaydigan preview (200)."""
    if 'topic' not in request.data:
        return Response(preview)
    serializer = ImportSaveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    quiz = services.save_imported_quiz(
        teacher=request.user, preview=preview, topic=data['topic'], course=data.get('course'),
        subject=data.get('subject', ''), title=data.get('title', ''),
    )
    payload = dict(QuizDetailSerializer(quiz, context={'request': request}).data)
    payload['warnings'] = preview.get('warnings', [])
    return Response(payload, status=status.HTTP_201_CREATED)


class QuizListCreateView(generics.ListCreateAPIView):
    filterset_fields = ['course', 'lesson', 'subject']
    search_fields = ['topic', 'title']
    ordering_fields = ['created_at', 'due_at', 'opens_at']

    def get_permissions(self):
        perm = 'quiz.create' if self.request.method == 'POST' else 'quiz.view'
        return [RequirePerm(perm)()]

    def get_queryset(self):
        return selectors.quizzes_for(self.request.user)

    def get_serializer_class(self):
        return QuizListSerializer

    def create(self, request, *args, **kwargs):
        as_draft = request.data.get('status') == Quiz.Status.DRAFT
        serializer = QuizCreateSerializer(data=request.data, context={'draft': as_draft})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        quiz = services.create_quiz(
            teacher=request.user, course=data.get('course'), subject=data.get('subject', ''),
            lesson=data.get('lesson'), topic=data['topic'],
            title=data.get('title', ''), description=data.get('description', ''),
            due_at=data.get('due_at'), opens_at=data.get('opens_at'), questions=data['questions'],
            groups=data.get('groups'), status=Quiz.Status.DRAFT if as_draft else Quiz.Status.PUBLISHED,
        )
        return Response(
            QuizDetailSerializer(quiz, context={'request': request}).data, status=status.HTTP_201_CREATED,
        )


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
        return _import_response(request, result)


class QuizAiGenerateView(APIView):
    """O'qituvchi material (PDF/Word/PowerPoint/Excel/matn) yuklaydi, ixtiyoriy ravishda imtihon qoidalari
    (`rules_file` yoki `rules_text`) ham: AI qoidalarga qarab to'liq test tuzadi (bo'limlar, matn parchalari,
    turli savol turlari, tartib); qoidalar berilmasa — oddiy variantli test. Ish fonda bajariladi: javob darhol
    `202` (+ ish id'si), tayyor bo'lgach `GET .../{id}/` da `quiz` (qoralama test) paydo bo'ladi."""

    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def get(self, request):
        jobs = AiQuizJob.objects.filter(teacher=request.user)[:50]
        return Response(AiQuizJobSerializer(jobs, many=True).data)

    def post(self, request):
        serializer = AiQuizCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        job = ai_jobs.create_job(
            teacher=request.user, uploads=request.FILES.getlist('file'), course=data.get('course'),
            subject=data.get('subject', ''), topic=data['topic'], title=data.get('title', ''),
            standard=data.get('standard', ''), question_count=data['question_count'], language=data.get('language', ''),
            rules_upload=request.FILES.get('rules_file'), rules_text=data.get('rules_text', ''),
            material_text_value=data.get('material_text', ''), exam_name=data.get('exam_name', ''),
        )
        return Response(AiQuizJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class QuizAiJobDetailView(APIView):
    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def get(self, request, pk):
        try:
            job = AiQuizJob.objects.get(pk=pk, teacher=request.user)
        except (AiQuizJob.DoesNotExist, ValueError, TypeError):
            raise NotFound(_('Ish topilmadi.'))
        return Response(AiQuizJobSerializer(job).data)


class QuizGoogleDocImportView(APIView):
    """Ochiq (public — "Havolaga ega har kim ko'ra oladi") Google Docs
    havolasidan test savollarini parse qilib preview qaytaradi. OAuth
    kerak emas — `QuizImportView` bilan bir xil preview shakli."""

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def post(self, request):
        result = services.import_google_doc(url=request.data.get('url'))
        return _import_response(request, result)


class QuizGoogleFormImportView(APIView):
    """Ochiq Google Forms havolasidan savol/variant matnini o'qib preview
    qaytaradi. TO'G'RI JAVOBLAR ANIQLANMAYDI (Google buni ochiq sahifaga
    yubormaydi) — barcha savol `warnings`da, o'qituvchi preview'da
    to'g'ri variantni o'zi belgilaydi."""

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def post(self, request):
        result = services.import_google_form(url=request.data.get('url'))
        return _import_response(request, result)


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


class QuizExportView(APIView):
    """Testni yuklab olish: `?type=pdf|docx|xlsx|csv|json&mode=student|teacher` (standart: pdf, student).

    `student` — o'quvchiga tarqatish uchun (javob kaliti YO'Q), `teacher` — javoblar va Listening skripti bilan.
    Faqat test egasi (o'qituvchi). E'TIBOR: parametr `type` (DRF'ning `format`i content-negotiation uchun band)."""

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def get(self, request, pk):
        import re

        quiz = _get_quiz(request.user, pk)
        fmt = (request.query_params.get('type') or 'pdf').lower()
        mode = (request.query_params.get('mode') or 'student').lower()
        data = QuizDetailSerializer(quiz, context={'request': request}).data
        try:
            content, content_type = export.export_quiz(dict(data), fmt=fmt, mode=mode)
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})
        name = re.sub(r'[^A-Za-z0-9._-]+', '_', f"{quiz.title or quiz.topic}_{mode}").strip('_')[:80] or 'test'
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{name}.{fmt}"'
        return response


class QuizAttemptsExportView(APIView):
    """Test natijalari: `?type=xlsx|csv` (standart xlsx) — har o'quvchining har urinishi va savollar bo'yicha javobi.
    Faqat test egasi (o'qituvchi)."""

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def get(self, request, pk):
        import re

        quiz = _get_quiz(request.user, pk)
        fmt = (request.query_params.get('type') or 'xlsx').lower()
        attempts = selectors.attempts_for(request.user, quiz).select_related('student').prefetch_related(
            Prefetch('answers', queryset=AnswerResponse.objects.all()),
        )
        try:
            content, content_type = attempts_export.build_attempts_export(quiz, list(attempts), fmt)
        except ValueError as exc:
            raise ValidationError({'type': str(exc)})
        name = re.sub(r'[^A-Za-z0-9._-]+', '_', f"{quiz.title or quiz.topic}_natijalar").strip('_')[:80] or 'natijalar'
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{name}.{fmt}"'
        return response


class QuizNotAttemptedView(APIView):
    """Guruhdagi o'quvchilardan bu testni hali topshirmaganlar (guruhsiz testda bo'sh ro'yxat)."""

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def get(self, request, pk):
        from apps.lessons.models import Enrollment

        quiz = _get_quiz(request.user, pk)
        if not quiz.course_id:
            return Response([])
        students = (
            User.objects.filter(enrollments__course_id=quiz.course_id, enrollments__status=Enrollment.Status.APPROVED)
            .exclude(quiz_attempts__quiz=quiz).distinct()
        )
        rows = []
        for student in sorted(students, key=lambda u: (u.get_full_name() or u.username).lower()):
            avatar = student.avatar.url if student.avatar else None
            rows.append({
                'id': str(student.id), 'name': student.get_full_name() or student.username,
                'username': student.username,
                'avatar_url': request.build_absolute_uri(avatar) if avatar else None,
            })
        return Response(rows)


class QuizDetailView(APIView):
    def get_permissions(self):
        perm = 'quiz.view' if self.request.method == 'GET' else 'quiz.create'
        return [RequirePerm(perm)()]

    def get(self, request, pk):
        quiz = _get_quiz(request.user, pk)
        context = {'request': request}
        if request.user.role in _STAFF_ROLES:
            return Response(QuizDetailSerializer(quiz, context=context).data)
        return Response(QuizTakeSerializer(quiz, context=context).data)

    def patch(self, request, pk):
        """Faqat metadata (mavzu/nom/tavsif/muddat/ochilish vaqti) — savollar
        bu orqali o'zgartirilmaydi."""
        quiz = _get_quiz(request.user, pk)
        serializer = QuizUpdateSerializer(
            data=request.data, partial=True, context={'draft': quiz.status == Quiz.Status.DRAFT},
        )
        serializer.is_valid(raise_exception=True)
        quiz = services.update_quiz(teacher=request.user, quiz=quiz, **serializer.validated_data)
        return Response(QuizDetailSerializer(quiz, context={'request': request}).data)

    def delete(self, request, pk):
        quiz = _get_quiz(request.user, pk)
        services.delete_quiz(teacher=request.user, quiz=quiz)
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuizGroupAudioView(APIView):
    """Guruhga audio yuklash (IELTS Listening): `POST` multipart `file` — mavjud
    audio almashtiriladi; `DELETE` — audioni olib tashlaydi. Faqat test egasi."""

    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def post(self, request, pk, group_id):
        quiz = _get_quiz(request.user, pk)
        upload = request.FILES.get('file')
        if upload is None:
            raise ValidationError({'file': _('Audio fayl yuboring.')})
        group = services.set_group_audio(teacher=request.user, quiz=quiz, group_id=group_id, upload=upload)
        return Response(GroupReadSerializer(group, context={'request': request}).data)

    def delete(self, request, pk, group_id):
        quiz = _get_quiz(request.user, pk)
        services.remove_group_audio(teacher=request.user, quiz=quiz, group_id=group_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuizPublishView(APIView):
    """Qoralamani e'lon qiladi — barcha savolda to'g'ri javob belgilangan bo'lishi shart."""

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def post(self, request, pk):
        quiz = _get_quiz(request.user, pk)
        quiz = services.publish_quiz(teacher=request.user, quiz=quiz)
        return Response(QuizDetailSerializer(quiz, context={'request': request}).data)


class QuizAttemptListCreateView(APIView):
    def get_permissions(self):
        perm = 'quiz.attempt' if self.request.method == 'POST' else 'quiz.view'
        return [RequirePerm(perm)()]

    def get(self, request, pk):
        quiz = _get_quiz(request.user, pk)
        answers = AnswerResponse.objects.filter(attempt=OuterRef('pk')).exclude(question__type=Question.Type.ESSAY)
        attempts = selectors.attempts_for(request.user, quiz).annotate(
            attempt_no=Window(RowNumber(), partition_by=[F('student_id')], order_by=F('created_at').asc()),
            question_n=Coalesce(Subquery(
                answers.order_by().values('attempt').annotate(c=Count('pk')).values('c')[:1], output_field=IntegerField(),
            ), 0),
            correct_n=Coalesce(Subquery(
                answers.filter(is_correct=True).order_by().values('attempt').annotate(c=Count('pk')).values('c')[:1],
                output_field=IntegerField(),
            ), 0),
        )
        return Response(AttemptListSerializer(attempts, many=True, context={'request': request}).data)

    def post(self, request, pk):
        quiz = _get_quiz(request.user, pk)
        serializer = AttemptSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = services.submit_attempt(
            student=request.user, quiz=quiz, answers=serializer.validated_data['answers'],
            duration_seconds=serializer.validated_data.get('duration_seconds'),
        )
        return Response(AttemptResultSerializer(attempt).data, status=status.HTTP_201_CREATED)


class QuizStatsView(APIView):
    """O'qituvchi: savollar bo'yicha statistika — `[{question_id, order, label, wrong_rate, attempts_count}]`,
    eng ko'p xato qilinganlari birinchi (`wrong_rate` — foiz). Insho savollari kirmaydi."""

    def get_permissions(self):
        return [RequirePerm('quiz.view')()]

    def get(self, request, pk):
        quiz = _get_quiz(request.user, pk)
        if request.user.role not in _STAFF_ROLES:
            raise PermissionDenied(_("Savollar statistikasi faqat o'qituvchiga."))
        questions = list(quiz.questions.exclude(type=Question.Type.ESSAY).order_by('order', 'created_at'))
        rows = {
            row['question']: row for row in AnswerResponse.objects.filter(attempt__quiz=quiz).values('question').annotate(
                total=Count('pk'), wrong=Count('pk', filter=Q(is_correct=False)),
            )
        }
        result = []
        for position, question in enumerate(questions, 1):
            row = rows.get(question.id)
            if not row or not row['total']:
                continue
            label = ' '.join(question.text.split())
            result.append({
                'question_id': str(question.id), 'order': position,
                'label': label if len(label) <= 80 else label[:79] + '…',
                'wrong_rate': round(row['wrong'] * 100 / row['total']), 'attempts_count': row['total'],
            })
        result.sort(key=lambda item: (-item['wrong_rate'], item['order']))
        return Response(result)


class QuizMiniTestView(APIView):
    """AI: xato qilingan savollar bo'yicha mini-test (`POST {quiz_id, wrong_question_ids}`) — odatdagi AI ish (202),
    natija qoralama test bo'ladi (`GET /quizzes/ai-generate/{id}/`)."""

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        return [RequirePerm('quiz.create')()]

    def post(self, request):
        if not _is_uuid(request.data.get('quiz_id')):
            raise ValidationError({'quiz_id': _("Test id'si kerak.")})
        quiz = _get_quiz(request.user, request.data.get('quiz_id'))
        if request.user.role not in _STAFF_ROLES or quiz.course.teacher_id != request.user.id:
            raise PermissionDenied(_("Bu test sizning guruhingizniki emas."))
        raw = request.data.get('wrong_question_ids')
        if not isinstance(raw, list) or not 1 <= len(raw) <= 30:
            raise ValidationError({'wrong_question_ids': _("1 tadan 30 tagacha savol id'si ro'yxati kerak.")})
        questions = list(quiz.questions.filter(pk__in=[str(i) for i in raw if _is_uuid(i)]).prefetch_related('options'))
        if not questions:
            raise ValidationError({'wrong_question_ids': _("Bu testda bunday savol topilmadi.")})
        material = ai_jobs.mini_test_material(quiz, questions)
        job = ai_jobs.create_job(
            teacher=request.user, uploads=[], course=quiz.course, subject='',
            topic=f"{quiz.title}: xato qilingan mavzular"[:200], title=f'{quiz.title} — mini-test'[:200],
            question_count=min(20, max(5, len(questions) * 2)), material_text_value=material,
        )
        return Response(AiQuizJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


def _is_uuid(value) -> bool:
    import uuid

    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False
