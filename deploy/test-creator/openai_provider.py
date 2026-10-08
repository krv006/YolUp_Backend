"""Test-creator uchun OpenAI (GPT) provayderi.

Bu fayl Test-creator repo'siga (`backend/app/services/providers/openai_provider.py`) `apply_patch.py`
orqali `gemini_provider.py` bilan birga nusxalanadi. Promptlar, javobni tahlil qilish va embedding
(`extract_knowledge`, `generate_questions`, `embed`) Gemini provayderi bilan BIR XIL (undan meros olinadi);
faqat tashqi chaqiruv (`_call_json`) OpenAI Chat Completions orqali bajariladi.

Sozlama (env): `OPENAI_API_KEY` (majburiy), `OPENAI_MODEL` (standart gpt-4o-mini), ixtiyoriy
`OPENAI_BASE_URL` (SDK o'zi o'qiydi) va `OPENAI_MAX_OUTPUT_TOKENS` (standart 8192).
Faollashtirish: `AI_DEFAULT_PROVIDER=openai` (compose'da `TC_AI_PROVIDER=openai`).
"""
import json
import os
import time

from app.services.providers.gemini_provider import GeminiProvider, _strip_fences
from app.services.providers.mock_provider import MockProvider

DEFAULT_MODEL = 'gpt-4o-mini'
MAX_RETRIES = 2
REQUEST_TIMEOUT_S = 180


class OpenAIProvider(GeminiProvider):
    name = 'openai'

    def __init__(self):  # noqa: super().__init__ ataylab chaqirilmaydi: u Gemini mijozini yaratadi
        api_key = os.environ.get('OPENAI_API_KEY', '')
        if not api_key:
            raise RuntimeError(
                'OPENAI_API_KEY is not set. Set AI_DEFAULT_PROVIDER=mock to run without a key, '
                'or provide OPENAI_API_KEY in .env to use OpenAI generation.'
            )
        from openai import OpenAI

        # SDK o'zi 429/5xx'ni 1 marta qayta urinadi; bizning sikl esa noto'g'ri JSON uchun
        self.client = OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_S, max_retries=1)
        self.model = os.environ.get('OPENAI_MODEL', DEFAULT_MODEL)
        self.max_output_tokens = int(os.environ.get('OPENAI_MAX_OUTPUT_TOKENS', '8192'))
        self._embedder = MockProvider()

    def _call_json(self, system: str, user: str) -> tuple:
        """(data, input_tokens, output_tokens, latency_ms). Noto'g'ri JSON bo'lsa qayta so'raydi."""
        messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            started = time.monotonic()
            try:
                response = self.client.chat.completions.create(
                    model=self.model, messages=messages, response_format={'type': 'json_object'},
                    max_completion_tokens=self.max_output_tokens,
                )
                data = json.loads(_strip_fences(response.choices[0].message.content))
                if not isinstance(data, dict):
                    raise ValueError('JSON object expected')
            except (ValueError, TypeError, AttributeError, IndexError) as exc:  # json.JSONDecodeError ham ValueError
                last_error = exc
                messages = messages + [{
                    'role': 'user',
                    'content': 'Your previous response was not a valid JSON object of the required shape. '
                               'Return ONLY the corrected JSON object.',
                }]
                continue
            except Exception as exc:  # tarmoq / kvota
                last_error = exc
                time.sleep(2 * (attempt + 1))
                continue
            usage = getattr(response, 'usage', None)
            return (
                data,
                getattr(usage, 'prompt_tokens', 0) or 0,
                getattr(usage, 'completion_tokens', 0) or 0,
                int((time.monotonic() - started) * 1000),
            )
        raise RuntimeError(f'OpenAI {MAX_RETRIES + 1} urinishdan keyin ham yaroqli javob bermadi: {last_error}')
