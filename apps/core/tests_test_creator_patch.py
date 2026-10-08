"""deploy/test-creator: Gemini provayderi va Test-creator'ga qo'llanadigan moslashtirish (patch).

Test-creator repo'si bizniki emas, shuning uchun uning kerakli fayllari shu yerda qisqartirilgan
nusxalarda (haqiqiy fayllardan olingan joylar bilan) yaratiladi va patch shularga qo'llanadi."""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import time
import types
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

DEPLOY = Path(__file__).resolve().parents[2] / 'deploy' / 'test-creator'

ROUTER_SRC = '''"""AI Model Router."""
from app.core.config import settings
from app.services.providers.base import AIProvider
from app.services.providers.mock_provider import MockProvider

_PROVIDER_REGISTRY: dict[str, type] = {"mock": MockProvider}

try:
    from app.services.providers.anthropic_provider import AnthropicProvider

    _PROVIDER_REGISTRY["anthropic"] = AnthropicProvider
except ImportError:  # pragma: no cover
    pass

_provider_instances: dict[str, AIProvider] = {}


def _get_or_create_model_row(db, provider):
    model_name = {
        "mock": "mock-deterministic-v1",
        "anthropic": settings.ANTHROPIC_MODEL,
    }.get(provider, provider)
    return model_name
'''

AUTH_SRC = '''from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload, db=Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    return "created"


@router.post("/login")
def login(payload, db=Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    return user
'''


GEN_SRC = '''"""Question Generation Algorithm."""
from sqlalchemy.orm import Session

BATCH_BUFFER_MULTIPLIER = 1.4


def generate_and_validate(
    db: Session,
    router,
    *,
    subject,
    knowledge_node_id,
    standard_version_id,
    difficulty: str,
    organization_id,
    teacher_id,
    language: str = "uz",
) -> GenerationOutcome:
    chunks = []
    return language
'''


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_tree(root: Path) -> Path:
    for rel, text in (
        ('backend/app/main.py', ''),
        ('backend/app/services/ai_router.py', ROUTER_SRC),
        ('backend/app/api/v1/auth.py', AUTH_SRC),
        ('backend/requirements.txt', 'fastapi>=0.110\nanthropic>=0.40\n'),
        ('backend/app/services/question_generation_service.py', GEN_SRC),
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    (root / 'backend/app/services/providers').mkdir(parents=True, exist_ok=True)
    return root


class ApplyPatchTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = fake_tree(Path(self.tmp.name))
        self.patcher = load(DEPLOY / 'apply_patch.py', 'tc_apply_patch')
        real_main = self.patcher.main

        def quiet_main(root):
            with contextlib.redirect_stdout(io.StringIO()):  # patch chop etadigan xabarlar test chiqishini to'ldirmasin
                real_main(root)

        self.patcher.main = quiet_main

    def read(self, rel):
        return (self.root / rel).read_text(encoding='utf-8')

    def test_everything_is_applied(self):
        self.patcher.main(str(self.root))
        self.assertTrue((self.root / 'backend/app/services/providers/gemini_provider.py').exists())
        router = self.read('backend/app/services/ai_router.py')
        self.assertIn('_PROVIDER_REGISTRY["gemini"] = GeminiProvider', router)
        self.assertIn('"gemini": __import__("os").environ.get("GEMINI_MODEL", "gemini-3.5-flash"),', router)
        self.assertIn('google-genai>=1.0', self.read('backend/requirements.txt'))
        self.assertIn('openai>=1.40', self.read('backend/requirements.txt'))
        self.assertTrue((self.root / 'backend/app/services/providers/openai_provider.py').exists())
        self.assertIn('_PROVIDER_REGISTRY["openai"] = OpenAIProvider', router)
        self.assertIn('"openai": __import__("os").environ.get("OPENAI_MODEL", "gpt-4o-mini"),', router)
        self.assertEqual(router.count('_PROVIDER_REGISTRY["gemini"]'), 1)  # Gemini ikki marta qo'shilmaydi
        auth = self.read('backend/app/api/v1/auth.py')
        self.assertIn('REGISTRATION_ALLOWED_EMAILS', auth)
        # tekshiruv register ichida, login'ga tegilmagan
        register_part, login_part = auth.split('def login')
        self.assertIn('REGISTRATION_ALLOWED_EMAILS', register_part)
        self.assertNotIn('REGISTRATION_ALLOWED_EMAILS', login_part)
        for rel in ('backend/app/services/ai_router.py', 'backend/app/api/v1/auth.py',
                    'backend/app/services/question_generation_service.py'):
            compile(self.read(rel), rel, 'exec')  # sintaksis to'g'ri

    def test_question_language_follows_the_standard(self):
        self.patcher.main(str(self.root))
        text = self.read('backend/app/services/question_generation_service.py')
        self.assertIn('language: str | None = None,', text)
        self.assertIn('language = _language_for(db, standard_version_id)', text)
        # Haqiqiy funksiyani ishga tushirib tekshiramiz (Session/GenerationOutcome nomlari uchun stub)
        namespace = {'GenerationOutcome': object, 'Session': object}
        exec(compile(text.replace('from sqlalchemy.orm import Session', ''), 'gen', 'exec'), namespace)

        def db_for(code):
            version = SimpleNamespace(standard_id='std')
            standard = SimpleNamespace(code=code)
            fake = MagicMock()
            fake.get.side_effect = lambda model, key: version if model.__name__ == 'StandardVersion' else standard
            return fake

        models = types.ModuleType('app.models.standard')
        models.Standard = type('Standard', (), {})
        models.StandardVersion = type('StandardVersion', (), {})
        modules = {'app': types.ModuleType('app'), 'app.models': types.ModuleType('app.models'),
                   'app.models.standard': models}
        with patch.dict(sys.modules, modules):
            generate = namespace['generate_and_validate']
            kwargs = dict(router=None, subject=None, knowledge_node_id=None, standard_version_id='v',
                          difficulty='easy', organization_id=None, teacher_id=None)
            self.assertEqual(generate(db_for('IELTS_ACADEMIC'), **kwargs), 'en')
            self.assertEqual(generate(db_for('DIGITAL_SAT'), **kwargs), 'en')
            self.assertEqual(generate(db_for('UZBMB'), **kwargs), 'uz')
            self.assertEqual(generate(db_for('IELTS_ACADEMIC'), language='ru', **kwargs), 'ru')  # aniq til ustun

    def test_is_idempotent(self):
        self.patcher.main(str(self.root))
        before = {rel: self.read(rel) for rel in (
            'backend/app/services/ai_router.py', 'backend/app/api/v1/auth.py', 'backend/requirements.txt',
            'backend/app/services/question_generation_service.py')}
        self.patcher.main(str(self.root))
        for rel, text in before.items():
            self.assertEqual(self.read(rel), text, rel)

    def test_unknown_repo_layout_fails_loudly(self):
        (self.root / 'backend/app/api/v1/auth.py').write_text('print("boshqa fayl")\n', encoding='utf-8')
        with self.assertRaises(SystemExit):
            self.patcher.main(str(self.root))
        (self.root / 'backend/app/main.py').unlink()
        with self.assertRaises(SystemExit):
            self.patcher.main(str(self.root))

    def test_patched_registration_only_lets_allowed_emails_through(self):
        self.patcher.main(str(self.root))
        namespace = {'get_db': None, 'User': SimpleNamespace(email=1)}
        fastapi = types.ModuleType('fastapi')

        class HTTPException(Exception):
            def __init__(self, code, detail):
                self.code, self.detail = code, detail

        fastapi.APIRouter = lambda **kw: SimpleNamespace(post=lambda *a, **k: (lambda f: f))
        fastapi.Depends = lambda f=None: None
        fastapi.HTTPException = HTTPException
        fastapi.status = SimpleNamespace(HTTP_201_CREATED=201, HTTP_409_CONFLICT=409, HTTP_403_FORBIDDEN=403)
        with patch.dict(sys.modules, {'fastapi': fastapi}):
            exec(compile(self.read('backend/app/api/v1/auth.py'), 'auth.py', 'exec'), namespace)
        register = namespace['register']

        def attempt(email, allowed):
            with patch.dict('os.environ', {'REGISTRATION_ALLOWED_EMAILS': allowed}):
                return register(SimpleNamespace(email=email), SimpleNamespace(
                    query=lambda model: SimpleNamespace(
                        filter=lambda cond: SimpleNamespace(one_or_none=lambda: None))))

        self.assertEqual(attempt('Teacher@School.uz', 'teacher@school.uz, other@x.uz'), 'created')
        self.assertEqual(attempt('other@x.uz', 'teacher@school.uz, other@x.uz'), 'created')
        for email, allowed in (('hacker@evil.com', 'teacher@school.uz'), ('teacher@school.uz', ''), ('a@b.c', '  ,  ')):
            with self.assertRaises(HTTPException) as ctx:
                attempt(email, allowed)
            self.assertEqual(ctx.exception.code, 403)


# --------------------------------------------------------------------------- GeminiProvider
@dataclass
class Result:
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


@dataclass
class KnowledgeExtractionResult(Result):
    tree: list = field(default_factory=list)


@dataclass
class QuestionGenerationResult(Result):
    questions: list = field(default_factory=list)


@dataclass
class GeneratedQuestion:
    question_text: str = ''
    question_type: str = ''
    difficulty: str = ''
    options: list = field(default_factory=list)
    correct_answer: dict = field(default_factory=dict)
    explanation: str = ''
    skill: str = None
    cognitive_level: str = None
    source_chunk_index: int = None


@dataclass
class EmbeddingResult:
    vectors: list = field(default_factory=list)
    dim: int = 384
    input_tokens: int = 0


class FakeMock:
    def embed(self, texts):
        return EmbeddingResult(vectors=[[0.0] * 384 for _ in texts], input_tokens=len(texts))


def response(text, prompt=100, output=50):
    return SimpleNamespace(text=text, usage_metadata=SimpleNamespace(
        prompt_token_count=prompt, candidates_token_count=output))


class GeminiProviderTests(SimpleTestCase):
    def setUp(self):
        base = types.ModuleType('app.services.providers.base')
        base.AIProvider = object
        base.EmbeddingResult = EmbeddingResult
        base.GeneratedQuestion = GeneratedQuestion
        base.KnowledgeExtractionResult = KnowledgeExtractionResult
        base.QuestionGenerationResult = QuestionGenerationResult
        mock_module = types.ModuleType('app.services.providers.mock_provider')
        mock_module.MockProvider = FakeMock
        self.client = MagicMock()
        genai = types.ModuleType('google.genai')
        genai.Client = MagicMock(return_value=self.client)
        types_module = types.ModuleType('google.genai.types')
        types_module.HttpOptions = lambda **kw: SimpleNamespace(**kw)
        types_module.GenerateContentConfig = lambda **kw: SimpleNamespace(**kw)
        genai.types = types_module
        google = types.ModuleType('google')
        google.genai = genai
        modules = {
            'app': types.ModuleType('app'), 'app.services': types.ModuleType('app.services'),
            'app.services.providers': types.ModuleType('app.services.providers'),
            'app.services.providers.base': base, 'app.services.providers.mock_provider': mock_module,
            'google': google, 'google.genai': genai, 'google.genai.types': types_module,
        }
        patcher = patch.dict(sys.modules, modules)
        patcher.start()
        self.addCleanup(patcher.stop)
        env = patch.dict('os.environ', {'GEMINI_API_KEY': 'k', 'GEMINI_MODEL': 'test-model'})
        env.start()
        self.addCleanup(env.stop)
        sleep = patch('time.sleep', lambda *_: None)
        sleep.start()
        self.addCleanup(sleep.stop)
        self.module = load(DEPLOY / 'gemini_provider.py', 'tc_gemini_provider')
        self.provider = self.module.GeminiProvider()

    def mcq(self, text='Q?', correct=1, **extra):
        return {'question_text': text, 'question_type': 'multiple_choice', 'difficulty': 'easy',
                'options': [{'label': l, 'text': f'v{l}', 'is_correct': i == correct}
                            for i, l in enumerate('ABCD')],
                'correct_answer': {'value': 'vB'}, 'explanation': 'because', **extra}

    def generate(self, **kw):
        defaults = dict(subject_name='Math', topic_name='T', chunks=[{'index': 0, 'text': 'x'}],
                        standard_config={}, difficulty='easy', question_type='multiple_choice', count=5,
                        avoid_similar_to=[])
        return self.provider.generate_questions(**{**defaults, **kw})

    def test_questions_are_parsed_with_tokens_and_the_requested_model(self):
        payload = {'questions': [self.mcq('Birinchi?', skill='algebra', source_chunk_index=0), self.mcq('Ikkinchi?')]}
        self.client.models.generate_content.return_value = response('```json\n' + json.dumps(payload) + '\n```', 321, 87)
        result = self.generate(count=2)
        self.assertEqual([q.question_text for q in result.questions], ['Birinchi?', 'Ikkinchi?'])
        self.assertEqual((result.input_tokens, result.output_tokens), (321, 87))
        self.assertEqual(result.questions[0].skill, 'algebra')
        self.assertEqual(result.questions[0].correct_answer, {'value': 'vB'})
        call = self.client.models.generate_content.call_args.kwargs
        self.assertEqual(call['model'], 'test-model')
        self.assertEqual(call['config'].response_mime_type, 'application/json')
        sent = json.loads(call['contents'][0])
        self.assertEqual((sent['count'], sent['language'], sent['topic']), (2, 'uz', 'T'))

    def test_malformed_questions_are_dropped_and_count_is_capped(self):
        bad_two_correct = self.mcq('Ikki javobli')
        bad_two_correct['options'][0]['is_correct'] = True
        payload = {'questions': [
            self.mcq('Yaxshi 1'), bad_two_correct, {'question_text': '   '}, 'axlat',
            {**self.mcq('Variantsiz'), 'options': []}, self.mcq('Yaxshi 2'), self.mcq('Yaxshi 3'),
        ]}
        self.client.models.generate_content.return_value = response(json.dumps(payload))
        result = self.generate(count=2)
        self.assertEqual([q.question_text for q in result.questions], ['Yaxshi 1', 'Yaxshi 2'])

    def test_non_mcq_questions_keep_their_answer_object_or_wrap_a_plain_value(self):
        payload = {'questions': [
            {'question_text': 'Qisqa?', 'question_type': 'short_answer', 'difficulty': 'easy', 'correct_answer': 'Toshkent'},
            {'question_text': 'Son?', 'question_type': 'numeric', 'difficulty': 'easy', 'correct_answer': {'value': 4}},
        ]}
        self.client.models.generate_content.return_value = response(json.dumps(payload))
        result = self.generate(question_type='short_answer')
        self.assertEqual(result.questions[0].correct_answer, {'value': 'Toshkent'})
        self.assertEqual(result.questions[1].correct_answer, {'value': 4})

    def test_invalid_json_is_retried_with_a_hint(self):
        good = response(json.dumps({'questions': [self.mcq()]}))
        self.client.models.generate_content.side_effect = [response('bu json emas'), good]
        result = self.generate()
        self.assertEqual(len(result.questions), 1)
        second = self.client.models.generate_content.call_args.kwargs['contents']
        self.assertIn('not a valid JSON', second[-1])

    def test_network_errors_are_retried_then_raise(self):
        self.client.models.generate_content.side_effect = RuntimeError('503')
        with self.assertRaises(RuntimeError) as ctx:
            self.generate()
        self.assertEqual(self.client.models.generate_content.call_count, self.module.MAX_RETRIES + 1)
        self.assertIn('503', str(ctx.exception))

    def test_knowledge_tree(self):
        tree = [{'level': 'topic', 'name': 'Algebra', 'children': [{'level': 'concept', 'name': 'Tenglama'}]},
                {'level': 'topic', 'name': ''}, 'axlat']
        self.client.models.generate_content.return_value = response(json.dumps({'tree': tree}), 10, 5)
        result = self.provider.extract_knowledge('Math', [{'index': 0, 'heading_path': 'H', 'text': 'matn'}])
        self.assertEqual([n['name'] for n in result.tree], ['Algebra'])
        self.assertEqual((result.input_tokens, result.output_tokens), (10, 5))
        self.assertIn('[chunk 0] (H)', self.client.models.generate_content.call_args.kwargs['contents'][0])

    def test_knowledge_with_unexpected_shape_gives_an_empty_tree(self):
        self.client.models.generate_content.return_value = response(json.dumps({'tree': 'yo\'q'}))
        self.assertEqual(self.provider.extract_knowledge('Math', []).tree, [])

    def test_embeddings_come_from_the_local_embedder(self):
        result = self.provider.embed(['a', 'b'])
        self.assertEqual((len(result.vectors), result.dim), (2, 384))
        self.client.models.generate_content.assert_not_called()

    def test_missing_key_is_a_clear_error(self):
        with patch.dict('os.environ', {'GEMINI_API_KEY': ''}):
            with self.assertRaises(RuntimeError) as ctx:
                self.module.GeminiProvider()
        self.assertIn('GEMINI_API_KEY', str(ctx.exception))


class DeployFilesTests(SimpleTestCase):
    """Server sozlama fayllarining xavfsizlik qoidalari (Docker/Caddy serverda ishga tushmaguncha shu yerda qo'riqlanadi)."""

    root = Path(__file__).resolve().parents[2]

    def read(self, rel):
        return (self.root / rel).read_text(encoding='utf-8')

    def test_test_creator_is_internal_only(self):
        caddy = self.read('deploy/Caddyfile')
        self.assertNotIn('tc-api', caddy)
        self.assertNotIn('tc-frontend', caddy)
        self.assertNotIn('TC_DOMAIN', caddy)
        compose = self.read('deploy/test-creator/docker-compose.tc.yml')
        self.assertNotIn('tc-frontend:', compose)
        self.assertIn('- tc-api', compose)  # bizning backend shu nom bilan ko'radi

    def test_ai_quiz_sources_are_not_publicly_served(self):
        caddy = self.read('deploy/Caddyfile')
        self.assertLess(caddy.index('handle /media/ai_quiz_sources/*'), caddy.index('handle /media/* {'))

    def test_cron_runs_the_ai_quiz_sync_in_its_own_loop(self):
        compose = self.read('docker-compose.prod.yml')
        self.assertIn('python manage.py sync_ai_quizzes', compose)
        self.assertLess(compose.index('sync_ai_quizzes'), compose.index('sync_homework_ai'))

    def test_caddy_mounts_the_whole_deploy_folder(self):
        compose = self.read('docker-compose.prod.yml')
        self.assertIn('- ./deploy:/etc/caddy:ro', compose)
        self.assertNotIn('./deploy/Caddyfile:/etc/caddy/Caddyfile', compose)

    def test_side_services_publish_no_ports(self):
        for rel in ('deploy/test-creator/docker-compose.tc.yml', 'deploy/ai-home-checker/docker-compose.ai.yml'):
            text = self.read(rel)
            self.assertNotRegex(text, r'(?m)^\s*ports:', rel)

    def test_test_creator_uses_gemini_and_closed_registration_defaults(self):
        compose = self.read('deploy/test-creator/docker-compose.tc.yml')
        self.assertIn('AI_DEFAULT_PROVIDER: ${TC_AI_PROVIDER:-gemini}', compose)
        self.assertIn('DEBUG: "false"', compose)
        self.assertIn('QUALITY_AUTO_APPROVE_THRESHOLD: "55"', compose)
        self.assertIn('QUALITY_REJECT_THRESHOLD: "40"', compose)
        readme = self.read('deploy/test-creator/README.md')
        self.assertIn('REGISTRATION_ALLOWED_EMAILS', readme)
        self.assertIn('apply_patch.py', readme)


# --------------------------------------------------------------------------- OpenAIProvider
class OpenAIProviderTests(SimpleTestCase):
    def setUp(self):
        base = types.ModuleType('app.services.providers.base')
        base.AIProvider = object
        base.EmbeddingResult = EmbeddingResult
        base.GeneratedQuestion = GeneratedQuestion
        base.KnowledgeExtractionResult = KnowledgeExtractionResult
        base.QuestionGenerationResult = QuestionGenerationResult
        mock_module = types.ModuleType('app.services.providers.mock_provider')
        mock_module.MockProvider = FakeMock
        self.client = MagicMock()
        openai = types.ModuleType('openai')
        openai.OpenAI = MagicMock(return_value=self.client)
        self.openai = openai
        modules = {
            'app': types.ModuleType('app'), 'app.services': types.ModuleType('app.services'),
            'app.services.providers': types.ModuleType('app.services.providers'),
            'app.services.providers.base': base, 'app.services.providers.mock_provider': mock_module,
            'openai': openai,
        }
        patcher = patch.dict(sys.modules, modules)
        patcher.start()
        self.addCleanup(patcher.stop)
        # OpenAI provayderi Gemini provayderidan meros oladi — avval o'sha yuklanadi
        sys.modules['app.services.providers.gemini_provider'] = load(DEPLOY / 'gemini_provider.py', 'tc_gem_for_openai')
        env = patch.dict('os.environ', {'OPENAI_API_KEY': 'k', 'OPENAI_MODEL': 'gpt-test'})
        env.start()
        self.addCleanup(env.stop)
        sleep = patch('time.sleep', lambda *_: None)
        sleep.start()
        self.addCleanup(sleep.stop)
        self.module = load(DEPLOY / 'openai_provider.py', 'tc_openai_provider')
        self.provider = self.module.OpenAIProvider()

    @staticmethod
    def completion(text, prompt=100, output=50):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
            usage=SimpleNamespace(prompt_tokens=prompt, completion_tokens=output),
        )

    def mcq(self, text='Q?', correct=1):
        return {'question_text': text, 'question_type': 'multiple_choice', 'difficulty': 'easy',
                'options': [{'label': l, 'text': f'v{l}', 'is_correct': i == correct} for i, l in enumerate('ABCD')],
                'correct_answer': {'value': 'vB'}, 'explanation': 'because'}

    def generate(self, **kw):
        defaults = dict(subject_name='English', topic_name='T', chunks=[{'index': 0, 'text': 'x'}],
                        standard_config={}, difficulty='easy', question_type='multiple_choice', count=5,
                        avoid_similar_to=[], language='en')
        return self.provider.generate_questions(**{**defaults, **kw})

    def test_questions_use_chat_completions_with_json_mode_and_report_tokens(self):
        payload = {'questions': [self.mcq('One?'), self.mcq('Two?')]}
        self.client.chat.completions.create.return_value = self.completion('```json\n' + json.dumps(payload) + '\n```', 321, 87)
        result = self.generate(count=2)
        self.assertEqual([q.question_text for q in result.questions], ['One?', 'Two?'])
        self.assertEqual((result.input_tokens, result.output_tokens), (321, 87))
        call = self.client.chat.completions.create.call_args.kwargs
        self.assertEqual(call['model'], 'gpt-test')
        self.assertEqual(call['response_format'], {'type': 'json_object'})
        self.assertEqual(call['max_completion_tokens'], 8192)
        self.assertEqual([m['role'] for m in call['messages']], ['system', 'user'])
        self.assertIn('JSON', call['messages'][0]['content'])  # JSON rejimi promptda "JSON" so'zini talab qiladi
        sent = json.loads(call['messages'][1]['content'])
        self.assertEqual((sent['count'], sent['language']), (2, 'en'))
        self.openai.OpenAI.assert_called_once()
        self.assertEqual(self.openai.OpenAI.call_args.kwargs['api_key'], 'k')

    def test_questions_without_exactly_one_correct_option_are_dropped(self):
        bad = self.mcq('Two correct')
        bad['options'][0]['is_correct'] = True
        self.client.chat.completions.create.return_value = self.completion(
            json.dumps({'questions': [self.mcq('Good'), bad, {'question_text': ' '}]}))
        self.assertEqual([q.question_text for q in self.generate().questions], ['Good'])

    def test_invalid_json_is_retried_with_a_correction_message(self):
        good = self.completion(json.dumps({'questions': [self.mcq('Q?')]}))
        self.client.chat.completions.create.side_effect = [self.completion('not json'), good]
        self.assertEqual(len(self.generate().questions), 1)
        second = self.client.chat.completions.create.call_args_list[1].kwargs['messages']
        self.assertIn('not a valid JSON', second[-1]['content'])

    def test_network_errors_are_retried_then_raise_with_the_provider_name(self):
        self.client.chat.completions.create.side_effect = ConnectionError('down')
        with self.assertRaises(RuntimeError) as ctx:
            self.generate()
        self.assertIn('OpenAI', str(ctx.exception))
        self.assertEqual(self.client.chat.completions.create.call_count, 3)

    def test_knowledge_tree_and_embeddings_are_inherited(self):
        tree = {'tree': [{'level': 'topic', 'name': 'Grammar', 'children': []}, {'level': 'topic'}]}
        self.client.chat.completions.create.return_value = self.completion(json.dumps(tree))
        result = self.provider.extract_knowledge('English', [{'index': 0, 'text': 'x'}])
        self.assertEqual([n['name'] for n in result.tree], ['Grammar'])
        self.assertEqual(len(self.provider.embed(['a']).vectors[0]), 384)

    def test_missing_key_is_a_clear_error(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}):
            with self.assertRaises(RuntimeError) as ctx:
                self.module.OpenAIProvider()
        self.assertIn('OPENAI_API_KEY', str(ctx.exception))

    def test_default_model_and_output_limit_are_overridable(self):
        with patch.dict('os.environ', {'OPENAI_MODEL': '', 'OPENAI_MAX_OUTPUT_TOKENS': '4000'}):
            os.environ.pop('OPENAI_MODEL')
            provider = self.module.OpenAIProvider()
        self.assertEqual((provider.model, provider.max_output_tokens), ('gpt-4o-mini', 4000))
