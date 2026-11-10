"""Vazifa ichidagi savollar: tuzish, javoblarni qabul qilish, avtomatik baholash va AI/o'qituvchi ballari bilan birlashtirish (2026-11-10)."""
import math

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from .models import AssignmentQuestion, SubmissionAnswer

T = AssignmentQuestion.Type
TEST_TYPES = (T.SINGLE, T.MULTIPLE)
OPEN_TYPES = (T.SHORT, T.LONG)
MAX_QUESTIONS = 100
MAX_OPTIONS = 10
MAX_TEXT = 5000
MAX_ANSWER = 10000
MAX_POINTS = 1000


def _err(index: int, field: str, message) -> ValidationError:
    return ValidationError({'questions': {index: {field: message}}})


def clean_questions(raw) -> list:
    """Savollar ro'yxatini tekshiradi: `[{type, text, options?, correct?, points?}]`."""
    if raw in (None, ''):
        return []
    if not isinstance(raw, list):
        raise ValidationError({'questions': _("Savollar ro'yxat bo'lishi kerak.")})
    if len(raw) > MAX_QUESTIONS:
        raise ValidationError({'questions': _("Ko'pi bilan %(n)s ta savol.") % {'n': MAX_QUESTIONS}})
    cleaned = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise _err(index, 'detail', _("Savol obyekt bo'lishi kerak."))
        qtype = item.get('type')
        if qtype not in AssignmentQuestion.Type.values:
            raise _err(index, 'type', _("single, multiple, short yoki long."))
        text = str(item.get('text') or '').strip()
        if not text or len(text) > MAX_TEXT:
            raise _err(index, 'text', _("Savol matni kerak (1-5000 belgi)."))
        points = item.get('points', 1)
        if isinstance(points, bool) or not isinstance(points, int) or not 1 <= points <= MAX_POINTS:
            raise _err(index, 'points', _("Ball 1 dan 1000 gacha butun son."))
        options, correct = [], []
        if qtype in TEST_TYPES:
            options = [str(o or '').strip() for o in (item.get('options') or [])]
            if not 2 <= len(options) <= MAX_OPTIONS or any(not o or len(o) > 500 for o in options):
                raise _err(index, 'options', _("2 dan 10 gacha bo'sh bo'lmagan variant kerak."))
            correct = item.get('correct')
            if not isinstance(correct, list) or any(isinstance(c, bool) or not isinstance(c, int) or not 0 <= c < len(options) for c in correct):
                raise _err(index, 'correct', _("To'g'ri javob indekslari ro'yxati kerak."))
            correct = sorted(set(correct))
            if not correct or (qtype == T.SINGLE and len(correct) != 1):
                raise _err(index, 'correct', _("Bitta to'g'ri javobli savolda aynan bitta, boshqasida kamida bitta to'g'ri javob kerak."))
        cleaned.append({'type': qtype, 'text': text, 'options': options, 'correct': correct, 'points': points})
    return cleaned


def set_questions(assignment, cleaned: list) -> None:
    """Savollarni to'liq almashtiradi (topshiriqlar bo'lmaganda)."""
    assignment.questions.all().delete()
    AssignmentQuestion.objects.bulk_create([
        AssignmentQuestion(assignment=assignment, order=i, **item) for i, item in enumerate(cleaned)
    ])


def questions_payload(assignment, include_correct: bool) -> list:
    rows = []
    for q in assignment.questions.all():
        row = {'id': str(q.id), 'order': q.order, 'type': q.type, 'text': q.text, 'options': q.options, 'points': q.points}
        if include_correct:
            row['correct'] = q.correct
        rows.append(row)
    return rows


def total_points(assignment) -> int:
    return sum(q.points for q in assignment.questions.all())


# ── javoblar ────────────────────────────────────────────────────────────────

def parse_answers(assignment, raw) -> list:
    """`[{question_id, answer}]` -> [(savol, tozalangan javob)]. Test: tanlangan indekslar; ochiq: matn. Javobsiz savollar 0 ball."""
    if raw in (None, ''):
        return []
    if not isinstance(raw, list):
        raise ValidationError({'answers': _("Javoblar ro'yxat bo'lishi kerak.")})
    questions = {str(q.id): q for q in assignment.questions.all()}
    seen, result = set(), []
    for item in raw:
        if not isinstance(item, dict) or str(item.get('question_id')) not in questions:
            raise ValidationError({'answers': _("Noma'lum savol.")})
        question = questions[str(item['question_id'])]
        if str(question.id) in seen:
            raise ValidationError({'answers': _("Bitta savolga ikki marta javob berilgan.")})
        seen.add(str(question.id))
        answer = item.get('answer')
        if question.type in TEST_TYPES:
            chosen = answer if isinstance(answer, list) else ([] if answer in (None, '') else [answer])
            if any(isinstance(c, bool) or not isinstance(c, int) or not 0 <= c < len(question.options) for c in chosen):
                raise ValidationError({'answers': _("Variant indeksi noto'g'ri.")})
            chosen = sorted(set(chosen))
            if question.type == T.SINGLE and len(chosen) > 1:
                raise ValidationError({'answers': _("Bu savolda faqat bitta variant tanlanadi.")})
            result.append((question, chosen))
        else:
            text = str(answer or '').strip()
            if len(text) > MAX_ANSWER:
                raise ValidationError({'answers': _("Javob juda uzun.")})
            result.append((question, text))
    return result


def auto_score(question, answer) -> float | None:
    """Test: to'g'ri bo'lsa to'liq ball, aks holda 0 (bir nechta to'g'ri javobli savolda ham "hammasi yoki hech nima"). Ochiq: None."""
    if question.type not in TEST_TYPES:
        return None
    return float(question.points) if sorted(answer or []) == sorted(question.correct) else 0.0


def save_answers(submission, parsed: list) -> None:
    answered = {q.id for q, _a in parsed}
    rows = []
    for question, answer in parsed:
        score = auto_score(question, answer)
        rows.append(SubmissionAnswer(submission=submission, question=question, answer=answer, auto_score=score, final_score=score))
    for question in submission.assignment.questions.exclude(pk__in=answered):  # javobsiz savol — 0 ball
        score = 0.0 if question.type in TEST_TYPES else None
        rows.append(SubmissionAnswer(
            submission=submission, question=question, answer=[] if question.type in TEST_TYPES else '', auto_score=score, final_score=score,
        ))
    SubmissionAnswer.objects.bulk_create(rows)


def has_open_questions(assignment) -> bool:
    return assignment.questions.filter(type__in=OPEN_TYPES).exists()


def percent(submission) -> float | None:
    """Hozirgi `final_score`lar bo'yicha umumiy foiz (ballanmagan ochiq javob hozircha 0)."""
    total = total_points(submission.assignment)
    if not total:
        return None
    earned = sum((a.final_score or 0.0) for a in submission.answers.all())
    return round(earned * 100 / total, 1)


def open_answers_text(submission) -> str:
    """AI'ga beriladigan o'quvchi ishi: ochiq savollar va javoblari (testlar AI'ga yuborilmaydi)."""
    lines = []
    for number, answer in enumerate(
        [a for a in submission.answers.select_related('question') if a.question.type in OPEN_TYPES], start=1,
    ):
        lines.append(f'Question {number} ({answer.question.points} points): {answer.question.text}\nStudent answer: {answer.answer or "[no answer]"}')
    return '\n\n'.join(lines)[:30000]


def merge_ai(submission, result: dict) -> None:
    """AI natijasidagi har ochiq savol bali (%) -> `ai_score` (= `final_score` taklifi) va umumiy foizni test balli bilan birlashtirish."""
    open_answers = [a for a in submission.answers.select_related('question').order_by('question__order') if a.question.type in OPEN_TYPES]
    if not open_answers:
        return
    by_number = {}
    for position, item in enumerate((result or {}).get('questions') or [], start=1):
        try:
            by_number[int(item.get('question_number') or position)] = float(item.get('score'))
        except (TypeError, ValueError, AttributeError):
            continue
    for number, answer in enumerate(open_answers, start=1):
        value = by_number.get(number)
        if value is None or not math.isfinite(value) or not answer.answer:
            score = 0.0 if not answer.answer else None
        else:
            score = round(answer.question.points * max(0.0, min(100.0, value)) / 100, 2)
        answer.ai_score = score
        answer.final_score = score
        answer.save(update_fields=['ai_score', 'final_score', 'updated_at'])
    value = percent(submission)
    if value is not None:
        submission.overall_score = value
        submission.ai_overall_score = value


def apply_teacher_scores(submission, scores) -> float | None:
    """O'qituvchi har ochiq javobga ball qo'yadi: `{savol_id: ball}` (0..savol balli). Qaytaradi: yangi umumiy foiz."""
    if not isinstance(scores, dict):
        raise ValidationError({'answer_scores': _("{savol_id: ball} ko'rinishida bo'lishi kerak.")})
    answers = {str(a.question_id): a for a in submission.answers.select_related('question')}
    for question_id, raw in scores.items():
        answer = answers.get(str(question_id))
        if answer is None:
            raise ValidationError({'answer_scores': _("Noma'lum savol.")})
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ValidationError({'answer_scores': _("Ball raqam bo'lishi kerak.")}) from None
        if not math.isfinite(value) or not 0 <= value <= answer.question.points:
            raise ValidationError({'answer_scores': _("Ball 0 dan savol balligacha bo'lishi kerak.")})
        answer.final_score = round(value, 2)
        answer.save(update_fields=['final_score', 'updated_at'])
    return percent(submission)


def answers_payload(submission, is_teacher: bool) -> list:
    rows = []
    for a in submission.answers.select_related('question').order_by('question__order'):
        q = a.question
        row = {
            'question_id': str(q.id), 'order': q.order, 'type': q.type, 'text': q.text, 'options': q.options, 'points': q.points,
            'answer': a.answer, 'score': a.final_score,
        }
        if q.type in TEST_TYPES:
            row['correct'] = q.correct
            row['is_correct'] = a.auto_score is not None and a.auto_score == q.points
        if is_teacher:
            row['ai_score'] = a.ai_score
            row['auto_score'] = a.auto_score
        rows.append(row)
    return rows
