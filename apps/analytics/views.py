from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.permissions import RequirePerm

from . import dashboard, selectors


class DashboardSummaryView(APIView):
    """Joriy holat: faol o'quvchi/o'qituvchi/kurs, davomat, reyting, top ro'yxatlar."""

    permission_classes = [RequirePerm('audit.view')]

    def get(self, request):
        return Response(selectors.dashboard_summary())


class DashboardTrendsView(APIView):
    """`?period=day|week|month|year` — kesim bo'yicha vaqt qatorlari."""

    permission_classes = [RequirePerm('audit.view')]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        if period not in selectors.PERIOD_BUCKET_COUNTS:
            raise ValidationError({'period': _("Noto'g'ri davr — day/week/month/year bo'lishi kerak.")})
        return Response(selectors.dashboard_trends(period))


class TeacherDashboardView(APIView):
    """O'qituvchi bosh sahifasi: to'rtta ko'rsatkich bitta javobda (`/dashboard/teacher/`)."""

    def get(self, request):
        if request.user.role != User.Role.TEACHER:
            raise PermissionDenied(_("Faqat o'qituvchi uchun."))
        return Response(dashboard.teacher_overview(request.user))


class ActivityView(APIView):
    """"So'nggi faollik": `?limit=10` (ko'pi bilan 50) — `[{id, category, title, body, link_type, link_id, created_at}]`."""

    def get(self, request):
        return Response(dashboard.recent_activity(request.user, request.query_params.get('limit')))


class MyTrendsView(APIView):
    """O'qituvchining o'z kurslari bo'yicha vaqt qatori (`?period=day|week|month|year`, standart `week`)."""

    permission_classes = [RequirePerm('stats.view_own')]

    def get(self, request):
        if request.user.role != User.Role.TEACHER:
            raise PermissionDenied(_("Faqat o'qituvchi uchun."))
        period = request.query_params.get('period', 'week')
        if period not in selectors.PERIOD_BUCKET_COUNTS:
            raise ValidationError({'period': _("Noto'g'ri davr — day/week/month/year bo'lishi kerak.")})
        return Response(selectors.teacher_trends(request.user, period))


class MyAnalyticsView(APIView):
    """Workspace > Tahlil — shaxsiy statistika. O'quvchi uchun test natijalari
    tarixi, o'qituvchi uchun umumiy ko'rsatkichlar + kurslar orasidagi
    solishtiruv (rol bo'yicha `RequirePerm('stats.view_own')` cheklaydi,
    hozircha faqat TEACHER va STUDENT rolida bor)."""

    permission_classes = [RequirePerm('stats.view_own')]

    def get(self, request):
        if request.user.role == User.Role.STUDENT:
            return Response(selectors.student_own_stats(request.user))
        return Response(selectors.teacher_own_stats(request.user))
