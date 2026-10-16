"""Uy vazifasi doskasi: o'quvchi vazifani fayl yuklamasdan, to'liq funksiyali doskada yechadi.

Oqim: `GET/PUT .../board/` (avtosaqlash) -> `POST .../board/submit/` — sahifalar rasmli PDF'ga aylanadi va oddiy
topshiriq (`services.submit`) sifatida ketadi, shuning uchun AI tekshiruv, o'qituvchi baholashi, bildirishnomalar va
soatlik chegaralar fayl yuklash bilan aynan bir xil ishlaydi. Chiziq shakllari/tekshiruvi dars doskasi bilan umumiy
(`apps.board.services._validate_stroke`)."""
import json
import re
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.board import render
from apps.board.models import SHEET_H, SHEET_W
from apps.board.services import _validate_stroke
from apps.lessons.models import Course

from . import services
from .models import HomeworkBoard

MAX_SHEETS = 20
MAX_STROKES_PER_SHEET = 3000
MAX_PAYLOAD_BYTES = 4 * 1024 * 1024
_ID = re.compile(r'^[0-9A-Za-z_-]{6,40}$')


def _assignment_for(student: User, assignment_id):
    assignment = services._get_assignment(assignment_id)
    if not services._is_enrolled(student, assignment.course):
        raise PermissionDenied(_("Bu kursga yozilmagansiz — doskada vazifa yecha olmaysiz."))
    return assignment


def _view(assignment, board) -> dict:
    sheets = (board.sheets if board else None) or [{'strokes': []}]
    subject = assignment.course.subject
    return {
        'sheets': [{'index': i, 'strokes': sheet.get('strokes', [])} for i, sheet in enumerate(sheets)],
        'size': [SHEET_W, SHEET_H],
        'math_enabled': subject == Course.Subject.MATH,
        'chemistry_enabled': subject == Course.Subject.CHEMISTRY,
        'updated_at': board.updated_at if board else None,
    }


def get_board(*, student: User, assignment_id) -> dict:
    assignment = _assignment_for(student, assignment_id)
    board = HomeworkBoard.objects.filter(assignment=assignment, student=student).first()
    return _view(assignment, board)


def _clean_sheets(raw) -> list:
    if not isinstance(raw, list) or not raw:
        raise ValidationError({'sheets': _("Kamida bitta sheet kerak.")})
    if len(raw) > MAX_SHEETS:
        raise ValidationError({'sheets': _("Eng ko'pi bilan %(n)s ta sheet.") % {'n': MAX_SHEETS}})
    sheets = []
    for sheet in raw:
        strokes = sheet.get('strokes') if isinstance(sheet, dict) else None
        if not isinstance(strokes, list):
            raise ValidationError({'sheets': _("Sheet shakli noto'g'ri.")})
        if len(strokes) > MAX_STROKES_PER_SHEET:
            raise ValidationError({'sheets': _("Sheet to'ldi — yangisini oching.")})
        clean = []
        for stroke in strokes:
            if not isinstance(stroke, dict):
                raise ValidationError({'sheets': _("Chiziq shakli noto'g'ri.")})
            item = _validate_stroke(stroke)
            given = str(stroke.get('id') or '')
            item['id'] = given if _ID.match(given) else uuid.uuid4().hex[:12]
            clean.append(item)
        sheets.append({'strokes': clean})
    return sheets


def save_board(*, student: User, assignment_id, sheets) -> dict:
    """Avtosaqlash: butun doska holatini almashtiradi (har chiziq serverda qayta tekshiriladi)."""
    assignment = _assignment_for(student, assignment_id)
    if len(json.dumps(sheets, default=str)) > MAX_PAYLOAD_BYTES:
        raise ValidationError({'sheets': _("Doska juda katta.")})
    board, _created = HomeworkBoard.objects.update_or_create(
        assignment=assignment, student=student, defaults={'sheets': _clean_sheets(sheets)})
    return _view(assignment, board)


def submit_board(*, student: User, assignment_id) -> dict:
    """Doskani rasmli PDF qilib oddiy topshiriq sifatida yuboradi (bo'sh doska qabul qilinmaydi)."""
    assignment = _assignment_for(student, assignment_id)
    board = HomeworkBoard.objects.filter(assignment=assignment, student=student).first()
    pdf = render.sheets_to_pdf([sheet.get('strokes', []) for sheet in (board.sheets if board else [])])
    if pdf is None:
        raise ValidationError({'sheets': _("Doska bo'sh — avval vazifani yeching.")})
    upload = SimpleUploadedFile('doska.pdf', pdf, content_type='application/pdf')
    return services.submit(student=student, assignment_id=assignment.id, upload=upload)


def solve_formula(*, student: User, assignment_id, expr: str) -> dict:
    """Photomath uslubidagi yechuvchi — dars doskasidagi kabi faqat matematika kurslarida."""
    assignment = _assignment_for(student, assignment_id)
    if assignment.course.subject != Course.Subject.MATH:
        raise ValidationError({'expr': _('Formula yechuvchi faqat matematika kurslarida ishlaydi.')})
    from apps.board.math_solver import MathError, solve_math

    try:
        return solve_math(expr)
    except MathError as exc:
        raise ValidationError({'expr': str(exc)})
