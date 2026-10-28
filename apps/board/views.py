"""Board views — yupqa qatlam."""
from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RequirePerm

from . import services
from .periodic_table_data import LATIN_NAMES, PERIODIC_TABLE


class PeriodicTableView(APIView):
    """Davriy jadval — darsga/xonaga bog'liq emas, shuning uchun `lesson_id`
    talab qilmaydi (`room.token` o'rniga oddiy autentifikatsiya yetarli)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([{**element, 'latin_name': LATIN_NAMES.get(element['symbol'], element['name'])} for element in PERIODIC_TABLE])


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


class CurrentSheetView(APIView):
    """O'qituvchi: `POST {sheet}` — hozir shu sahifada turibman (o'quvchilarga socket `current_sheet` hodisasi boradi)."""

    permission_classes = [RequirePerm('room.token')]

    def post(self, request, lesson_id):
        return Response({'current_sheet': services.set_current_sheet(
            user=request.user, lesson_id=lesson_id, index=request.data.get('sheet'),
        )})


class SheetView(APIView):
    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request, lesson_id):
        title = request.data.get('title') or ''
        index = services.add_sheet(user=request.user, lesson_id=lesson_id, title=title)
        return Response({'index': index, 'title': services._clean_title(title)}, status=201)


class SheetDetailView(APIView):
    """`PATCH {title}` — sahifa nomini o'zgartirish (faqat o'qituvchi)."""

    permission_classes = [RequirePerm('room.moderate')]

    def patch(self, request, lesson_id, index):
        return Response(services.rename_sheet(
            user=request.user, lesson_id=lesson_id, index=index, title=request.data.get('title'),
        ))


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
        student_ids, mode = request.data.get('student_ids'), request.data.get('mode') or ''
        if student_ids is not None or mode:
            # ommaviy: `student_ids` ro'yxati yoki `mode: all | none`
            return Response({'ok': True, **services.grant_many(
                teacher=request.user, lesson_id=lesson_id,
                student_ids=student_ids if isinstance(student_ids, list) else None, mode=mode,
            )})
        services.grant_draw(
            teacher=request.user, lesson_id=lesson_id,
            student_id=request.data.get('student_id'),
        )
        return Response({'ok': True})


class RevokeView(APIView):
    """O'qituvchi: bitta o'quvchidan doskaga chizish ruxsatini qaytarib oladi — `{student_id}`."""

    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request, lesson_id):
        revoked = services.revoke_draw(
            teacher=request.user, lesson_id=lesson_id, student_id=request.data.get('student_id'),
        )
        return Response({'ok': True, 'revoked': revoked})


class SendToChatView(APIView):
    """O'qituvchi: doskani guruh chatiga PDF sifatida yuboradi -> `{message_id}`."""

    permission_classes = [RequirePerm('room.moderate')]

    def post(self, request, lesson_id):
        message = services.send_to_chat(teacher=request.user, lesson_id=lesson_id)
        return Response({'message_id': str(message.id)}, status=201)


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
