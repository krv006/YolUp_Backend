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
import logging
import random
import re
import uuid

from django.conf import settings

from . import llm, mathcheck

logger = logging.getLogger('apps')

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
    'If a section is a LISTENING section (the student listens to a recording), set "audio" instead of "passage": '
    '{"min_words": 500, "max_words": 800, "speakers": 2, "description": "..."} (a real recording lasts 4-5 minutes, '
    'about 130 spoken words per minute) - the platform writes the script and '
    'turns it into spoken audio with a separate voice per speaker (a monologue has 1 speaker, a conversation 2-4). '
    'If the rules fix the counts, follow them. If they do not, use the official question counts and points of '
    'the exam; when a numeric target_total is given and the exam has no fixed count, spread it sensibly. If the rules are '
    'unclear, use the most standard interpretation. Never plan more than {max_total} questions in total and '
    f'never more than {MAX_SECTIONS} sections. "rules" lists short generation rules that the question writer must '
    'obey (answer location, word limits, difficulty, language, etc.). "language" is the language the test must be '
    'written in (for example "en", "uz", "ru"), or "auto" to follow the source material.\n\n'
    'If SOURCE MATERIAL is given, look at it and decide which part of the exam each section can be written from: '
    'set "focus" of every section to a short note on WHICH topic/chapter/part of the material that section must '
    'use (different sections use different parts when the material is long). Plan only sections that can be '
    'written from text or from a spoken script; never plan image-, map- or diagram-based sections, and never plan '
    'Speaking or Writing sections. If the material is short, reduce counts '
    'proportionally but keep the exam section order and question types.\n'
    'Allowed block "type" values: ' + ', '.join(KINDS) + '. Meanings: mcq = one correct option; mcq_multiple = '
    'choose several; true_false_not_given / yes_no_not_given / true_false = statements judged against the text; '
    'matching = match items to a list (headings, people, features, sentence endings); fill_blank = '
    'sentence/note/summary/table/flow-chart completion; short_answer = answer in a few words; numeric = a number; '
    'ordering = put steps in order.\n\n'
    'Return ONLY valid JSON of this exact shape (no markdown):\n'
    '{"exam_name": "...", "language": "auto", "rules": ["..."], "sections": [{"title": "Passage 1", '
    '"passage": {"min_words": 700, "max_words": 900, "description": "..."} , "audio": null, '
    '"focus": "...", "blocks": [{"type": "true_false_not_given", "count": 6, "instruction": "...", "options": 4, "points": 1}]}]}'
)

_WRITER_SYSTEM = (
    'You are an expert exam-item writer. Write ONE section of an exam, strictly following the SECTION SPEC and '
    'the exam RULES. Base everything on the SOURCE MATERIAL: every correct answer must be supported by the '
    'passage/material, never invent facts that contradict it. Each question must have exactly one defensible '
    'answer (or the stated number of answers), plausible distractors, and no hints in the wording. '
    'Copy answers exactly as spelled in the passage (keep British/American spelling and word forms). For '
    'short_answer, fill_blank and numeric items every accepted answer must be words that appear in the passage '
    '(or a trivial variant such as capitalisation or a number written as a figure): never list synonyms, '
    'paraphrases or guesses, and give at most three accepted answers. Never write a '
    'question that has several valid answers in the passage (for example "which city" when several cities are '
    'named). For true/false/not given and yes/no/not given blocks use all three outcomes in a realistic mix: NOT '
    'GIVEN means the passage neither confirms nor contradicts the statement. '
    'Follow the question blocks in order. For every block write its "count" questions PLUS its "spare" extra '
    'questions of the same kind (spares replace questions that fail validation; put the best questions first). '
    'Use the block type as "kind" and put the block "index" into every question as "block". '
    'For fill_blank blocks "count" is the number of GAPS: one note/form/table/summary item with {{1}}..{{n}} counts '
    'as n, so a block of 10 gaps is ONE item with ten gaps (or several items whose gaps add up to 10). '
    'For numeric questions, and for mcq whose correct option is a number, ALSO add "check": a pure arithmetic '
    'expression (digits, + - * / ^ ( ) and sqrt() only, no words or units) whose value equals the correct answer, '
    'e.g. "check": "3*(4+5)"; it is used to verify your answer automatically. Omit it when the answer is not a '
    'single computable number. '
    'Do not number the questions and do not repeat the block instruction inside each question '
    '(it is shown separately). The section spec may carry a "focus": use that part of the material for this section. If "passage" is requested, write the passage yourself from the source material '
    '(adapt/rewrite it into a coherent text within the word range, keep it factual); otherwise use "passage": "". '
    'If "audio" is requested, this is a LISTENING section: write a natural spoken SCRIPT as a list of turns '
    '{"speaker": "A", "text": "..."} (speakers A-D; a monologue uses only A; no stage directions, no question text, '
    'numbers/names/spellings dictated naturally as in the real exam, with the realistic distractors and '
    'self-corrections of the exam). Every answer must be clearly stated in the script and the questions must be '
    'answerable only by listening; use "passage": "". The script must contain AT LEAST "min_words" words: a real '
    'recording is 4-5 minutes long, so write a full, detailed conversation or talk with realistic distractors '
    '(e.g. a speaker corrects a day or a number, offers alternatives, spells a name) instead of stating each answer '
    'once in plain words. '
    'Write in the requested language ("auto" = the language of the source material). Use topics/parts of the material '
    'that differ from "avoid_topics" and write NEW questions that do not repeat or closely paraphrase any text in '
    '"avoid_questions" (questions that already exist). If "source_material" is empty, there is no source: write original, accurate, '
    'exam-appropriate content yourself about the given "topic" (passages must be factual and well structured), '
    'and make every answer verifiable from the text you wrote.\n\n'
    + KIND_HELP + '\n\n'
    'Return ONLY valid JSON (no markdown): {"passage": "...", "script": [{"speaker": "A", "text": "..."}], '
    '"questions": [ ...question objects in order... ]} ("script" only for an audio section).'
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
        audio = section.get('audio')
        if isinstance(audio, dict):  # Listening: audio matn parchasining o'rnini bosadi (skript o'quvchiga ko'rsatilmaydi)
            low = max(350, _int(audio.get('min_words'), 500))  # haqiqiy yozuv ~4-5 daqiqa (daqiqasiga ~130 so'z)
            high = max(low, _int(audio.get('max_words'), low + 300))
            audio = {'min_words': min(low, 1200), 'max_words': min(high, 1500),
                     'speakers': min(4, max(1, _int(audio.get('speakers'), 2))),
                     'description': str(audio.get('description') or '')[:300]}
            passage = None
        else:
            audio = None
        sections.append({'title': str(section.get('title') or f'Section {index}')[:200], 'passage': passage,
                         'audio': audio, 'focus': str(section.get('focus') or '')[:300], 'blocks': blocks})
    if not sections:
        return default_plan(fallback_count)
    return {
        'exam_name': str(raw.get('exam_name') or '')[:200],
        'language': str(raw.get('language') or 'auto')[:20],
        'rules': [str(r)[:400] for r in (raw.get('rules') or []) if str(r).strip()][:20],
        'sections': sections,
    }


def _material_outline(material: str, limit: int = 12000) -> str:
    """Rejaga ko'rsatiladigan material: qisqa bo'lsa to'liq, uzun bo'lsa boshi/o'rtasi/oxiridan bo'laklar."""
    if len(material) <= limit:
        return material
    third = limit // 3
    mid = len(material) // 2
    return '\n[...]\n'.join([material[:third], material[mid - third // 2: mid + third // 2], material[-third:]])


def plan_exam(rules_text: str, *, target_total: int, topic: str = '', exam_name: str = '', material: str = '') -> dict:
    """Reja tuzadi. Manba: (1) o'qituvchining qoidalar matni, (2) imtihon nomi — AI uning rasmiy tuzilmasini
    o'zi eslaydi (IELTS, SAT...), (3) ikkalasi ham bo'sh — oddiy variantli reja (AI chaqirilmaydi).
    Qoidalar va nom birga berilsa, qoidalar ustun."""
    rules_text = (rules_text or '').strip()
    exam_name = (exam_name or '').strip()
    if not rules_text and not exam_name:
        return default_plan(target_total or 20)
    total = f'target_total: {target_total}' if target_total else 'target_total: auto (use the official counts of the exam)'
    parts = [total, f'topic: {topic}']
    if exam_name:
        parts.append(f'exam: {exam_name}')
    if rules_text:
        parts.append('EXAM FORMAT RULES (they override your own knowledge of the exam):\n'
                     + rules_text[:settings.AI_EXAM_RULES_CHARS])
    else:
        parts.append(
            'EXAM FORMAT RULES: none provided. Use your own knowledge of the official/standard format of the exam '
            f'named above ("{exam_name}") as accurately as you can: its sections, question types, counts and order. '
            'If you do not recognise the exam, return a simple plan of one section with multiple-choice questions.')
    if material.strip():
        parts.append('SOURCE MATERIAL (excerpt):\n' + _material_outline(material))
    raw = llm.chat_json(_PLANNER_SYSTEM.replace('{max_total}', str(settings.AI_EXAM_MAX_QUESTIONS)),
                        '\n'.join(parts))
    return normalize_plan(raw, fallback_count=target_total or 20)


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


_LETTER_REFERENCE = re.compile(r'\b(above|both|all of|none of|neither|a and b|b and c|a and c)\b', re.IGNORECASE)


_LETTER_PREFIX = re.compile(r'^\(?([A-Ha-h])[\.\):]\s+')


def _strip_letters(options: list) -> list:
    """Model variantlarni "A. ...", "B) ..." deb yozsa, shu belgilar olib tashlanadi — faqat HAMMA variantda ketma-ket
    harflar (A, B, C...) bo'lsa (aks holda "A. Smith" kabi haqiqiy matn buzilmasin)."""
    matches = [_LETTER_PREFIX.match(o) for o in options]
    if all(matches) and [m.group(1).upper() for m in matches] == [chr(65 + i) for i in range(len(options))]:
        return [o[m.end():] for o, m in zip(options, matches)]
    return options


def _option_dicts(options: list, correct: set) -> list:
    """Variantlar ro'yxati; to'g'ri javob doim bir xil joyda (masalan, "B") bo'lib qolmasligi uchun aralashtiriladi.
    "yuqoridagilarning hammasi" kabi boshqa variantga ishora qiladigan variant bo'lsa — tartib saqlanadi."""
    options = _strip_letters(options)
    order = list(range(len(options)))
    if not any(_LETTER_REFERENCE.search(o) for o in options):
        random.shuffle(order)
    return [{'text': options[old], 'is_correct': old in correct, 'order': new} for new, old in enumerate(order)]


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
        return {**base, 'type': 'single', 'options': _option_dicts(options, {answer})}

    if kind == 'mcq_multiple':
        options = _strs(raw.get('options'))
        answers = {a for a in (_int(x) for x in (raw.get('answers') or [])) if a is not None and 0 <= a < len(options)}
        if len(options) < 2 or not answers:
            return None
        return {**base, 'type': 'multiple', 'options': _option_dicts(options, answers)}

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
    if serializer.is_valid():
        return serializer.validated_data
    logger.info("AI savoli yaroqsiz (%s): %s", question.get('type'), str(serializer.errors)[:300])
    return None


def _belongs(raw: dict, block_index: int, block: dict) -> bool:
    """Savol shu blokka tegishlimi: turi mos va (model `block` raqamini yozgan bo'lsa) raqami ham mos."""
    if raw.get('kind') != block['type']:
        return False
    marker = _int(raw.get('block'))
    return marker is None or marker == block_index


def _script_turns(data: dict) -> list:
    """Modelning `script` ro'yxatini tozalaydi: [{'speaker': 'A', 'text': '...'}]."""
    turns = []
    for item in data.get('script') or []:
        if isinstance(item, dict):
            text = str(item.get('text') or '').strip()
            speaker = str(item.get('speaker') or 'A').strip().upper()[:1] or 'A'
            if text:
                turns.append({'speaker': speaker, 'text': text[:1500]})
    return turns


def _words(text: str) -> int:
    return len(text.split())


def _transcript(turns: list) -> str:
    return '\n'.join(f"{t['speaker']}: {t['text']}" for t in turns)


def _trim_turns(turns: list) -> list:
    """Juda uzun skriptni chegaragacha qisqartiradi (ovoz xarajati va audio uzunligi cheklanadi)."""
    kept, total = [], 0
    for turn in turns:
        total += len(turn['text']) + 3
        if total > settings.AI_EXAM_AUDIO_MAX_CHARS:
            break
        kept.append(turn)
    return kept


def _synthesize(turns: list) -> bytes:
    """Skriptni ovozga aylantiradi: har gapiruvchiga o'z ovozi, mp3 bo'laklari ketma-ket ulanadi."""
    voices = settings.OPENAI_TTS_VOICES or ['alloy']
    assigned = {}
    chunks = []
    for turn in turns:
        voice = assigned.setdefault(turn['speaker'], voices[len(assigned) % len(voices)])
        chunks.append(llm.speech(turn['text'], voice))
    return b''.join(chunks)


def _store_audio(data: bytes) -> str:
    """Tayyor audioni vaqtincha saqlaydi (test yaratilgach guruhga biriktiriladi va o'chiriladi)."""
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    return default_storage.save(f'ai_quiz_audio/{uuid.uuid4().hex}.mp3', ContentFile(data))


def _spares(count: int) -> int:
    return 2 if count >= 3 else 1  # tushib qoladigan savollar o'rniga zaxira


def _size(question: dict) -> int:
    """Savol blokdagi nechta o'rinni egallaydi: fill_blank - bo'shliqlar soni, qolganlari - 1."""
    return len(question.get('blanks') or []) if question.get('type') == 'fill_blank' else 1


_JUDGE_SYSTEM = (
    'You are a strict but fair exam reviewer. You get a SOURCE (reading passage, listening script or study material; '
    'it may be empty) and numbered exam QUESTIONS with the intended correct answers marked. For each question decide '
    'whether it is sound: the marked answer must be correct and supported by the source (or, when the source is '
    'empty, be a well-established fact), exactly one answer must be defensible, the wording must not give the answer '
    'away, and the question must be understandable on its own. Reject a question ONLY when you are confident it is '
    'wrong, unsupported by the source, ambiguous or broken; style preferences are not a reason to reject. '
    'Return ONLY JSON: {"verdicts": [{"id": 0, "ok": true, "problem": ""}, ...]} with one entry per question id.'
)


def _judge_view(number: int, question: dict) -> dict:
    kind = question.get('type')
    view = {'id': number, 'type': kind, 'question': question.get('text', '')}
    if kind in ('single', 'multiple'):
        view['options'] = [o['text'] for o in question.get('options', [])]
        view['correct'] = [o['text'] for o in question.get('options', []) if o.get('is_correct')]
    elif kind == 'true_false':
        view['correct'] = bool(question.get('correct_bool'))
    elif kind == 'matching':
        view['pairs'] = [[p['left'], p['right']] for p in question.get('pairs', [])]
    elif kind == 'fill_blank':
        view['correct_per_gap'] = [b.get('answers') for b in question.get('blanks', [])]
    elif kind in ('text', 'numeric'):
        view['accepted_answers'] = question.get('accepted_answers', [])
    elif kind == 'ordering':
        view['correct_order'] = question.get('items', [])
    return view


def _judge(candidates: list, source: str, language: str) -> set:
    """Bo'lim savollarini AI bilan tekshiradi (javob manbaga mosmi, bitta to'g'ri javob bormi). Qaytaradi: tashlanadigan
    nomzodlar tartib raqamlari. Tekshiruv ishlamasa yoki shubhali bo'lsa (savollarning ko'pi rad etilsa) - hech narsa
    tashlanmaydi: tekshiruv hech qachon test yaratishni to'xtatmasligi kerak."""
    payload = json.dumps({
        'source': source, 'language': language,
        'questions': [_judge_view(number, q) for number, (_block, q, _spare) in enumerate(candidates)],
    }, ensure_ascii=False)
    try:
        data = llm.chat_json(_JUDGE_SYSTEM, payload, max_tokens=2500)
    except llm.LLMError as exc:
        logger.warning("AI tekshiruvi ishlamadi, o'tkazib yuborildi: %s", exc)
        return set()
    bad = set()
    for item in data.get('verdicts') or []:
        number = _int(item.get('id')) if isinstance(item, dict) else None
        if number is not None and 0 <= number < len(candidates) and item.get('ok') is False:
            bad.add(number)
            logger.info("AI tekshiruvi savolni rad etdi (%s): %s", item.get('problem'),
                        str(candidates[number][1].get('text'))[:120])
    if len(bad) * 10 > len(candidates) * 6:  # >60% rad - tekshiruvchining o'zi adashgan bo'lishi mumkin
        logger.warning("AI tekshiruvi savollarning ko'pini rad etdi (%d/%d) - e'tiborga olinmadi", len(bad), len(candidates))
        return set()
    return bad


# ─── Bo'lim yozish ─────────────────────────────────────────────────────────


def generate_section(plan: dict, index: int, material: str, *, avoid_topics: list, topic: str = '',
                     avoid_questions: list = ()) -> dict:
    """`plan['sections'][index]` uchun matn parchasi va savollar. Qaytaradi:
    {'title', 'passage', 'questions': [{...create_quiz formati, 'block': i}], 'dropped': n, 'missing': n}."""
    section = plan['sections'][index]
    spec = {
        'section_number': index + 1, 'sections_total': len(plan['sections']), 'title': section['title'],
        'passage': section['passage'], 'audio': section.get('audio'), 'focus': section.get('focus', ''),
        'blocks': [{**block, 'index': i, 'spare': _spares(block['count'])} for i, block in enumerate(section['blocks'])],
    }
    payload = {
        'section_spec': spec, 'exam_rules': plan['rules'], 'language': plan['language'],
        'avoid_topics': avoid_topics, 'topic': topic,
        'source_material': material[:settings.AI_EXAM_MATERIAL_CHARS],
    }
    if avoid_questions:  # shu o'qituvchining oldingi testlaridagi savollar - takrorlanmasin
        payload['avoid_questions'] = list(avoid_questions)
    user = json.dumps(payload, ensure_ascii=False)
    data = llm.chat_json(_WRITER_SYSTEM, user)
    if section.get('audio'):  # Listening skripti juda qisqa bo'lsa — bir marta kengaytirishni so'raymiz
        words, wanted = _words(_transcript(_script_turns(data))), section['audio']['min_words']
        if words < wanted * 0.7:
            retry = json.dumps({
                **json.loads(user),
                'problem': f'Your previous script had only {words} words; it must have at least {wanted}. '
                           'Write the FULL script again, longer and with realistic distractors, and re-write the '
                           'questions to match it.',
            }, ensure_ascii=False)
            data = llm.chat_json(_WRITER_SYSTEM, retry)

    passage = str(data.get('passage') or '').strip() if section['passage'] else ''
    if section['passage'] and len(passage) < 150:
        raise llm.LLMError('AI matn parchasini yozmadi (bo\'sh/juda qisqa javob).')

    transcript, audio_path = '', ''
    if section.get('audio'):
        turns = _script_turns(data)
        if len(_transcript(turns)) < 200 or _words(_transcript(turns)) < section['audio']['min_words'] * 0.4:
            raise llm.LLMError('AI audio skriptini yozmadi (bo\'sh/juda qisqa javob).')
        if len(_transcript(turns)) > settings.AI_EXAM_AUDIO_MAX_CHARS:
            turns = _trim_turns(turns)
        transcript = _transcript(turns)
        audio_path = _store_audio(_synthesize(turns))

    raw_questions = [q for q in (data.get('questions') or []) if isinstance(q, dict)]
    judging = bool(settings.AI_EXAM_JUDGE)
    candidates, dropped = [], 0  # candidates: [(blok, savol, zaxirami)]
    for block_index, block in enumerate(section['blocks']):
        filled, spare_taken = 0, 0
        for raw in list(raw_questions):
            over = filled >= block['count']
            if over and not (judging and _int(raw.get('block')) == block_index and spare_taken < _spares(block['count'])):
                break
            if _belongs(raw, block_index, block):
                raw_questions.remove(raw)
                if mathcheck.contradicts(raw):  # javobi hisobga zid - zaxira savol o'rniga keladi
                    dropped += 1
                    continue
                converted = _to_question(raw, points=block['points'])
                valid = _validated(converted) if converted else None
                if valid is None:
                    dropped += 1
                    if converted is None:
                        logger.info("AI savoli shaklga kelmadi (%s): %s", raw.get('kind'), str(raw)[:200])
                    continue
                candidates.append((block_index, valid, over))
                if over:
                    spare_taken += 1
                else:
                    filled += _size(valid)

    rejected = _judge(candidates, passage or transcript or material[:settings.AI_EXAM_JUDGE_CHARS], plan['language']) \
        if judging and candidates else set()
    dropped += len(rejected)

    result, missing = [], 0
    for block_index, block in enumerate(section['blocks']):
        mine, filled = [], 0
        for number, (owner, valid, _spare) in enumerate(candidates):
            if owner != block_index or number in rejected or filled >= block['count']:
                continue
            mine.append(valid)
            filled += _size(valid)
        missing += max(0, block['count'] - filled)
        if mine and block['instruction']:
            mine[0] = {**mine[0], 'text': f"{block['instruction']}\n\n{mine[0]['text']}"}
        result.extend({**q, 'block': block_index} for q in mine)
    return {'title': section['title'], 'passage': passage, 'transcript': transcript, 'audio_path': audio_path,
            'questions': result, 'dropped': dropped, 'missing': missing}


def assemble(plan: dict, sections: list) -> tuple:
    """Bo'limlar natijasidan `create_quiz` uchun (groups, questions, summary) yig'adi."""
    groups, questions, dropped, missing = [], [], 0, 0
    for section in sections:
        group_index = None
        if section['passage'] or section.get('audio_path'):
            group_index = len(groups)
            groups.append({
                'title': section['title'], 'passage': section['passage'][:30000],
                'transcript': section.get('transcript', '')[:30000], 'audio_path': section.get('audio_path', ''),
            })
        for question in section['questions']:
            item = {k: v for k, v in question.items() if k != 'block'}
            item['group'] = group_index
            item['order'] = len(questions)
            questions.append(item)
        dropped += section['dropped']
        missing += section['missing']
    summary = f"{len(sections)} bo'lim · {len(questions)} savol"
    if missing:  # zaxira savollar bilan to'ldirilgan yaroqsizlar (dropped) hisobga olinmaydi — faqat reja bo'yicha yetishmaganlar
        summary += f" ({missing} ta savol yetishmagani uchun tushib qoldi)"
    return groups, questions, summary
