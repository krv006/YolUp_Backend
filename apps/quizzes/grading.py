"""Savol turlari bo'yicha avtomatik baholash va o'qiladigan javob ko'rinishi.

`grade()` — bitta savol uchun (olingan ball, xom javob, given_display) qaytaradi.
`correct_display()` — to'g'ri javobning o'qiladigan matni (natija sahifasi uchun).
Qisman ball faqat matching va fill_blank'da; qolgan turlarda to'liq yoki 0.
"""
import math
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from .models import Question

T = Question.Type
ARROW = ' → '


class Graded(NamedTuple):
    earned: float
    answer: object
    given_display: str | None


def round_points(value) -> float:
    return float(Decimal(str(value)).quantize(Decimal('0.01'), ROUND_HALF_UP))


def _partial(points: int, correct: int, total: int) -> float:
    if not total:
        return 0.0
    return round_points(Decimal(points) * correct / total)


def normalize_text(value, case_sensitive: bool = False) -> str:
    text = ' '.join(str(value).split())
    return text if case_sensitive else text.casefold()


def parse_number(value) -> float | None:
    cleaned = str(value).replace(' ', '').replace(',', '.')
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _options(question: Question) -> list:
    return list(question.options.all())


def _bad_answer() -> ValidationError:
    return ValidationError({'answers': _("Javobdagi element bu savolga tegishli emas.")})


def grade(question: Question, answer: dict) -> Graded:
    handler = _HANDLERS[question.type]
    return handler(question, answer)


def _unanswered() -> Graded:
    return Graded(0.0, None, None)


def _grade_single(question, answer) -> Graded:
    selected = answer.get('selected_option')
    if selected is None:
        return _unanswered()
    if selected.question_id != question.id:
        raise ValidationError({'answers': _('Tanlangan variant bu savolga tegishli emas.')})
    earned = float(question.points) if selected.is_correct else 0.0
    return Graded(earned, {'selected_option': str(selected.id)}, selected.text)


def _grade_multiple(question, answer) -> Graded:
    selected = answer.get('selected_options') or []
    if not selected:
        return _unanswered()
    options = _options(question)
    by_id = {o.id: o for o in options}
    if any(o.id not in by_id for o in selected):
        raise ValidationError({'answers': _('Tanlangan variant bu savolga tegishli emas.')})
    chosen = {o.id for o in selected}
    correct = {o.id for o in options if o.is_correct}
    earned = float(question.points) if chosen == correct else 0.0
    given = ', '.join(o.text for o in options if o.id in chosen)
    return Graded(earned, {'selected_options': [str(o.id) for o in selected]}, given)


def _grade_true_false(question, answer) -> Graded:
    value = answer.get('value_bool')
    if value is None:
        return _unanswered()
    earned = float(question.points) if value == question.answer_key.get('correct_bool') else 0.0
    return Graded(earned, {'value_bool': value}, _bool_label(value))


def _bool_label(value: bool) -> str:
    return _("To'g'ri") if value else _("Noto'g'ri")


def _grade_numeric(question, answer) -> Graded:
    raw = answer.get('value_text')
    if raw is None or not str(raw).strip():
        return _unanswered()
    key = question.answer_key
    tolerance = float(key.get('tolerance') or 0)
    given = parse_number(raw)
    earned = 0.0
    if given is not None:
        for accepted in key.get('accepted_answers', []):
            target = parse_number(accepted)
            if target is not None and abs(given - target) <= tolerance:
                earned = float(question.points)
                break
    return Graded(earned, {'value_text': str(raw)}, str(raw).strip())


def _grade_text(question, answer) -> Graded:
    raw = answer.get('value_text')
    if raw is None or not str(raw).strip():
        return _unanswered()
    key = question.answer_key
    case_sensitive = bool(key.get('case_sensitive'))
    given = normalize_text(raw, case_sensitive)
    accepted = {normalize_text(a, case_sensitive) for a in key.get('accepted_answers', [])}
    earned = float(question.points) if given in accepted else 0.0
    return Graded(earned, {'value_text': str(raw)}, ' '.join(str(raw).split()))


def _grade_matching(question, answer) -> Graded:
    given_pairs = answer.get('pairs') or []
    if not given_pairs:
        return _unanswered()
    pairs = question.answer_key.get('pairs', [])
    right_of = {p['left_id']: p['right_id'] for p in pairs}
    left_text = {p['left_id']: p['left'] for p in pairs}
    right_text = {p['right_id']: p['right'] for p in pairs}
    chosen: dict = {}
    for item in given_pairs:
        left, right = str(item['left']), str(item['right'])
        if left not in right_of or right not in right_text:
            raise _bad_answer()
        chosen[left] = right
    correct = sum(1 for left, right in chosen.items() if right_of[left] == right)
    given = '; '.join(
        f'{left_text[p["left_id"]]}{ARROW}{right_text[chosen[p["left_id"]]]}'
        for p in pairs if p['left_id'] in chosen
    )
    return Graded(
        _partial(question.points, correct, len(pairs)),
        {'pairs': [{'left': left, 'right': right} for left, right in chosen.items()]},
        given,
    )


def _grade_ordering(question, answer) -> Graded:
    order = [str(x) for x in (answer.get('order') or [])]
    if not order:
        return _unanswered()
    options = _options(question)
    text_of = {str(o.id): o.text for o in options}
    if any(x not in text_of for x in order):
        raise _bad_answer()
    correct_order = [str(o.id) for o in options]
    earned = float(question.points) if order == correct_order else 0.0
    return Graded(earned, {'order': order}, ARROW.join(text_of[x] for x in order))


def _grade_fill_blank(question, answer) -> Graded:
    given = [str(x) for x in (answer.get('blanks') or [])]
    if not any(x.strip() for x in given):
        return _unanswered()
    blanks = question.answer_key.get('blanks', [])
    correct = 0
    for index, blank in enumerate(blanks):
        if index >= len(given):
            break
        accepted = {normalize_text(a) for a in blank['answers']}
        if normalize_text(given[index]) in accepted:
            correct += 1
    display = '; '.join(' '.join(x.split()) for x in given)
    return Graded(_partial(question.points, correct, len(blanks)), {'blanks': given}, display)


_HANDLERS = {
    T.SINGLE: _grade_single,
    T.MULTIPLE: _grade_multiple,
    T.TRUE_FALSE: _grade_true_false,
    T.NUMERIC: _grade_numeric,
    T.TEXT: _grade_text,
    T.MATCHING: _grade_matching,
    T.ORDERING: _grade_ordering,
    T.FILL_BLANK: _grade_fill_blank,
}


def correct_display(question: Question) -> str | None:
    key = question.answer_key or {}
    qtype = question.type
    if qtype in (T.SINGLE, T.MULTIPLE):
        return ', '.join(o.text for o in question.options.all() if o.is_correct) or None
    if qtype == T.TRUE_FALSE:
        return _bool_label(bool(key.get('correct_bool')))
    if qtype == T.NUMERIC:
        text = ' | '.join(key.get('accepted_answers', []))
        tolerance = key.get('tolerance') or 0
        return f'{text} (±{tolerance:g})' if tolerance else text
    if qtype == T.TEXT:
        return ' | '.join(key.get('accepted_answers', []))
    if qtype == T.MATCHING:
        return '; '.join(f'{p["left"]}{ARROW}{p["right"]}' for p in key.get('pairs', []))
    if qtype == T.ORDERING:
        return ARROW.join(o.text for o in question.options.all())
    if qtype == T.FILL_BLANK:
        return '; '.join(' | '.join(b['answers']) for b in key.get('blanks', []))
    return None
