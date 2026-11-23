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


def extract_text(data: bytes, filename: str, *, max_chars: int = 0, min_chars: int = _MIN_TEXT_CHARS) -> str:
    """`data` baytlaridan toza matn. `max_chars` > 0 bo'lsa shu uzunlikda kesiladi. `min_chars` dan qisqa matn "matn yo'q"
    hisoblanadi (material uchun 80: skanerlangan fayl; o'quvchi ishida 1: qisqa javob ham javob)."""
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
    if len(text) < max(1, min_chars):
        raise MaterialError(
            f"«{filename}» faylida o'qiladigan matn deyarli yo'q (skanerlangan/rasmli fayl bo'lishi mumkin). "
            "Matnli PDF yoki Word fayl yuklang."
        )
    return text[:max_chars] if max_chars else text


_WORD = re.compile(r"[\w']+", re.UNICODE)
_CHUNK_CHARS = 1500


def _topic_matchers(topic: str):
    """Mavzudan: (butun ibora, so'z o'zaklari). Qisqa/xizmat so'zlari (<3 harf) o'zak bo'lmaydi, lekin ibora sifatida
    ("to be") qidiriladi. O'zbekcha qo'shimchalar uchun uzun so'zning boshi olinadi (tenglamalar -> tenglam)."""
    words = [w.lower() for w in _WORD.findall(topic or '')]
    if not words:
        return None, []
    phrase = re.compile(r'\b' + r'\s+'.join(re.escape(w) for w in words) + r'\b', re.IGNORECASE)
    stems = []
    for word in words:
        if len(word) < 3:
            continue
        stem = word if len(word) <= 5 else word[:max(4, int(len(word) * 0.7))]
        stems.append(re.compile(r'\b' + re.escape(stem) + r'\w*', re.IGNORECASE))
    return phrase, stems


def _chunks(text: str) -> list:
    out, start = [], 0
    while start < len(text):
        end = min(len(text), start + _CHUNK_CHARS)
        if end < len(text):
            space = text.find(' ', end, end + 120)
            end = space if space != -1 else end
        out.append(text[start:end])
        start = end
    return out


def select_relevant(text: str, topic: str, limit: int) -> str:
    """Katta material (kitob) sig'masa — boshidan emas, MAVZUGA oid qismlardan `limit` belgi tanlanadi (asl tartibda).
    Mavzu bo'sh yoki materialda umuman topilmasa — avvalgidek boshidan."""
    if len(text) <= limit:
        return text
    phrase, stems = _topic_matchers(topic)
    if phrase is None:
        return text[:limit]
    chunks = _chunks(text)
    scores = [len(phrase.findall(chunk)) * 3 + sum(len(rx.findall(chunk)) for rx in stems) for chunk in chunks]
    if not any(scores):
        return text[:limit]
    ranked = sorted((i for i, score in enumerate(scores) if score), key=lambda i: (-scores[i], i))
    chosen, used = set(), 0
    for index in ranked:
        if used + len(chunks[index]) > limit and chosen:
            break
        chosen.add(index)
        used += len(chunks[index]) + 5
    for index in ranked:  # qolgan joyga eng yaxshi bo'laklarning davomi (tushuntirish ko'pincha keyingi bo'lakda)
        nxt = index + 1
        if used >= limit:
            break
        if nxt < len(chunks) and nxt not in chosen and used + len(chunks[nxt]) <= limit:
            chosen.add(nxt)
            used += len(chunks[nxt]) + 5
    return '\n...\n'.join(chunks[i] for i in sorted(chosen))[:limit]


def combine_texts(named_texts: list, limit: int, topic: str = '') -> str:
    """[(nom, matn), ...] -> bitta matn. Sig'masa har faylga teng ulush beriladi (so'nggi fayl butunlay
    kesilib ketmasin); `topic` berilsa har fayldan mavzuga oid qismlar olinadi (boshidan emas).
    Bitta matn bo'lsa sarlavhasiz qaytariladi."""
    named_texts = [(name, text) for name, text in named_texts if text.strip()]
    if not named_texts:
        return ''
    if len(named_texts) == 1:
        return select_relevant(named_texts[0][1], topic, limit)
    share = limit // len(named_texts)
    return '\n\n'.join(f'=== {name} ===\n{select_relevant(text, topic, share)}' for name, text in named_texts)
