"""Homework views — yupqa qatlam (board uslubi)."""
from django.http import FileResponse
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RequirePerm, user_has_perm

from . import services


class AssignmentListCreateView(APIView):
    """GET ?course=<id> — kurs vazifalari; POST — yangi vazifa (o'qituvchi).

    POST multipart yoki JSON qabul qiladi: rich matn (body) + ixtiyoriy
    biriktirilgan fayl (attachment: Word/PDF/rasm).
    """

    permission_classes = [RequirePerm('homework.view')]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        return Response(services.list_assignments(
            user=request.user, course_id=request.query_params.get('course'),
        ))

    def post(self, request):
        if not user_has_perm(request.user, 'homework.assign'):
            return Response({'detail': "Vazifa berish faqat o'qituvchi uchun."}, status=403)
        data = services.create_assignment(
            teacher=request.user,
            course_id=request.data.get('course_id'),
            title=request.data.get('title') or '',
            description=request.data.get('description') or '',
            body=request.data.get('body') or '',
            due_at=request.data.get('due_at') or None,
            skill_key=request.data.get('skill_key') or '',
            lesson_id=request.data.get('lesson_id') or None,
            extra_instructions=request.data.get('extra_instructions') or '',
            attachment=request.FILES.get('attachment'),
        )
        return Response(data, status=201)


class AssignmentDetailView(APIView):
    permission_classes = [RequirePerm('homework.view')]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, assignment_id):
        return Response(services.get_assignment(user=request.user, assignment_id=assignment_id))

    def patch(self, request, assignment_id):
        """Vazifani tahrirlash — faqat yuborilgan maydonlar o'zgaradi
        (masalan faqat `due_at`, boshqa hech narsaga tegilmaydi)."""
        if not user_has_perm(request.user, 'homework.assign'):
            return Response({'detail': "Tahrirlash faqat o'qituvchi uchun."}, status=403)

        kwargs = {}
        for field in ('title', 'description', 'body', 'due_at', 'skill_key', 'lesson_id', 'extra_instructions'):
            if field in request.data:
                kwargs[field] = request.data.get(field)
        if 'attachment' in request.FILES:
            kwargs['attachment'] = request.FILES.get('attachment')

        data = services.update_assignment(teacher=request.user, assignment_id=assignment_id, **kwargs)
        return Response(data)

    def delete(self, request, assignment_id):
        if not user_has_perm(request.user, 'homework.assign'):
            return Response({'detail': "O'chirish faqat o'qituvchi uchun."}, status=403)
        services.delete_assignment(teacher=request.user, assignment_id=assignment_id)
        return Response(status=204)


class AssignmentFileView(APIView):
    """O'qituvchi biriktirgan vazifa faylini yuklab olish."""

    permission_classes = [RequirePerm('homework.view')]

    def get(self, request, assignment_id):
        path, name = services.assignment_file(user=request.user, assignment_id=assignment_id)
        return FileResponse(open(path, 'rb'), as_attachment=True, filename=name)


class SubmitView(APIView):
    """O'quvchi faylini yuklaydi — topshiriq o'qituvchiga baholash uchun tushadi."""

    permission_classes = [RequirePerm('homework.submit')]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, assignment_id):
        data = services.submit(
            student=request.user,
            assignment_id=assignment_id,
            upload=request.FILES.get('file'),
        )
        return Response(data, status=201)


class SubmissionDetailView(APIView):
    """GET — topshiriq va (o'qituvchi tasdiqlagach) natija."""

    permission_classes = [RequirePerm('homework.view')]

    def get(self, request, submission_id):
        return Response(services.get_submission(user=request.user, submission_id=submission_id))


class SubmissionFileView(APIView):
    """Yuklangan faylni ko'rish/yuklab olish (faqat aloqador foydalanuvchilar)."""

    permission_classes = [RequirePerm('homework.view')]

    def get(self, request, submission_id):
        path, name = services.submission_file(user=request.user, submission_id=submission_id)
        return FileResponse(open(path, 'rb'), as_attachment=True, filename=name)


class RecheckView(APIView):
    """AI tekshiruv olib tashlangan — eski mijozlar uchun faqat tushunarli xato qaytaradi."""

    permission_classes = [RequirePerm('homework.assign')]

    def post(self, request, submission_id):
        return Response(services.recheck(user=request.user, submission_id=submission_id))


class SubmissionReviewView(APIView):
    """O'qituvchi topshiriqni baholaydi: `overall_score` (0-100, shart), ixtiyoriy
    `grade` va `result` (izoh). Shundan keyingina o'quvchi natijani ko'radi."""

    permission_classes = [RequirePerm('homework.assign')]

    def post(self, request, submission_id):
        data = services.review_submission(
            teacher=request.user,
            submission_id=submission_id,
            overall_score=request.data.get('overall_score'),
            grade=request.data.get('grade') or '',
            result=request.data.get('result'),
        )
        return Response(data)


class AssignmentFocusView(APIView):
    """O'quvchi vazifa sahifasidan chiqib-kirishini belgilaydi (vaqt kuzatuvi)."""

    permission_classes = [RequirePerm('homework.submit')]

    def post(self, request, assignment_id):
        data = services.record_focus(
            student=request.user,
            assignment_id=assignment_id,
            kind=request.data.get('kind') or '',
        )
        return Response(data)


class ProgressReportView(APIView):
    """Uspevaemost: fan bo'yicha uy vazifasi bajarilish foizi + o'rtacha
    ball, va umumiy (barcha fanlar) yagona ko'rsatkich.

    O'quvchi — o'zinikini ko'radi (student_id shart emas).
    Ota-ona — ?student_id=<uuid> bilan, faqat APPROVED bog'langan bolasiniki.
    """

    permission_classes = [RequirePerm('homework.view')]

    def get(self, request):
        report = services.get_progress_report(
            user=request.user, student_id=request.query_params.get('student_id'),
        )
        return Response(report)
