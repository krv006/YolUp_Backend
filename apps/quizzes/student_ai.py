"""O'quvchi uchun AI: xatoni tushuntirish va mavzu bo'yicha mashq savollari (saqlanmaydi — o'quvchiga to'g'ridan-to'g'ri qaytadi).

Har o'quvchiga kuniga `STUDENT_AI_DAILY_LIMIT` (standart 20) ta so'rov (xarajat nazorati uchun). AI kaliti sozlanmagan bo'lsa — aniq xato.
"""
import logging

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import Throttled, ValidationError

from . import llm

logger = logging.getLogger('apps')

LANGUAGES = {'uz': 'Uzbek (Latin script)', 'uz_cyrl': 'Uzbek (Cyrillic script)', 'ru': 'Russian', 'en': 'English'}
MAX_TEXT = 3000
MAX_PRACTICE = 10


def _limit() -> int:
    return int(getattr(settings, 'STUDENT_AI_DAILY_LIMIT', 20))


def _spend(user) -> dict:
    """Kunlik limitdan bittasini sarflaydi (oshsa 429). Qaytaradi: `{used, limit}`."""
    key = f'student-ai:{user.id}:{timezone.localdate()}'
    cache.add(key, 0, 26 * 3600)
    try:
        used = cache.incr(key)
    except ValueError:
        used = 1
        cache.set(key, 1, 26 * 3600)
    if used > _limit():
        raise Throttled(wait=3600, detail=str(_("Bugungi AI so'rovlar limiti tugadi. Ertaga qayta urinib ko'ring.")))
    return {'used': used, 'limit': _limit()}


def _refund(user) -> None:
    key = f'student-ai:{user.id}:{timezone.localdate()}'
    try:
        cache.decr(key)
    except ValueError:
        pass


def _language(user, language: str) -> str:
    code = language or getattr(user, 'preferred_language', '') or 'uz'
    return LANGUAGES.get(code, LANGUAGES['uz'])


def _call(user, system: str, prompt: str) -> dict:
    if not llm.enabled():
        raise ValidationError({'detail': _("AI hozir o'chirilgan (kalit sozlanmagan).")})
    usage = _spend(user)
    try:
        return {**llm.chat_json(system, prompt), '_usage': usage}
    except llm.LLMError as exc:
        _refund(user)  # xizmat ishlamadi — limit kuymasin
        logger.warning('student ai xato: %s', exc)
        raise ValidationError({'detail': _("AI hozir javob bermayapti. Birozdan keyin urinib ko'ring.")}) from exc


def explain(user, *, question: str, wrong_answer: str = '', correct_answer: str = '', language: str = '') -> dict:
    question = (question or '').strip()
    if not question:
        raise ValidationError({'question': _('Savolni yozing.')})
    prompt = f'Question: {question[:MAX_TEXT]}\nStudent answer: {(wrong_answer or "-")[:500]}\nCorrect answer: {(correct_answer or "-")[:500]}'
    system = (
        'You are a patient school tutor. Explain briefly and clearly why the student answer is wrong (if given) and how to reach '
        f'the correct answer, in simple words. Write in {_language(user, language)}. '
        'Return ONLY a JSON object: {"explanation": "<text, max 900 characters>", "tip": "<one short tip to remember>"}.'
    )
    data = _call(user, system, prompt)
    return {'explanation': str(data.get('explanation') or '')[:1500], 'tip': str(data.get('tip') or '')[:300], **data['_usage']}


def practice(user, *, topic: str, count: int = 5, material: str = '', language: str = '') -> dict:
    topic = (topic or '').strip()
    if not topic and not (material or '').strip():
        raise ValidationError({'topic': _('Mavzuni yozing.')})
    try:
        count = max(1, min(int(count or 5), MAX_PRACTICE))
    except (TypeError, ValueError):
        raise ValidationError({'count': _("Son bo'lishi kerak.")}) from None
    system = (
        f'You write practice questions for a school student. Write in {_language(user, language)}. '
        f'Create exactly {count} multiple-choice questions (4 options each, exactly one correct) that reinforce the topic. '
        'Return ONLY a JSON object: {"questions": [{"text": "...", "options": ["...", "...", "...", "..."], '
        '"correct_index": 0, "explanation": "one sentence"}]}.'
    )
    prompt = f'Topic: {topic[:300]}\n' + (f'Material / mistakes to reinforce:\n{material[:MAX_TEXT]}' if material else '')
    data = _call(user, system, prompt)
    questions = []
    for raw in data.get('questions') or []:
        options = [str(o)[:300] for o in (raw.get('options') or [])][:6]
        try:
            index = int(raw.get('correct_index'))
        except (TypeError, ValueError):
            continue
        if len(options) < 2 or not 0 <= index < len(options) or not str(raw.get('text') or '').strip():
            continue
        questions.append({
            'text': str(raw['text'])[:600], 'options': options, 'correct_index': index,
            'explanation': str(raw.get('explanation') or '')[:400],
        })
    if not questions:
        _refund(user)
        raise ValidationError({'detail': _("AI savollar yarata olmadi. Qayta urinib ko'ring.")})
    return {'topic': topic, 'questions': questions[:count], **data['_usage']}
