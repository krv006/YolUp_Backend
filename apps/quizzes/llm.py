"""OpenAI-mos (Chat Completions) til modeliga oddiy HTTP chaqiruv.

Faqat JSON rejimida ishlaydi: `chat_json` doim `dict` qaytaradi yoki `LLMError`. Tashqi SDK kerak emas
(`requests` bor). Xatolar ikkiga bo'linadi:
  - doimiy (`permanent=True`): kalit noto'g'ri, hisobda mablag'/limit yo'q, so'rov rad etilgan — qayta urinish foydasiz;
  - vaqtincha: tarmoq, 5xx, band xizmat (429 "rate limit"), noto'g'ri JSON — keyinroq qayta uriniladi.
"""
import json
import logging
import re
import time

import requests
from django.conf import settings

from .tc_client import TestCreatorError

logger = logging.getLogger('apps')

_JSON_RETRIES = 1  # noto'g'ri JSON bo'lsa shuncha marta tuzatish so'raymiz


class LLMError(TestCreatorError):
    pass


def enabled() -> bool:
    return bool(getattr(settings, 'OPENAI_API_KEY', ''))


def _strip_fences(text: str) -> str:
    cleaned = (text or '').strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    return re.sub(r'\s*```$', '', cleaned).strip()


def _error_message(response: requests.Response) -> tuple:
    try:
        body = response.json().get('error') or {}
    except ValueError:
        return '', ''
    return str(body.get('code') or body.get('type') or ''), str(body.get('message') or '')[:300]


def _post(messages: list, max_tokens: int) -> dict:
    url = settings.OPENAI_BASE_URL.rstrip('/') + '/chat/completions'
    payload = {
        'model': settings.OPENAI_MODEL, 'messages': messages,
        'response_format': {'type': 'json_object'}, 'max_completion_tokens': max_tokens,
    }
    try:
        response = requests.post(
            url, json=payload, timeout=settings.OPENAI_TIMEOUT,
            headers={'Authorization': f'Bearer {settings.OPENAI_API_KEY}'},
        )
    except requests.RequestException as exc:
        raise LLMError(f"AI xizmatiga ulanib bo'lmadi: {exc}") from exc
    status = response.status_code
    if status == 200:
        return response.json()
    code, message = _error_message(response)
    if status in (401, 403):
        raise LLMError("AI kaliti noto'g'ri yoki ruxsat yo'q (OPENAI_API_KEY).", permanent=True)
    if status == 429 and code in ('insufficient_quota', 'billing_not_active'):
        raise LLMError("AI hisobida mablag' yoki limit tugagan (OpenAI billing/quota).", permanent=True)
    if status == 404:
        raise LLMError(f"AI modeli topilmadi yoki hisobingizda ochiq emas: {settings.OPENAI_MODEL}.", permanent=True)
    if status == 400:
        raise LLMError(f"AI so'rovni rad etdi: {message}", permanent=True)
    raise LLMError(f'AI xizmati vaqtincha javob bermadi ({status}) {message}'.strip())


def chat_json(system: str, user: str, *, max_tokens: int = 0) -> dict:
    """Tizim va foydalanuvchi xabari bo'yicha JSON obyekt qaytaradi."""
    max_tokens = max_tokens or settings.OPENAI_MAX_OUTPUT_TOKENS
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
    last = ''
    for attempt in range(_JSON_RETRIES + 1):
        started = time.monotonic()
        body = _post(messages, max_tokens)
        try:
            choice = body['choices'][0]
            text = choice['message']['content']
            data = json.loads(_strip_fences(text))
            if not isinstance(data, dict):
                raise ValueError('JSON object expected')
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            last = str(exc)
            if (body.get('choices') or [{}])[0].get('finish_reason') == 'length':
                last = 'javob uzunligi chegaradan oshib, qirqilib qoldi'
            messages = messages + [{
                'role': 'user',
                'content': 'Your previous response was not a valid, complete JSON object of the required shape. '
                           'Return ONLY the corrected JSON object.',
            }]
            continue
        logger.info('AI chaqiruvi: %s, %s ms, token %s', settings.OPENAI_MODEL,
                    int((time.monotonic() - started) * 1000), (body.get('usage') or {}).get('total_tokens'))
        return data
    raise LLMError(f"AI yaroqli javob bermadi: {last}")
