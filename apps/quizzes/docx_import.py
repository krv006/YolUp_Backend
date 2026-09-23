"""O'qituvchi yuklagan .docx fayldan test savollarini ajratib olish (import).

Kutilgan format (real namunaga asoslangan — standart o'quv markazlarida keng
tarqalgan uslub):

    <sarlavha qatori(lari) — birinchi savoldan oldin>

    1. Savol matni?
    A) Variant 1
    B) Variant 2
    ...
    To'g'ri javob: B

Bu app'ning sxemasi oddiy (Quiz -> Question -> Option, har savolda aynan
bitta to'g'ri variant — `QuestionWriteSerializer.validate_options`), shuning
uchun parser ham shunga mos: standart/knowledge_node/verify kabi maydonlar
YO'Q, chunki ular DB'da mavjud emas.

Bitta savolning javobi noaniq bo'lsa (javob qatori yo'q yoki variant harfiga
mos kelmasa) butun faylni to'xtatmaymiz — shu savol `warnings`da belgilanib,
`is_correct=False` bilan preview'ga qo'shiladi, o'qituvchi ko'rib tuzatadi.
"""
import re
from io import BytesIO

MAX_IMPORT_FILE_SIZE_MB = 10

_APOSTROPHE_MAP = str.maketrans({
    '‘': "'", '’': "'", 'ʻ': "'", 'ʼ': "'", '`': "'",
})

_QUESTION_RE = re.compile(r'^\s*\d+[.\)]\s+(.+)$')
_OPTION_RE = re.compile(r'^\s*([A-Za-z])[.\)]\s+(.+)$')
_ANSWER_RE = re.compile(
    r"^(?:to'g'ri\s+javob|javob|answer|correct\s+answer)\s*[:\-]\s*([A-Za-z])\.?\s*$",
    re.IGNORECASE,
)


def _normalize(line: str) -> str:
    return line.translate(_APOSTROPHE_MAP).strip()


def _finalize_question(question: dict) -> dict:
    answer_letter = question.pop('answer_letter', None)
    options = []
    for index, opt in enumerate(question['options']):
        options.append({
            'text': opt['text'].strip(),
            'is_correct': bool(answer_letter) and opt['letter'] == answer_letter,
            'order': index,
        })
    question['options'] = options
    question['text'] = question['text'].strip()
    return question


def parse_docx_questions(file_obj) -> dict:
    """`.docx` fayl (fayl-obyekt yoki yo'l)ni preview strukturasiga aylantiradi.

    Qaytaradi: {'title': str, 'description': str,
                'questions': [{'text', 'order', 'options': [{'text','is_correct','order'}]}],
                'warnings': [{'question_number', 'reason'}]}
    """
    import docx  # python-docx — lazy, faqat import vaqtida kerak

    data = file_obj.read() if hasattr(file_obj, 'read') else file_obj
    if isinstance(data, (bytes, bytearray)):
        data = BytesIO(data)
    document = docx.Document(data)

    lines = [_normalize(p.text) for p in document.paragraphs if p.text and p.text.strip()]
    return parse_lines(lines)


def parse_lines(lines: list) -> dict:
    """Matn qatorlaridan savollarni ajratib olish — manbadan mustaqil
    (`.docx` paragraflari yoki Google Docs'dan olingan oddiy matn qatorlari
    bo'lishi mumkin, format bir xil — `apps.quizzes.google_docs_import`)."""
    title_lines: list = []
    questions: list = []
    current = None

    for line in lines:
        m_question = _QUESTION_RE.match(line)
        m_option = _OPTION_RE.match(line) if current is not None else None
        m_answer = _ANSWER_RE.match(line) if current is not None else None

        if m_question:
            if current is not None:
                questions.append(_finalize_question(current))
            current = {'text': m_question.group(1), 'order': len(questions), 'options': [], 'answer_letter': None}
        elif m_answer:
            current['answer_letter'] = m_answer.group(1).upper()
        elif m_option:
            current['options'].append({'letter': m_option.group(1).upper(), 'text': m_option.group(2)})
        elif current is not None:
            # Ko'p qatorli savol/variant matnining davomi
            if current['options']:
                current['options'][-1]['text'] += ' ' + line
            else:
                current['text'] += ' ' + line
        else:
            title_lines.append(line)

    if current is not None:
        questions.append(_finalize_question(current))

    warnings = []
    for q in questions:
        correct_count = sum(1 for o in q['options'] if o['is_correct'])
        if len(q['options']) < 2:
            warnings.append({'question_number': q['order'] + 1, 'reason': 'not_enough_options'})
        elif correct_count != 1:
            warnings.append({'question_number': q['order'] + 1, 'reason': 'answer_not_detected'})

    return {
        'title': (title_lines[0] if title_lines else '')[:200],
        'description': ' '.join(title_lines[1:])[:2000],
        'questions': questions,
        'warnings': warnings,
    }
