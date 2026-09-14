"""Board views — yupqa qatlam."""
from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RequirePerm

from . import services
from .periodic_table_data import PERIODIC_TABLE


class PeriodicTableView(APIView):
    """Davriy jadval — darsga/xonaga bog'liq emas, shuning uchun `lesson_id`
    talab qilmaydi (`room.token` o'rniga oddiy autentifikatsiya yetarli)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PERIODIC_TABLE)


class BoardView(APIView):
    """GET: doska holati (polling). Chizish ruxsati ham shu javobda."""

    permission_classes = [RequirePerm('room.token')]

    def get(self, request, lesson_id):
        return Response(services.get_board(user=request.user, lesson_id=lesson_id))


class StrokeView(APIView):
    permission_classes = [RequirePerm('room.token')]

    def post(self, request, lesson_id):
        stroke = services.add_stroke(
            user=request.user, lesson_id=lesson_id,
            sheet_index=request.data.get('sheet', 0),
            stroke=request.data.get('stroke') or {},
        )
        return Response(stroke, status=201)


class SheetView(APIView):
    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request, lesson_id):
        index = services.add_sheet(user=request.user, lesson_id=lesson_id)
        return Response({'index': index}, status=201)


class EraseView(APIView):
    permission_classes = [RequirePerm('room.token')]

    def post(self, request, lesson_id):
        removed = services.erase_strokes(
            user=request.user, lesson_id=lesson_id,
            sheet_index=request.data.get('sheet', 0),
            stroke_ids=request.data.get('stroke_ids') or [],
            reason=request.data.get('reason'),
        )
        return Response({'removed': removed})


class GrantView(APIView):
    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request, lesson_id):
        services.grant_draw(
            teacher=request.user, lesson_id=lesson_id,
            student_id=request.data.get('student_id'),
        )
        return Response({'ok': True})


class SolveView(APIView):
    """Photomath uslubi: formula matnini yechish (SymPy)."""

    permission_classes = [RequirePerm('room.token')]

    def post(self, request, lesson_id):
        result = services.solve_formula(
            user=request.user, lesson_id=lesson_id, expr=request.data.get('expr'),
        )
        return Response(result)


class PdfView(APIView):
    permission_classes = [RequirePerm('room.token')]

    def get(self, request, lesson_id):
        path = services.pdf_file(user=request.user, lesson_id=lesson_id)
        resp = FileResponse(open(path, 'rb'), content_type='application/pdf')
        resp['Content-Disposition'] = 'inline; filename="doska.pdf"'
        resp['Cache-Control'] = 'no-store'
        resp['X-Content-Type-Options'] = 'nosniff'
        return resp
