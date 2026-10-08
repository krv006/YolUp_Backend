"""Yuklangan fayldan (material yoki imtihon qoidalari hujjati) oddiy matn olish.

Qo'llab-quvvatlanadi: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx/.xlsm), CSV, TXT, MD.
Skanerlangan (rasmli) PDF'da matn bo'lmaydi — buni aniq xabar bilan rad etamiz.
"""
import csv
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .tc_client import TestCreatorError

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.txt', '.md', '.csv', '.xlsx', '.xlsm'}
_MIN_TEXT_CHARS = 80  # undan kam bo'lsa — matn yo'q (skanerlangan fayl)


class MaterialError(TestCreatorError):
    """Fayldan matn olib bo'lmadi — qayta urinish foydasiz."""

    def __init__(self, message: str):
        super().__init__(message, permanent=True)


def _clean(text: str) -> str:
    text = text.replace('\x00', ' ').replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t\f\v]+', ' ', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def _pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return '\n\n'.join((page.extract_text() or '') for page in reader.pages)


def _docx(data: bytes) -> str:
    from docx import Document

    document = Document(io.BytesIO(data))
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(' | '.join(cell.text.strip() for cell in row.cells))
    return '\n'.join(parts)


def _pptx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        slides = sorted(
            (name for name in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', name)),
            key=lambda name: int(re.search(r'(\d+)', Path(name).stem).group(1)),
        )
        out = []
        for name in slides:
            root = ElementTree.fromstring(archive.read(name))
            out.append(' '.join(node.text for node in root.iter() if node.tag.endswith('}t') and node.text))
    return '\n\n'.join(out)


def _xlsx(data: bytes) -> str:
    from openpyxl import load_workbook

    workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    lines = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c not in (None, '')]
            if cells:
                lines.append(' | '.join(cells))
    return '\n'.join(lines)


def _csv(data: bytes) -> str:
    text = data.decode('utf-8-sig', errors='replace')
    return '\n'.join(' | '.join(cell.strip() for cell in row if cell.strip()) for row in csv.reader(io.StringIO(text)))


_PARSERS = {'.pdf': _pdf, '.docx': _docx, '.pptx': _pptx, '.xlsx': _xlsx, '.xlsm': _xlsx, '.csv': _csv}


def extract_text(data: bytes, filename: str, *, max_chars: int = 0) -> str:
    """`data` baytlaridan toza matn. `max_chars` > 0 bo'lsa shu uzunlikda kesiladi."""
    ext = Path(filename or '').suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise MaterialError(f"Fayl turi qo'llab-quvvatlanmaydi: {ext or filename}.")
    try:
        if ext in _PARSERS:
            raw = _PARSERS[ext](data)
        else:
            raw = data.decode('utf-8-sig', errors='replace')
    except MaterialError:
        raise
    except Exception as exc:  # noqa: BLE001 — buzuq/parolli fayl
        raise MaterialError(f"«{filename}» faylini o'qib bo'lmadi: {exc}") from exc
    text = _clean(raw)
    if len(text) < _MIN_TEXT_CHARS:
        raise MaterialError(
            f"«{filename}» faylida o'qiladigan matn deyarli yo'q (skanerlangan/rasmli fayl bo'lishi mumkin). "
            "Matnli PDF yoki Word fayl yuklang."
        )
    return text[:max_chars] if max_chars else text


def combine_texts(named_texts: list, limit: int) -> str:
    """[(nom, matn), ...] -> bitta matn. Sig'masa har faylga teng ulush beriladi (so'nggi fayl butunlay
    kesilib ketmasin). Bitta matn bo'lsa sarlavhasiz qaytariladi."""
    named_texts = [(name, text) for name, text in named_texts if text.strip()]
    if not named_texts:
        return ''
    if len(named_texts) == 1:
        return named_texts[0][1][:limit]
    share = limit // len(named_texts)
    return '\n\n'.join(f'=== {name} ===\n{text[:share]}' for name, text in named_texts)
