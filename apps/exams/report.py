"""Imtihon natijasi PDF (reportlab): sarlavha, o'quvchi, jami ball va bo'limlar."""
import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _flat(value, prefix=''):
    """Natija lug'atini (bo'limlar ichma-ich) `(nom, qiymat)` qatorlariga yoyadi; faqat oddiy qiymatlar."""
    rows = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ('student', 'integrity', 'manual_answers', 'progress'):
                continue
            rows.extend(_flat(item, f'{prefix}{key}.'))
    elif isinstance(value, list):
        for index, item in enumerate(value, 1):
            rows.extend(_flat(item, f'{prefix}{index}.'))
    elif value is not None:
        rows.append((prefix.rstrip('.'), value))
    return rows


def build_pdf(exam, item) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 60
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(50, y, str(exam.title)[:70])
    y -= 24
    pdf.setFont('Helvetica', 11)
    student = item.get('student') or {}
    pdf.drawString(50, y, f"O'quvchi: {student.get('name', '')}")
    y -= 16
    pdf.drawString(50, y, f"Guruh: {exam.course.title}   Sana: {exam.starts_at:%Y-%m-%d %H:%M}")
    y -= 28
    total = item.get('total') or {}
    if total:
        pdf.setFont('Helvetica-Bold', 13)
        label = f" ({total['label']})" if total.get('label') else ''
        pdf.drawString(50, y, f"Jami: {total.get('score')}/{total.get('max')}{label}")
        y -= 24
    pdf.setFont('Helvetica', 10)
    for name, value in _flat({key: val for key, val in item.items() if key != 'total'}):
        if y < 60:
            pdf.showPage()
            pdf.setFont('Helvetica', 10)
            y = height - 60
        pdf.drawString(50, y, f"{name[:48]}: {str(value)[:70]}")
        y -= 14
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
