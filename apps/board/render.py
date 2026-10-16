"""Doska sahifalarini rasmga (PNG/JPEG) va PDF ga aylantirish — uy vazifasi doskasi uchun.

Nega rasm: uy vazifasini AI ko'rish imkoniyati (vision) bilan o'qiydi va o'qituvchi PDF'ni ochib ko'radi; qo'lda chizilgan
yechim va formulalar matn emas, shuning uchun har sahifa to'liq rasm sifatida PDF'ga joylanadi (`PdfView` dagi vektor
PDF dars doskasi uchun, u yerda rasm talab qilinmaydi). Chizish qoidalari frontend (`board-stroke.tsx`) bilan bir xil:
matn bazaviy chizig'i `y` da, qatorlar oralig'i 1.35 x o'lcham, to'rtburchak burchagi 6 px.
"""
import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import SHEET_H, SHEET_W

INK = (28, 30, 58)
_FONT_CACHE: dict = {}


def _color(value, default=INK):
    text = str(value or '').strip().lstrip('#')
    try:
        if len(text) in (3, 4):
            text = ''.join(ch * 2 for ch in text)
        if len(text) >= 6:
            return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        pass
    return default


def _font(size: float):
    size = max(8, int(round(size)))
    if size not in _FONT_CACHE:
        try:
            import matplotlib

            path = Path(matplotlib.get_data_path()) / 'fonts' / 'ttf' / 'DejaVuSans-Bold.ttf'
            _FONT_CACHE[size] = ImageFont.truetype(str(path), size)
        except Exception:  # noqa: BLE001 - shrift topilmasa ham chizamiz (standart shrift)
            _FONT_CACHE[size] = ImageFont.load_default()
    return _FONT_CACHE[size]


def _math_image(latex: str, color: tuple, size: float):
    """LaTeX -> shaffof PNG (matplotlib mathtext). Chiqmasa None.

    Formula qora rangda, oq fonda chiziladi; kulrang qiymatdan shaffoflik niqobi yasab kerakli rangga bo'yaymiz
    (matplotlib versiyasiga qarab fon shaffof bo'lmasligi mumkin)."""
    try:
        from matplotlib import mathtext
        from PIL import ImageOps

        buffer = io.BytesIO()
        mathtext.math_to_image(f'${latex}$', buffer, dpi=200, format='png', color='black')
        buffer.seek(0)
        gray = Image.open(buffer).convert('L')
        scale = max(0.1, size / 27.8)  # 10pt @ 200dpi ~ 27.8 px/em -> kerakli o'lcham (px)
        gray = gray.resize((max(1, int(gray.width * scale)), max(1, int(gray.height * scale))), Image.LANCZOS)
        image = Image.new('RGBA', gray.size, (*color, 0))
        image.putalpha(ImageOps.invert(gray))
        return image
    except Exception:  # noqa: BLE001 - murakkab LaTeX: formulani matn sifatida chizamiz
        return None


def _arrow_head(draw, x1, y1, x2, y2, width, color):
    angle = math.atan2(y2 - y1, x2 - x1)
    length = max(10, width * 3.5)
    for delta in (2.6, -2.6):
        draw.line([(x2, y2), (x2 + length * math.cos(angle + delta), y2 + length * math.sin(angle + delta))],
                  fill=color, width=max(1, int(width)))


def render_sheet(strokes: list) -> Image.Image:
    """Bitta sheet (1600 x 900) -> RGB rasm."""
    page = Image.new('RGBA', (SHEET_W, SHEET_H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(page)
    for stroke in strokes or []:
        kind = stroke.get('type')
        color = _color(stroke.get('color'))
        width = max(1, int(stroke.get('width') or 4))
        if kind == 'text':
            size = int(stroke.get('size') or 22)
            font = _font(size)
            y = float(stroke.get('y', 60))
            for line in str(stroke.get('text', '')).split('\n'):
                draw.text((float(stroke.get('x', 60)), y), line, font=font, fill=color, anchor='ls')
                y += size * 1.35
        elif kind == 'math':
            size = int(stroke.get('size') or 24)
            image = _math_image(str(stroke.get('latex', '')), color, size)
            x, y = float(stroke.get('x', 60)), float(stroke.get('y', 60))
            if image is not None:
                page.alpha_composite(image, (int(max(0, x)), int(max(0, y - image.height * 0.75))))
            else:
                draw.text((x, y), str(stroke.get('latex', '')), font=_font(size), fill=color, anchor='ls')
        elif kind == 'line':
            x1, y1, x2, y2 = (float(stroke.get(k, 0)) for k in ('x1', 'y1', 'x2', 'y2'))
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
            if stroke.get('arrow'):
                _arrow_head(draw, x1, y1, x2, y2, width, color)
        elif kind == 'rect':
            x, y, w, h = (float(stroke.get(k, 0)) for k in ('x', 'y', 'w', 'h'))
            draw.rounded_rectangle([x, y, x + w, y + h], radius=6, outline=color, width=width)
        elif kind == 'ellipse':
            x, y, w, h = (float(stroke.get(k, 0)) for k in ('x', 'y', 'w', 'h'))
            draw.ellipse([x, y, x + w, y + h], outline=color, width=width)
        else:
            points = [(float(p[0]), float(p[1])) for p in (stroke.get('points') or []) if len(p) >= 2]
            if len(points) < 2:
                continue
            opacity = stroke.get('opacity')
            if opacity and float(opacity) < 1:  # marker: shaffof qatlam
                layer = Image.new('RGBA', page.size, (0, 0, 0, 0))
                ImageDraw.Draw(layer).line(points, fill=(*color, int(255 * float(opacity))), width=width, joint='curve')
                page.alpha_composite(layer)
                draw = ImageDraw.Draw(page)
            else:
                draw.line(points, fill=color, width=width, joint='curve')
                r = width / 2  # yumaloq uchlar
                for cx, cy in (points[0], points[-1]):
                    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    return page.convert('RGB')


def sheets_to_pdf(sheets: list):
    """[[stroke, ...], ...] -> PDF baytlari (har bo'sh bo'lmagan sheet — bitta rasm sahifa). Hammasi bo'sh -> None."""
    pages = [render_sheet(strokes) for strokes in sheets if strokes]
    if not pages:
        return None
    buffer = io.BytesIO()
    pages[0].save(buffer, format='PDF', save_all=True, append_images=pages[1:], resolution=110.0, quality=88)
    return buffer.getvalue()
