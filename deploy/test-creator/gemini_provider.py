"""Test-creator uchun Gemini provayderi.

Bu fayl Test-creator repo'siga (`backend/app/services/providers/gemini_provider.py`) `apply_patch.py`
orqali nusxalanadi — `AnthropicProvider` bilan bir xil shartnoma: `extract_knowledge`,
`generate_questions`, `embed`. Embedding (384 o'lchovli) mock provayderdan olinadi — xuddi
Anthropic provayderidagidek, shuning uchun DB vektor ustuni o'zgarmaydi.

Sozlama (env): `GEMINI_API_KEY` (majburiy), `GEMINI_MODEL` (ixtiyoriy, standart gemini-3.5-flash).
Faollashtirish: `AI_DEFAULT_PROVIDER=gemini`.
"""
import json
import os
import re
import time
from typing import Any

from app.services.providers.base import (
    AIProvider,
    EmbeddingResult,
    GeneratedQuestion,
    KnowledgeExtractionResult,
    QuestionGenerationResult,
)
from app.services.providers.mock_provider import MockProvider

DEFAULT_MODEL = 'gemini-3.5-flash'
MAX_RETRIES = 2
REQUEST_TIMEOUT_MS = 180_000

_KNOWLEDGE_SYSTEM = (
    'You extract a hierarchical knowledge map (topic -> subtopic -> concept -> learning_objective) '
    'from teaching material. Use ONLY content present in the provided chunks - never invent facts. '
    "Reference each node's originating chunk via source_chunk_index.\n\n"
    'Return ONLY valid JSON of this exact shape (no markdown, nothing else):\n'
    '{"tree": [{"level": "topic|subtopic|concept|learning_objective", "name": "...", '
    '"description": "...", "source_chunk_index": 0, "children": [ ...same shape... ]}]}'
)

_QUESTIONS_SYSTEM = (
    'You are an expert exam-item writer. Generate exam questions strictly grounded in the provided '
    "source material - never introduce facts absent from it. Follow the given standard's format rules. "
    'Each question must have exactly ONE unambiguous correct answer and plausible, non-trivial '
    "distractors. Do not repeat or closely paraphrase anything in 'avoid_similar_to'. Write all "
    "question text, options and explanations in the requested 'language' (uz = Uzbek Latin, en, ru).\n\n"
    'Return ONLY valid JSON of this exact shape (no markdown, nothing else):\n'
    '{"questions": [{"question_text": "...", "question_type": "multiple_choice", '
    '"difficulty": "easy|medium|hard", '
    '"options": [{"label": "A", "text": "...", "is_correct": true}, {"label": "B", "text": "...", "is_correct": false}], '
    '"correct_answer": {"value": "<exact text of the correct option, or the numeric answer>"}, '
    '"explanation": "...", "skill": "...", "cognitive_level": "remember|understand|apply|analyze", '
    '"source_chunk_index": 0}]}\n'
    'Rules: multiple_choice questions have 4 options labelled A-D with exactly one is_correct=true. '
    'For arithmetic/algebra questions also put the computable expression in correct_answer.expression '
    '(for example "12*7") so it can be verified. Return exactly the requested number of questions.'
)


def _strip_fences(text: str) -> str:
    cleaned = (text or '').strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    return re.sub(r'\s*```$', '', cleaned).strip()


class GeminiProvider(AIProvider):
    name = 'gemini'

    def __init__(self):
        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            raise RuntimeError(
                'GEMINI_API_KEY is not set. Set AI_DEFAULT_PROVIDER=mock to run without a key, '
                'or provide GEMINI_API_KEY in .env to use Gemini generation.'
            )
        from google import genai
        from google.genai import types

        self._types = types
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS))
        self.model = os.environ.get('GEMINI_MODEL', DEFAULT_MODEL)
        self._embedder = MockProvider()

    # ------------------------------------------------------------------ core call
    def _call_json(self, system: str, user: str) -> tuple:
        """(data, input_tokens, output_tokens, latency_ms). Noto'g'ri JSON bo'lsa qayta so'raydi."""
        config = self._types.GenerateContentConfig(
            system_instruction=system, response_mime_type='application/json',
            temperature=0.3, top_p=0.9, max_output_tokens=8192,
        )
        contents = [user]
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            started = time.monotonic()
            try:
                response = self.client.models.generate_content(model=self.model, contents=contents, config=config)
                data = json.loads(_strip_fences(response.text))
                if not isinstance(data, dict):
                    raise ValueError('JSON object expected')
            except (ValueError, TypeError) as exc:  # json.JSONDecodeError ham ValueError
                last_error = exc
                contents = contents + [
                    'Your previous response was not a valid JSON object of the required shape. '
                    'Return ONLY the corrected JSON object.'
                ]
                continue
            except Exception as exc:  # tarmoq / kvota
                last_error = exc
                time.sleep(2 * (attempt + 1))
                continue
            usage = getattr(response, 'usage_metadata', None)
            return (
                data,
                getattr(usage, 'prompt_token_count', 0) or 0,
                getattr(usage, 'candidates_token_count', 0) or 0,
                int((time.monotonic() - started) * 1000),
            )
        raise RuntimeError(f'Gemini {MAX_RETRIES + 1} urinishdan keyin ham yaroqli javob bermadi: {last_error}')

    # ------------------------------------------------------------------ AIProvider
    def extract_knowledge(self, subject_name: str, chunks: list) -> KnowledgeExtractionResult:
        user = f'Subject: {subject_name}\n\nChunks:\n' + '\n\n'.join(
            f"[chunk {c['index']}] ({c.get('heading_path', '')})\n{c['text']}" for c in chunks
        )
        data, tokens_in, tokens_out, latency = self._call_json(_KNOWLEDGE_SYSTEM, user)
        tree = data.get('tree')
        tree = [node for node in tree if isinstance(node, dict) and node.get('name')] if isinstance(tree, list) else []
        return KnowledgeExtractionResult(
            tree=tree, input_tokens=tokens_in, output_tokens=tokens_out, latency_ms=latency,
        )

    def generate_questions(
        self, *, subject_name: str, topic_name: str, chunks: list, standard_config: dict[str, Any],
        difficulty: str, question_type: str, count: int, avoid_similar_to: list, language: str = 'uz',
    ) -> QuestionGenerationResult:
        user = json.dumps({
            'subject': subject_name, 'topic': topic_name, 'difficulty': difficulty,
            'question_type': question_type, 'language': language, 'count': count,
            'standard_config': standard_config, 'avoid_similar_to': avoid_similar_to,
            'source_chunks': [
                {'index': c['index'], 'heading_path': c.get('heading_path', ''), 'text': c['text']} for c in chunks
            ],
        }, ensure_ascii=False)
        data, tokens_in, tokens_out, latency = self._call_json(_QUESTIONS_SYSTEM, user)

        questions = []
        for raw in (data.get('questions') if isinstance(data.get('questions'), list) else []):
            if not isinstance(raw, dict) or not str(raw.get('question_text') or '').strip():
                continue
            options = [o for o in (raw.get('options') or []) if isinstance(o, dict) and o.get('text')]
            qtype = raw.get('question_type') or question_type
            if qtype in ('multiple_choice', 'auto') and sum(1 for o in options if o.get('is_correct')) != 1:
                continue  # aniq bitta to'g'ri javobi bo'lmagan test savoli — tashlab yuboriladi
            correct = raw.get('correct_answer')
            questions.append(GeneratedQuestion(
                question_text=str(raw['question_text']).strip(),
                question_type='multiple_choice' if qtype == 'auto' else qtype,
                difficulty=raw.get('difficulty') or difficulty,
                options=options,
                correct_answer=correct if isinstance(correct, dict) else {'value': correct},
                explanation=str(raw.get('explanation') or ''),
                skill=raw.get('skill'),
                cognitive_level=raw.get('cognitive_level'),
                source_chunk_index=raw.get('source_chunk_index'),
            ))
        return QuestionGenerationResult(
            questions=questions[:count] if count else questions,
            input_tokens=tokens_in, output_tokens=tokens_out, latency_ms=latency,
        )

    def embed(self, texts: list) -> EmbeddingResult:
        return self._embedder.embed(texts)
