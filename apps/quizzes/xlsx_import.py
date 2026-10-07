"""O'qituvchi yuklagan .xlsx fayldan test savollarini ajratib olish (import).

Kutilgan jadval (1-qator — sarlavha, o'tkazib yuboriladi):

    | Savol       | A        | B        | C        | D        | E        | To'g'ri javob |
    |-------------|----------|----------|----------|----------|----------|---------------|
    | Savol matni | Variant1 | Variant2 | Variant3 | Variant4 | Variant5 | B             |

Har bir ustun harfi (A-E) doim bir xil pozitsiyaga bog'langan (B ustuni =
A varianti, C ustuni = B varianti, ...) — "To'g'ri javob" ustunidagi harf
shu pozitsiyalardan biriga ishora qiladi. Variant ustunlaridan ba'zilari
bo'sh bo'lishi mumkin (masalan faqat 4 ta variant bo'lsa, E ustuni bo'sh
qoladi) — bu xato emas, shunchaki o'sha variant qatorga qo'shilmaydi.

`docx_import.py` bilan bir xil preview strukturasini qaytaradi, shuning
uchun `QuizImportView` ikkalasini ham bab-baravar ishlatadi.
"""
import re
from pathlib import Path

MAX_IMPORT_FILE_SIZE_MB = 10
# Pozitsiyaga bog'liq ustunlar (0-indeksli): 0=Savol, 1-5=A..E variant, 6=javob.
_OPTION_COLUMN_INDEXES = [1, 2, 3, 4, 5]
_ANSWER_COLUMN_INDEX = 6


def _cell_text(value) -> str:
    return str(value).strip() if value is not None else ''


def _row_value(row, index):
    """`row` — cell obyektlar tuple'i (oddiy rejim) yoki qiymatlar tuple'i
    (`values_only=True`). Ikkalasini ham qo'llab-quvvatlaydi, qatordan
    tashqariga chiqib ketsa (qisqaroq qator) `None` qaytaradi."""
    if index >= len(row):
        return None
    cell = row[index]
    return cell.value if hasattr(cell, 'value') else cell


def parse_xlsx_questions(file_obj) -> dict:
    """`.xlsx` fayl (fayl-obyekt yoki yo'l)ni preview strukturasiga aylantiradi.

    Qaytaradi: {'title': '', 'description': '',
                'questions': [{'text', 'order', 'options': [{'text','is_correct','order'}]}],
                'warnings': [{'question_number', 'reason'}]}

    Excel jadvalida erkin sarlavha/tavsif joyi yo'q (birinchi qator doim
    ustun nomlari), shuning uchun title/description hamisha bo'sh qaytadi —
    o'qituvchi buni allaqachon test yaratish oynasida kiritgan bo'ladi.

    `read_only` rejimi ATAYLAB ishlatilmaydi — bo'sh (yozilmagan) katakchalar
    o'sha rejimda `EmptyCell` sentinel sifatida qaytadi va oddiy `Cell`dan
    farqli xususiyatlarga ega, bu esa variant ustunlaridan biri bo'sh
    qoldirilganda (masalan faqat 4 ta variant) chalkashlikka olib keladi.
    """
    import openpyxl

    workbook = openpyxl.load_workbook(file_obj, data_only=True)
    sheet = workbook.active

    header = [_cell_text(cell.value).translate(_APOSTROPHES).lower() for cell in sheet[1]]
    if 'savol' in header and 'variantlar' in header:
        return _parse_test_creator_layout(sheet, header)

    questions = []
    warnings = []
    for row in sheet.iter_rows(min_row=2):
        question_text = _cell_text(_row_value(row, 0))
        if not question_text:
            continue  # bo'sh qator — o'tkazib yuboriladi

        options = []
        for index, col_index in enumerate(_OPTION_COLUMN_INDEXES):
            text = _cell_text(_row_value(row, col_index))
            if not text:
                continue
            options.append({'letter': chr(ord('A') + index), 'text': text})

        answer_letter = _cell_text(_row_value(row, _ANSWER_COLUMN_INDEX)).upper()[:1] or None
        order = len(questions)
        questions.append({
            'text': question_text,
            'order': order,
            'options': [{
                'text': opt['text'],
                'is_correct': bool(answer_letter) and opt['letter'] == answer_letter,
                'order': i,
            } for i, opt in enumerate(options)],
        })

        correct_count = sum(1 for o in questions[-1]['options'] if o['is_correct'])
        if len(options) < 2:
            warnings.append({'question_number': order + 1, 'reason': 'not_enough_options'})
        elif correct_count != 1:
            warnings.append({'question_number': order + 1, 'reason': 'answer_not_detected'})

    return {'title': '', 'description': '', 'questions': questions, 'warnings': warnings}


_APOSTROPHES = str.maketrans({'‘': "'", '’': "'", 'ʻ': "'", 'ʼ': "'", '`': "'"})
_OPTION_SPLIT_RE = re.compile(r';\s*(?=[A-Za-z][.\)])')
_OPTION_PART_RE = re.compile(r'^([A-Za-z])[.\)]\s*(.*)$', re.DOTALL)


def _parse_test_creator_layout(sheet, header: list) -> dict:
    """Test-creator eksporti: `# | Savol | Turi | Qiyinlik | Variantlar | Ball | To'g'ri javob | Izoh`.
    "Variantlar" bitta katakda: `A) matn; B) matn; ...`; "To'g'ri javob" — harf(lar): `B` yoki `A, C`.
    Ustunlar tartibiga emas, sarlavha nomiga qarab topiladi."""

    def column(*names):
        for index, title in enumerate(header):
            if any(title.startswith(name) for name in names):
                return index
        return None

    question_col, options_col = header.index('savol'), header.index('variantlar')
    answer_col, points_col = column("to'g'ri javob"), column('ball')

    questions, warnings = [], []
    for row in sheet.iter_rows(min_row=2):
        text = _cell_text(_row_value(row, question_col))
        if not text:
            continue
        options = []
        for part in _OPTION_SPLIT_RE.split(_cell_text(_row_value(row, options_col))):
            match = _OPTION_PART_RE.match(part.strip())
            if match and match.group(2).strip():
                options.append({'letter': match.group(1).upper(), 'text': match.group(2).strip()})
        letters = set()
        if answer_col is not None:
            letters = {c.upper() for c in re.findall(r'[A-Za-z]', _cell_text(_row_value(row, answer_col)))}
        order = len(questions)
        question = {
            'text': text, 'order': order,
            'options': [{'text': o['text'], 'is_correct': o['letter'] in letters, 'order': i}
                        for i, o in enumerate(options)],
        }
        if len(letters) > 1:
            question['type'] = 'multiple'
        if points_col is not None:
            try:
                question['points'] = min(100, max(1, int(round(float(_row_value(row, points_col))))))
            except (TypeError, ValueError):
                pass
        questions.append(question)

        correct = sum(1 for o in question['options'] if o['is_correct'])
        if len(options) < 2:
            warnings.append({'question_number': order + 1, 'reason': 'not_enough_options'})
        elif correct != 1 and not (question.get('type') == 'multiple' and correct >= 2):
            warnings.append({'question_number': order + 1, 'reason': 'answer_not_detected'})
    return {'title': '', 'description': '', 'questions': questions, 'warnings': warnings}


def is_xlsx(filename: str) -> bool:
    return Path(filename or '').suffix.lower() == '.xlsx'
