"""Imtihon qoidalariga qarab AI bilan to'liq test tuzish (har qanday imtihon uchun — IELTS, SAT, milliy...).

Imtihon formati KODDA yozilmaydi: o'qituvchi material bilan birga imtihon qoidalari hujjatini (yoki matnini)
yuklaydi, AI shuni o'qiydi. Qoidalar berilmasa — oddiy variantli (A-B-C-D) test.

Ikki bosqich:
  1. REJA (`plan_exam`): qoidalar matni -> tuzilma. Bo'limlar ketma-ketligi, har bo'limda matn parchasi
     kerakmi, qanday turdagi savollar, nechtadan, qaysi tartibda va talabaga ko'rsatiladigan ko'rsatma.
  2. YOZISH (`generate_section`): har bir bo'lim uchun alohida so'rov — material asosida matn parchasi va
     savollar, rejadagi tartib va sonda.
Natija bizning savol turlarimizga o'tkaziladi va `QuestionWriteSerializer` bilan tekshiriladi (yaroqsizlari
tashlanadi). Shu tariqa har bir test IELTS'dagi kabi ko'p turli savol, bo'limlar va matn parchalari bilan keladi.
"""
import json
import re

from django.conf import settings

from . import llm

# Reja tilidagi blok turlari
KINDS = (
    'mcq', 'mcq_multiple', 'true_false_not_given', 'yes_no_not_given', 'true_false',
    'matching', 'fill_blank', 'short_answer', 'numeric', 'ordering',
)
_TFNG = {'true_false_not_given': ('True', 'False', 'Not Given'), 'yes_no_not_given': ('Yes', 'No', 'Not Given')}
MAX_SECTIONS = 6
MAX_BLOCKS_PER_SECTION = 8
MAX_BLOCK_COUNT = 40

KIND_HELP = '''Block / question kinds (use these names exactly):
- mcq: multiple choice, ONE correct option.            {"kind":"mcq","text":"...","options":["..",".."],"answer":<0-based index>}
- mcq_multiple: choose TWO/THREE, several correct.     {"kind":"mcq_multiple","text":"...","options":[..],"answers":[<idx>,..]}
- true_false_not_given: statement vs passage.          {"kind":"true_false_not_given","text":"<statement>","answer":"true|false|not_given"}
- yes_no_not_given: writer's views/claims.             {"kind":"yes_no_not_given","text":"<statement>","answer":"yes|no|not_given"}
- true_false: plain true/false.                        {"kind":"true_false","text":"...","answer":true}
- matching: match items to a list (headings, people, features, sentence endings).
                                                       {"kind":"matching","text":"<instruction + what is matched>","pairs":[{"left":"..","right":".."},..]}
- fill_blank: sentence/note/summary/table/flow-chart completion; mark every gap as {{1}}, {{2}}, ... in order.
                                                       {"kind":"fill_blank","text":"... {{1}} ... {{2}}","blanks":[["answer","accepted variant"],["answer"]]}
- short_answer: answer in a few words.                 {"kind":"short_answer","text":"...","answers":["..",".."]}
- numeric: a number.                                   {"kind":"numeric","text":"...","answers":["12"],"tolerance":0}
- ordering: put steps in the correct order.            {"kind":"ordering","text":"...","items":["first","second",..]}'''

_PLANNER_SYSTEM = (
    'You are an exam designer. Convert the EXAM FORMAT RULES into a precise JSON test plan.\n'
    'Keep the real order of sections and question blocks exactly as the rules describe them. '
    'Put the student-facing instruction of each block exactly as the real exam prints it '
    '(for example "Choose NO MORE THAN TWO WORDS from the passage for each answer") in "instruction". '
    'If a section needs a reading passage, set "passage" with the word range; otherwise null. '
    'If the rules fix the counts, follow them. If they do not, spread target_total sensibly. If the rules are '
    'unclear, use the most standard interpretation. Never plan more than {max_total} questions in total and '
    f'never more than {MAX_SECTIONS} sections. "rules" lists short generation rules that the question writer must '
    'obey (answer location, word limits, difficulty, language, etc.). "language" is the language the test must be '
    'written in (for example "en", "uz", "ru"), or "auto" to follow the source material.\n\n'
    'Allowed block "type" values: ' + ', '.join(KINDS) + '. Meanings: mcq = one correct option; mcq_multiple = '
    'choose several; true_false_not_given / yes_no_not_given / true_false = statements judged against the text; '
    'matching = match items to a list (headings, people, features, sentence endings); fill_blank = '
    'sentence/note/summary/table/flow-chart completion; short_answer = answer in a few words; numeric = a number; '
    'ordering = put steps in order.\n\n'
    'Return ONLY valid JSON of this exact shape (no markdown):\n'
    '{"exam_name": "...", "language": "auto", "rules": ["..."], "sections": [{"title": "Passage 1", '
    '"passage": {"min_words": 700, "max_words": 900, "description": "..."} , '
    '"blocks": [{"type": "true_false_not_given", "count": 6, "instruction": "...", "options": 4, "points": 1}]}]}'
)

_WRITER_SYSTEM = (
    'You are an expert exam-item writer. Write ONE section of an exam, strictly following the SECTION SPEC and '
    'the exam RULES. Base everything on the SOURCE MATERIAL: every correct answer must be supported by the '
    'passage/material, never invent facts that contradict it. Each question must have exactly one defensible '
    'answer (or the stated number of answers), plausible distractors, and no hints in the wording. '
    'Follow the question blocks in order and give EXACTLY the requested count per block, using the block type as '
    '"kind". Do not number the questions and do not repeat the block instruction inside each question '
    '(it is shown separately). If "passage" is requested, write the passage yourself from the source material '
    '(adapt/rewrite it into a coherent text within the word range, keep it factual); otherwise use "passage": "". '
    'Write in the requested language ("auto" = the language of the source material). Use topics/parts of the material '
    'that differ from "avoid_topics". If "source_material" is empty, there is no source: write original, accurate, '
    'exam-appropriate content yourself about the given "topic" (passages must be factual and well structured), '
    'and make every answer verifiable from the text you wrote.\n\n'
    + KIND_HELP + '\n\n'
    'Return ONLY valid JSON (no markdown): {"passage": "...", "questions": [ ...question objects in order... ]}'
)


def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _strs(value) -> list:
    if isinstance(value, str):
        value = [value]
    out = []
    for item in value if isinstance(value, (list, tuple)) else []:
        text = str(item.get('text') if isinstance(item, dict) else item).strip()
        if text and text.lower() != 'none':
            out.append(text[:500])
    return out


# ─── Reja ──────────────────────────────────────────────────────────────────


def default_plan(count: int) -> dict:
    """Qoidalar berilmaganda: oddiy variantli (A-B-C-D) test."""
    return {
        'exam_name': '', 'language': 'auto', 'rules': [],
        'sections': [{'title': '', 'passage': None, 'blocks': [
            {'type': 'mcq', 'count': count, 'instruction': '', 'options': 4, 'points': 1},
        ]}],
    }


def normalize_plan(raw, *, fallback_count: int) -> dict:
    """Modeldan kelgan rejani tekshirib, xavfsiz chegaralarga keltiradi. Yaroqsiz bo'lsa — oddiy reja."""
    if not isinstance(raw, dict):
        return default_plan(fallback_count)
    max_total = settings.AI_EXAM_MAX_QUESTIONS
    sections, total = [], 0
    for index, section in enumerate((raw.get('sections') or [])[:MAX_SECTIONS], start=1):
        if not isinstance(section, dict):
            continue
        blocks = []
        for block in (section.get('blocks') or [])[:MAX_BLOCKS_PER_SECTION]:
            if not isinstance(block, dict) or block.get('type') not in KINDS:
                continue
            count = _int(block.get('count'), 0)
            if not 1 <= count <= MAX_BLOCK_COUNT:
                continue
            count = min(count, max_total - total)
            if count <= 0:
                break
            total += count
            blocks.append({
                'type': block['type'], 'count': count,
                'instruction': str(block.get('instruction') or '').strip()[:500],
                'options': min(6, max(3, _int(block.get('options'), 4))),
                'points': min(10, max(1, _int(block.get('points'), 1))),
            })
        if not blocks:
            continue
        passage = section.get('passage')
        if isinstance(passage, dict):
            low = max(80, _int(passage.get('min_words'), 300))
            high = max(low, _int(passage.get('max_words'), low + 200))
            passage = {'min_words': min(low, 2000), 'max_words': min(high, 2500),
                       'description': str(passage.get('description') or '')[:300]}
        else:
            passage = None
        sections.append({'title': str(section.get('title') or f'Section {index}')[:200], 'passage': passage,
                         'blocks': blocks})
    if not sections:
        return default_plan(fallback_count)
    return {
        'exam_name': str(raw.get('exam_name') or '')[:200],
        'language': str(raw.get('language') or 'auto')[:20],
        'rules': [str(r)[:400] for r in (raw.get('rules') or []) if str(r).strip()][:20],
        'sections': sections,
    }


def plan_exam(rules_text: str, *, target_total: int, topic: str = '') -> dict:
    """Qoidalar matnidan reja tuzadi. Qoidalar bo'sh bo'lsa — oddiy variantli reja (AI chaqirilmaydi)."""
    rules_text = (rules_text or '').strip()
    if not rules_text:
        return default_plan(target_total)
    user = f'target_total: {target_total}\ntopic: {topic}\n\nEXAM FORMAT RULES:\n{rules_text[:settings.AI_EXAM_RULES_CHARS]}'
    raw = llm.chat_json(_PLANNER_SYSTEM.replace('{max_total}', str(settings.AI_EXAM_MAX_QUESTIONS)), user)
    return normalize_plan(raw, fallback_count=target_total)


# ─── Savollarni bizning turlarga o'tkazish ────────────────────────────────


def _tf_answer(value):
    key = re.sub(r'[\s\-]+', '_', str(value).strip().lower())
    if key in ('true', 'yes', 't', 'y'):
        return 0
    if key in ('false', 'no', 'f', 'n'):
        return 1
    if key in ('not_given', 'notgiven', 'ng', 'not'):
        return 2
    return None


def _to_question(raw, *, points: int):
    """Modeldan kelgan bitta savol -> `create_quiz` formatidagi dict (tekshirilmagan). Yaroqsiz bo'lsa None."""
    if not isinstance(raw, dict) or raw.get('kind') not in KINDS:
        return None
    kind, text = raw['kind'], str(raw.get('text') or '').strip()
    if not text:
        return None
    base = {'text': text, 'points': points}

    if kind == 'mcq':
        options, answer = _strs(raw.get('options')), _int(raw.get('answer'))
        if len(options) < 2 or answer is None or not 0 <= answer < len(options):
            return None
        return {**base, 'type': 'single', 'options': [
            {'text': o, 'is_correct': i == answer, 'order': i} for i, o in enumerate(options)]}

    if kind == 'mcq_multiple':
        options = _strs(raw.get('options'))
        answers = {a for a in (_int(x) for x in (raw.get('answers') or [])) if a is not None and 0 <= a < len(options)}
        if len(options) < 2 or not answers:
            return None
        return {**base, 'type': 'multiple', 'options': [
            {'text': o, 'is_correct': i in answers, 'order': i} for i, o in enumerate(options)]}

    if kind in _TFNG:
        answer = _tf_answer(raw.get('answer'))
        if answer is None:
            return None
        return {**base, 'type': 'single', 'options': [
            {'text': label, 'is_correct': i == answer, 'order': i} for i, label in enumerate(_TFNG[kind])]}

    if kind == 'true_false':
        answer = raw.get('answer')
        if isinstance(answer, str):
            answer = {'true': True, 'false': False, 'yes': True, 'no': False}.get(answer.strip().lower())
        if not isinstance(answer, bool):
            return None
        return {**base, 'type': 'true_false', 'correct_bool': answer}

    if kind == 'matching':
        pairs = []
        for pair in raw.get('pairs') or []:
            if isinstance(pair, dict) and str(pair.get('left') or '').strip() and str(pair.get('right') or '').strip():
                pairs.append({'left': str(pair['left']).strip()[:500], 'right': str(pair['right']).strip()[:500]})
        return {**base, 'type': 'matching', 'pairs': pairs[:12]} if len(pairs) >= 2 else None

    if kind == 'fill_blank':
        markers = [int(n) for n in re.findall(r'\{\{(\d+)\}\}', text)]
        blanks = []
        for item in raw.get('blanks') or []:
            answers = _strs(item)
            if answers:
                blanks.append({'answers': answers})
        if not blanks or markers != list(range(1, len(markers) + 1)) or len(markers) > len(blanks):
            return None
        return {**base, 'type': 'fill_blank', 'blanks': blanks[:len(markers)]}

    if kind == 'short_answer':
        answers = _strs(raw.get('answers') if raw.get('answers') is not None else raw.get('answer'))
        return {**base, 'type': 'text', 'accepted_answers': answers} if answers else None

    if kind == 'numeric':
        answers = _strs(raw.get('answers') if raw.get('answers') is not None else raw.get('answer'))
        if not answers:
            return None
        tolerance = raw.get('tolerance')
        return {**base, 'type': 'numeric', 'accepted_answers': answers,
                'tolerance': float(tolerance) if isinstance(tolerance, (int, float)) and tolerance >= 0 else 0}

    items = _strs(raw.get('items'))  # ordering
    return {**base, 'type': 'ordering', 'items': items} if len(items) >= 2 else None


def _validated(question: dict):
    """Haqiqiy test yaratish qoidalari bo'yicha tekshiradi (qoralama rejimida). Yaroqsiz bo'lsa None."""
    from .serializers import QuestionWriteSerializer

    serializer = QuestionWriteSerializer(data=question, context={'draft': True})
    return serializer.validated_data if serializer.is_valid() else None


# ─── Bo'lim yozish ─────────────────────────────────────────────────────────


def generate_section(plan: dict, index: int, material: str, *, avoid_topics: list, topic: str = '') -> dict:
    """`plan['sections'][index]` uchun matn parchasi va savollar. Qaytaradi:
    {'title', 'passage', 'questions': [{...create_quiz formati, 'block': i}], 'dropped': n, 'missing': n}."""
    section = plan['sections'][index]
    spec = {
        'section_number': index + 1, 'sections_total': len(plan['sections']), 'title': section['title'],
        'passage': section['passage'], 'blocks': section['blocks'],
    }
    user = json.dumps({
        'section_spec': spec, 'exam_rules': plan['rules'], 'language': plan['language'],
        'avoid_topics': avoid_topics, 'topic': topic,
        'source_material': material[:settings.AI_EXAM_MATERIAL_CHARS],
    }, ensure_ascii=False)
    data = llm.chat_json(_WRITER_SYSTEM, user)

    passage = str(data.get('passage') or '').strip() if section['passage'] else ''
    if section['passage'] and len(passage) < 150:
        raise llm.LLMError('AI matn parchasini yozmadi (bo\'sh/juda qisqa javob).')

    raw_questions = [q for q in (data.get('questions') or []) if isinstance(q, dict)]
    result, dropped, missing = [], 0, 0
    for block_index, block in enumerate(section['blocks']):
        mine = []
        for raw in list(raw_questions):
            if len(mine) >= block['count']:
                break
            if raw.get('kind') == block['type']:
                raw_questions.remove(raw)
                converted = _to_question(raw, points=block['points'])
                valid = _validated(converted) if converted else None
                if valid is None:
                    dropped += 1
                    continue
                mine.append(valid)
        missing += max(0, block['count'] - len(mine))
        if mine and block['instruction']:
            mine[0] = {**mine[0], 'text': f"{block['instruction']}\n\n{mine[0]['text']}"}
        result.extend({**q, 'block': block_index} for q in mine)
    return {'title': section['title'], 'passage': passage, 'questions': result, 'dropped': dropped, 'missing': missing}


def assemble(plan: dict, sections: list) -> tuple:
    """Bo'limlar natijasidan `create_quiz` uchun (groups, questions, summary) yig'adi."""
    groups, questions, dropped, missing = [], [], 0, 0
    for section in sections:
        group_index = None
        if section['passage']:
            group_index = len(groups)
            groups.append({'title': section['title'], 'passage': section['passage'][:30000]})
        for question in section['questions']:
            item = {k: v for k, v in question.items() if k != 'block'}
            item['group'] = group_index
            item['order'] = len(questions)
            questions.append(item)
        dropped += section['dropped']
        missing += section['missing']
    summary = f"{len(sections)} bo'lim · {len(questions)} savol"
    if dropped or missing:
        summary += f" ({dropped + missing} ta savol yaroqsiz/yetishmagani uchun tushib qoldi)"
    return groups, questions, summary
