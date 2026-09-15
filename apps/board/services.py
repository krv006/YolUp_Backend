"""Doska service layer — chizish, o'chirish (sabab bilan), ruxsat, PDF -> chat."""
import uuid

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core import audit
from apps.lessons.models import Course, Enrollment, Lesson

from . import realtime
from .models import SHEET_H, SHEET_W, BoardErase, BoardGrant, BoardSheet

MAX_STROKE_POINTS = 2000
MAX_STROKES_PER_SHEET = 3000


def _get_lesson(lesson_id) -> Lesson:
    try:
        return Lesson.objects.select_related('course').get(pk=lesson_id)
    except (Lesson.DoesNotExist, ValueError, TypeError):
        raise NotFound(_('Dars topilmadi.'))


def _is_teacher(user: User, lesson: Lesson) -> bool:
    return lesson.course.teacher_id == user.id


def can_view(user: User, lesson: Lesson) -> bool:
    if _is_teacher(user, lesson):
        return True
    return Enrollment.objects.filter(
        course=lesson.course, student=user, status=Enrollment.Status.APPROVED,
    ).exists()


def can_draw(user: User, lesson: Lesson) -> bool:
    if _is_teacher(user, lesson):
        return True
    return BoardGrant.objects.filter(lesson=lesson, student=user).exists()


# Matematik vosita (MathLive formulalar, SymPy yechuvchi) FAQAT matematika
# kurslarida, davriy jadval FAQAT kimyo kurslarida — `Course.subject` endi
# erkin matn emas, tayin ro'yxatdan tanlanadi, shuning uchun oddiy tenglik
# yetarli (regex/imlo xatosi xavfi yo'q).
def is_math_lesson(lesson: Lesson) -> bool:
    return lesson.course.subject == Course.Subject.MATH


def is_chemistry_lesson(lesson: Lesson) -> bool:
    return lesson.course.subject == Course.Subject.CHEMISTRY


def get_board(*, user: User, lesson_id) -> dict:
    lesson = _get_lesson(lesson_id)
    if not can_view(user, lesson):
        raise PermissionDenied(_("Doskani ko'rish huquqingiz yo'q."))
    sheets = list(lesson.board_sheets.all())
    if not sheets:
        sheets = [BoardSheet.objects.create(lesson=lesson, index=0)]
    is_teacher = _is_teacher(user, lesson)
    result = {
        'sheets': [{'index': s.index, 'strokes': s.strokes} for s in sheets],
        'can_draw': can_draw(user, lesson),
        'is_teacher': is_teacher,
        'size': [SHEET_W, SHEET_H],
        'subject': lesson.course.subject,
        # Frontend uchun YAGONA manba: matematik vosita (MathLive math-field,
        # formula bloklari) faqat shu true bo'lganda ko'rsatiladi — fan
        # regex'ini frontendda takrorlash SHART EMAS
        'math_enabled': is_math_lesson(lesson),
        # Xuddi shunday: davriy jadval tugmasi faqat shu true bo'lganda
        # ko'rsatiladi (`GET /board/periodic-table/`ning o'zi fan bo'yicha
        # cheklanmagan — chunki ma'lumot umumiy va zararsiz, lekin UI shu
        # flag orqali faqat kimyo darslarida chiqishi kerak)
        'chemistry_enabled': is_chemistry_lesson(lesson),
    }
    if is_teacher:
        # Diqqatsiz o'quvchilar (oynadan chiqib, hali qaytmagan) — faqat
        # o'qituvchiga, WebSocket ulanishidan oldingi holatni ham qamrab oladi
        from apps.live.services import away_students, pending_camera_requests, pending_mic_requests
        result['away_students'] = away_students(lesson)
        # Javobsiz mikrofon/kamera so'rovlari — WebSocket'dan oldin/keyin kirsa
        # ham (sahifa yangilansa ham) yo'qolib qolmasligi uchun
        result['pending_mic_requests'] = pending_mic_requests(lesson)
        result['pending_camera_requests'] = pending_camera_requests(lesson)
    return result


def _validate_stroke(stroke: dict, *, allow_math: bool = False) -> dict:
    # MathLive formula bloki (LaTeX) — FAQAT matematika kurslarida
    if stroke.get('type') == 'math':
        if not allow_math:
            raise ValidationError({'stroke': (
                _('Matematik formula bloki faqat matematika kurslari doskasida ishlaydi.')
            )})
        latex = str(stroke.get('latex') or '').strip()
        if not latex:
            raise ValidationError({'stroke': _("Formula bo'sh.")})
        try:
            x = float(stroke.get('x', 60))
            y = float(stroke.get('y', 60))
        except (TypeError, ValueError):
            raise ValidationError({'stroke': _("Koordinata noto'g'ri.")})
        return {
            'type': 'math',
            'latex': latex[:2000],
            'x': round(max(0, min(SHEET_W - 40, x)), 1),
            'y': round(max(0, min(SHEET_H - 20, y)), 1),
            'size': max(12, min(48, int(stroke.get('size', 24)))),
            'color': str(stroke.get('color', '#1c1e3a'))[:9],
        }
    # Matn elementi (formula bloklari) — chiziq emas
    if stroke.get('type') == 'text':
        text = str(stroke.get('text') or '').strip()
        if not text:
            raise ValidationError({'stroke': _("Matn bo'sh.")})
        try:
            x = float(stroke.get('x', 60))
            y = float(stroke.get('y', 60))
        except (TypeError, ValueError):
            raise ValidationError({'stroke': _("Koordinata noto'g'ri.")})
        return {
            'type': 'text',
            'text': text[:2000],
            'x': round(max(0, min(SHEET_W - 40, x)), 1),
            'y': round(max(0, min(SHEET_H - 20, y)), 1),
            'size': max(12, min(48, int(stroke.get('size', 24)))),
            'color': str(stroke.get('color', '#1c1e3a'))[:9],
        }
    # Shakllar: to'g'ri chiziq/strelka, to'rtburchak, ellips — front doskasining
    # to'liq asboblar paneli uchun (hammasi saqlanadi va PDF'ga tushadi)
    if stroke.get('type') in ('line', 'rect', 'ellipse'):
        kind = stroke['type']

        def _coord(name, limit):
            try:
                return round(max(0, min(limit, float(stroke.get(name, 0)))), 1)
            except (TypeError, ValueError):
                raise ValidationError({
                    'stroke': _("'%(name)s' koordinatasi noto'g'ri.") % {'name': name},
                })

        clean = {
            'type': kind,
            'color': str(stroke.get('color', '#1c1e3a'))[:9],
            'width': max(1, min(24, int(stroke.get('width', 3)))),
        }
        if kind == 'line':
            clean.update(
                x1=_coord('x1', SHEET_W), y1=_coord('y1', SHEET_H),
                x2=_coord('x2', SHEET_W), y2=_coord('y2', SHEET_H),
                arrow=bool(stroke.get('arrow', False)),
            )
        else:
            clean.update(
                x=_coord('x', SHEET_W), y=_coord('y', SHEET_H),
                w=max(2, _coord('w', SHEET_W)), h=max(2, _coord('h', SHEET_H)),
            )
        return clean

    points = stroke.get('points') or []
    if not isinstance(points, list) or len(points) < 2:
        raise ValidationError({'stroke': _('Kamida 2 nuqta kerak.')})
    if len(points) > MAX_STROKE_POINTS:
        points = points[::2][:MAX_STROKE_POINTS]  # siyraklashtirish
    clean = []
    for p in points:
        try:
            x, y = float(p[0]), float(p[1])
        except (TypeError, ValueError, IndexError):
            raise ValidationError({'stroke': _("Nuqta formati noto'g'ri.")})
        clean.append([round(max(0, min(SHEET_W, x)), 1), round(max(0, min(SHEET_H, y)), 1)])
    color = str(stroke.get('color', '#1c1e3a'))[:9]
    width = max(1, min(24, int(stroke.get('width', 3))))
    result = {'points': clean, 'color': color, 'width': width}
    # Marker (highlighter) — shaffof qalam: front globalAlpha bilan chizadi,
    # PDF'da ham xuddi shu shaffoflik qo'llanadi
    try:
        opacity = float(stroke.get('opacity', 1))
    except (TypeError, ValueError):
        opacity = 1
    if opacity < 1:
        result['opacity'] = round(max(0.15, min(1, opacity)), 2)
    return result


@transaction.atomic
def add_stroke(*, user: User, lesson_id, sheet_index: int, stroke: dict) -> dict:
    lesson = _get_lesson(lesson_id)
    if not can_draw(user, lesson):
        raise PermissionDenied(_("Chizish uchun o'qituvchidan ruxsat oling."))
    sheet, _created = BoardSheet.objects.select_for_update().get_or_create(
        lesson=lesson, index=int(sheet_index or 0),
    )
    if len(sheet.strokes) >= MAX_STROKES_PER_SHEET:
        raise ValidationError(_("Bu sheet to'ldi — yangisini oching."))
    clean = _validate_stroke(stroke, allow_math=is_math_lesson(lesson))
    clean['id'] = uuid.uuid4().hex[:12]
    clean['by'] = user.first_name or user.username
    sheet.strokes = [*sheet.strokes, clean]
    sheet.save(update_fields=['strokes', 'updated_at'])
    # Real-time: barcha ulangan ishtirokchilarga bir zumda (WS, polling emas)
    transaction.on_commit(
        lambda: realtime.broadcast_stroke(lesson.id, sheet.index, clean)
    )
    return clean


@transaction.atomic
def add_sheet(*, user: User, lesson_id) -> int:
    lesson = _get_lesson(lesson_id)
    if not _is_teacher(user, lesson):
        raise PermissionDenied(_("Yangi sheet'ni faqat o'qituvchi ochadi."))
    last = lesson.board_sheets.order_by('-index').first()
    index = (last.index + 1) if last else 0
    BoardSheet.objects.create(lesson=lesson, index=index)
    transaction.on_commit(lambda: realtime.broadcast_sheet(lesson.id, index))
    return index


@transaction.atomic
def erase_strokes(*, user: User, lesson_id, sheet_index: int, stroke_ids: list, reason: str) -> int:
    """O'chirish — sabab MAJBURIY (EduTech.docx: "ochirish sababi bosh bolishi kere emas")."""
    reason = (reason or '').strip()
    if not reason:
        raise ValidationError({'reason': _("O'chirish sababi bo'sh bo'lishi mumkin emas.")})
    if not stroke_ids:
        raise ValidationError({'stroke_ids': _("Nimani o'chirish ko'rsatilmadi.")})
    lesson = _get_lesson(lesson_id)
    if not can_draw(user, lesson):
        raise PermissionDenied(_("O'chirish uchun ruxsat yo'q."))
    try:
        sheet = BoardSheet.objects.select_for_update().get(lesson=lesson, index=int(sheet_index or 0))
    except BoardSheet.DoesNotExist:
        raise NotFound(_('Sheet topilmadi.'))
    ids = set(stroke_ids)
    before = len(sheet.strokes)
    sheet.strokes = [s for s in sheet.strokes if s.get('id') not in ids]
    removed = before - len(sheet.strokes)
    if removed:
        sheet.save(update_fields=['strokes', 'updated_at'])
        BoardErase.objects.create(
            lesson=lesson, user=user, sheet_index=sheet.index,
            reason=reason, stroke_ids=list(ids),
        )
        audit.record(action='board.erase', actor=user, target=lesson, meta={'reason': reason, 'count': removed})
        transaction.on_commit(lambda: realtime.broadcast_erase(
            lesson.id, sheet.index, list(ids),
            user.first_name or user.username, reason,
        ))
    return removed


@transaction.atomic
def grant_draw(*, teacher: User, lesson_id, student_id) -> bool:
    lesson = _get_lesson(lesson_id)
    if not _is_teacher(teacher, lesson):
        raise PermissionDenied(_("Ruxsatni faqat kurs o'qituvchisi beradi."))
    try:
        student = User.objects.get(pk=student_id, role=User.Role.STUDENT)
    except (User.DoesNotExist, ValueError, TypeError):
        raise NotFound(_("O'quvchi topilmadi."))
    BoardGrant.objects.get_or_create(lesson=lesson, student=student)
    audit.record(action='board.grant', actor=teacher, target=lesson, meta={'student_id': str(student_id)})
    # WebSocket'ga darhol xabar — aks holda o'quvchi sahifani yangilamaguncha
    # ruxsat berilganini bilmay, chiza olmay turaverardi (2026-09-04 tuzatildi).
    transaction.on_commit(lambda: realtime.broadcast_board_granted(lesson.id, str(student_id)))
    return True


# ── PDF: dars tugagach doska lentasi PDF bo'lib guruh chatga tushadi ──────

def _pdf_path(lesson: Lesson):
    from pathlib import Path
    base = Path(settings.BASE_DIR) / 'private' / 'boards'
    base.mkdir(parents=True, exist_ok=True)
    return base / f'{lesson.id}.pdf'


def _math_png(latex: str, color: str):
    """LaTeX -> PNG (matplotlib mathtext — TeX o'rnatilishi shart emas).
    MathLive'dan kelgan formulalarning mutlaq ko'pchiligini qamraydi."""
    import io

    from matplotlib import mathtext

    buf = io.BytesIO()
    mathtext.math_to_image(f'${latex}$', buf, dpi=200, format='png', color=color)
    buf.seek(0)
    return buf


def generate_pdf(lesson: Lesson):
    """Sheet'larni PDF sahifalarga chizadi (reportlab). Bo'sh doska -> None."""
    sheets = [s for s in lesson.board_sheets.all() if s.strokes]
    if not sheets:
        return None
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas as pdf_canvas

    path = _pdf_path(lesson)
    page_w, page_h = 842, 595  # A4 landshaft (pt)
    scale = min(page_w / SHEET_W, page_h / SHEET_H)
    c = pdf_canvas.Canvas(str(path), pagesize=(page_w, page_h))
    for sheet in sheets:
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
        for s in sheet.strokes:
            if s.get('type') == 'math':
                # MathLive LaTeX bloki — rasmga aylantirib joylaymiz;
                # render bo'lmasa (murakkab LaTeX) — matn fallback
                size = max(6, s.get('size', 24) * scale)
                x_pt = s.get('x', 60) * scale
                y_pt = page_h - s.get('y', 60) * scale
                try:
                    from reportlab.lib.utils import ImageReader

                    img = ImageReader(_math_png(
                        s.get('latex', ''), s.get('color', '#1c1e3a'),
                    ))
                    iw, ih = img.getSize()
                    target_h = size * 1.6
                    target_w = iw * (target_h / ih)
                    c.drawImage(
                        img, x_pt, y_pt - target_h,
                        width=target_w, height=target_h, mask='auto',
                    )
                except Exception:  # noqa: BLE001 — PDF hech qachon yiqilmasin
                    c.setFont('Courier', size)
                    safe = str(s.get('latex', '')).encode('latin-1', 'replace').decode('latin-1')
                    c.drawString(x_pt, y_pt - size, safe)
                continue
            if s.get('type') == 'text':
                try:
                    c.setFillColor(HexColor(s.get('color', '#1c1e3a')))
                except ValueError:
                    c.setFillColor(HexColor('#1c1e3a'))
                size = max(6, s.get('size', 24) * scale)
                c.setFont('Courier', size)
                y = page_h - s.get('y', 60) * scale
                for line in str(s.get('text', '')).splitlines():
                    # Courier faqat latin-1 — unicode ramkalarni yaqin belgilarga almashtiramiz
                    safe = line.encode('latin-1', 'replace').decode('latin-1')
                    c.drawString(s.get('x', 60) * scale, y, safe)
                    y -= size * 1.3
                continue
            try:
                c.setStrokeColor(HexColor(s.get('color', '#1c1e3a')))
            except ValueError:
                c.setStrokeColor(HexColor('#1c1e3a'))
            c.setLineWidth(max(1, s.get('width', 3) * scale))
            c.setLineCap(1)
            c.setLineJoin(1)

            kind = s.get('type')
            if kind == 'line':
                x1, y1 = s.get('x1', 0) * scale, page_h - s.get('y1', 0) * scale
                x2, y2 = s.get('x2', 0) * scale, page_h - s.get('y2', 0) * scale
                c.line(x1, y1, x2, y2)
                if s.get('arrow'):
                    # strelka uchi — yo'nalish bo'ylab ikki qanot
                    import math as _math
                    ang = _math.atan2(y2 - y1, x2 - x1)
                    size = max(6, s.get('width', 3) * scale * 3)
                    for da in (2.6, -2.6):
                        c.line(
                            x2, y2,
                            x2 + size * _math.cos(ang + da),
                            y2 + size * _math.sin(ang + da),
                        )
                continue
            if kind == 'rect':
                c.rect(
                    s.get('x', 0) * scale,
                    page_h - (s.get('y', 0) + s.get('h', 0)) * scale,
                    s.get('w', 0) * scale, s.get('h', 0) * scale,
                    stroke=1, fill=0,
                )
                continue
            if kind == 'ellipse':
                x0 = s.get('x', 0) * scale
                y0 = page_h - (s.get('y', 0) + s.get('h', 0)) * scale
                c.ellipse(x0, y0, x0 + s.get('w', 0) * scale, y0 + s.get('h', 0) * scale)
                continue

            p = c.beginPath()
            pts = s.get('points') or []
            if len(pts) < 2:
                continue
            # Marker shaffofligi (highlighter)
            opacity = s.get('opacity')
            if opacity:
                c.setStrokeAlpha(float(opacity))
            # PDF koordinatalari pastdan yuqoriga — y ni ag'daramiz
            p.moveTo(pts[0][0] * scale, page_h - pts[0][1] * scale)
            for x, y in pts[1:]:
                p.lineTo(x * scale, page_h - y * scale)
            c.drawPath(p, stroke=1, fill=0)
            if opacity:
                c.setStrokeAlpha(1)
        c.showPage()
    c.save()
    return path


def publish_board_pdf(lesson: Lesson):
    """finish_lesson'dan chaqiriladi: PDF yaratib, guruh chatga FAYL sifatida tashlaydi
    (nusxa ko'chirish/yuklab olishdan himoyalangan — faqat platforma ichida ochiladi).

    Doska bo'sh bo'lsa jim o'tadi; xato dars yakunlashni to'xtatmasligi kerak.
    """
    path = generate_pdf(lesson)
    if path is None:
        return
    from django.core.files import File
    from django.db import transaction

    from apps.chat import realtime
    from apps.chat import services as chat_services
    from apps.chat.models import Message

    room = chat_services.ensure_course_room(lesson.course)
    msg = Message(
        room=room,
        sender=lesson.course.teacher,
        text=f'📋 "{lesson.course.title}" doskasi',
        kind=Message.Kind.SYSTEM,
        system_key='board_ready',
        system_params={'lesson_title': lesson.course.title},
    )
    with open(path, 'rb') as f:
        msg.file.save(f'doska_{lesson.id}.pdf', File(f), save=False)
    msg.save()
    room.save(update_fields=['updated_at'])
    # send_message bilan bir xil: WebSocket'ga darhol tarqatamiz.
    transaction.on_commit(lambda: realtime.broadcast_message(msg))


def solve_formula(*, user: User, lesson_id, expr: str) -> dict:
    """Photomath uslubi: formulani avtomatik yechish/soddalashtirish (SymPy).

    FAQAT matematika kurslarida — boshqa fanlarda bu vosita mavjud emas.
    """
    lesson = _get_lesson(lesson_id)
    if not can_view(user, lesson):
        raise PermissionDenied(_("Ruxsat yo'q."))
    if not is_math_lesson(lesson):
        raise ValidationError({'expr': (
            _('Formula yechuvchi faqat matematika kurslarida ishlaydi.')
        )})
    from .math_solver import MathError, solve_math
    try:
        return solve_math(expr)
    except MathError as exc:
        raise ValidationError({'expr': str(exc)})


def pdf_file(*, user: User, lesson_id):
    lesson = _get_lesson(lesson_id)
    if not can_view(user, lesson):
        raise PermissionDenied(_("Ruxsat yo'q."))
    path = _pdf_path(lesson)
    if not path.exists():
        path = generate_pdf(lesson)
        if path is None:
            raise NotFound(_("Doska bo'sh — PDF yo'q."))
    return path
