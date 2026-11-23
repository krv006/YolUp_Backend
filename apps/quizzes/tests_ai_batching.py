"""AI test yaratish: savollarni bo'lib yozish va yetishmaganini to'ldirish; test tili (fan bo'yicha avtomatik, tekshiruv, tarjima).

Sabab (2026-11-24): 57 savol so'ralganda model bitta so'rovda 9-10 ta yozib to'xtagan va to'ldirilmagan; til esa inglizcha
material ustun kelib, o'zbekcha tanlansa ham savollar inglizcha chiqqan.
"""
import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.lessons.models import Course

from . import ai_exam
from .models import AiQuizJob
from .tests_ai_exam import LLM_ON, LONG, completion
from .tests_question_types import QuizTestBase


def plan_of(count, *, passage=False, language='Uzbek (Latin script)'):
    block = {'type': 'mcq', 'count': count, 'instruction': 'Tanlang.', 'options': 4, 'points': 1}
    return {'exam_name': '', 'language': language, 'rules': [], 'sections': [{
        'title': 'S', 'passage': {'min_words': 80, 'max_words': 120} if passage else None, 'audio': None, 'focus': '',
        'blocks': [block]}]}


def mcq(number, text=None):
    return {'kind': 'mcq', 'text': text or f'Savol raqami {number} nima haqida?', 'options': ['bir', 'ikki', 'uch', 'to‘rt'],
            'answer': number % 4, 'block': 0}


class LazyModel:
    """Production'dagidek: nechta so'ralmasin, har chaqiruvda eng ko'pi bilan `cap` ta YANGI savol yozadi."""

    def __init__(self, cap=10, passage=''):
        self.cap, self.passage, self.calls, self.next = cap, passage, [], 0

    def __call__(self, system, user, **kwargs):
        payload = json.loads(user)
        if 'section_spec' not in payload:  # tarjima/tekshiruv chaqiruvi
            return {'verdicts': [], 'items': payload.get('items', [])}
        self.calls.append(payload)
        wanted = sum(b['count'] + b['spare'] for b in payload['section_spec']['blocks'])
        made = [mcq(self.next + i) for i in range(min(self.cap, wanted))]
        self.next += len(made)
        return {'passage': self.passage, 'questions': made}


@override_settings(**LLM_ON)
class BatchingTests(SimpleTestCase):
    def run_section(self, plan, model, **extra):
        with patch('apps.quizzes.llm.chat_json', side_effect=model):
            return ai_exam.generate_section(plan, 0, 'material', avoid_topics=[], **extra)

    def test_a_large_block_is_asked_in_chunks_and_filled_to_the_requested_count(self):
        model = LazyModel(cap=10)  # 57 so'ralsa bitta so'rovda 10 ta yozadigan model
        result = self.run_section(plan_of(57), model)
        self.assertEqual((len(result['questions']), result['missing']), (57, 0))
        self.assertGreater(len(model.calls), 1)
        for payload in model.calls:  # hech bir so'rovda CHUNK dan ortiq asosiy savol so'ralmagan
            self.assertLessEqual(payload['section_spec']['blocks'][0]['count'], ai_exam.CHUNK)

    def test_every_pass_sees_the_questions_written_so_far(self):
        model = LazyModel(cap=12)
        self.run_section(plan_of(30), model)
        self.assertNotIn('avoid_questions', model.calls[0])
        self.assertTrue(model.calls[1]['avoid_questions'])
        self.assertIn(model.calls[0] and 'Savol raqami 0 nima haqida?', model.calls[1]['avoid_questions'])

    def test_a_small_block_still_needs_only_one_call(self):
        model = LazyModel(cap=50)
        result = self.run_section(plan_of(10), model)
        self.assertEqual((len(model.calls), len(result['questions']), result['missing']), (1, 10, 0))

    def test_repeated_questions_are_dropped_and_a_stalled_model_gives_up(self):
        same = [mcq(i, text='Bir xil savol') for i in range(3)]
        calls = []

        def model(system, user, **kwargs):
            calls.append(1)
            return {'passage': '', 'questions': same}

        with patch('apps.quizzes.llm.chat_json', side_effect=model):
            result = ai_exam.generate_section(plan_of(20), 0, 'material', avoid_topics=[])
        self.assertEqual(len(result['questions']), 1)
        self.assertEqual(result['missing'], 19)
        self.assertLessEqual(len(calls), 3)  # birinchi so'rov + 2 ta foydasiz urinish

    def test_the_passage_is_written_once_and_given_to_later_passes(self):
        model = LazyModel(cap=6, passage=LONG * 2)
        plan = plan_of(14, passage=True)
        result = self.run_section(plan, model)
        self.assertEqual(len(result['questions']), 14)
        self.assertEqual(result['passage'], (LONG * 2).strip())
        first, second = model.calls[0], model.calls[1]
        self.assertTrue(first['section_spec']['passage'])
        self.assertNotIn('passage_given', first)
        self.assertIsNone(second['section_spec']['passage'])
        self.assertEqual(second['passage_given'], (LONG * 2).strip())

    def test_progress_is_reported_and_a_saved_state_resumes_where_it_stopped(self):
        saved = []
        first = LazyModel(cap=12)
        with patch('apps.quizzes.llm.chat_json', side_effect=first):
            try:
                ai_exam.generate_section(plan_of(30), 0, 'material', avoid_topics=[],
                                         progress=lambda acc: (saved.append(json.loads(json.dumps(acc))), _stop(len(saved))))
            except _Stop:
                pass
        self.assertEqual(len(saved), 2)  # ikkinchi so'rovdan keyin "xato" yuz berdi
        self.assertEqual(len(saved[-1]['questions']), 24)
        second = LazyModel(cap=12)
        second.next = 24
        result = self.run_section(plan_of(30), second, resume=saved[-1])
        self.assertEqual((len(result['questions']), result['missing']), (30, 0))
        self.assertEqual(len(second.calls), 1)  # tugagan so'rovlar qayta qilinmadi

    def test_block_instruction_is_added_once_to_the_first_question_of_the_block(self):
        result = self.run_section(plan_of(30), LazyModel(cap=12))
        starts = [q['text'].startswith('Tanlang.') for q in result['questions']]
        self.assertEqual(starts.count(True), 1)
        self.assertTrue(starts[0])


class _Stop(Exception):
    pass


def _stop(count):
    if count == 2:
        raise _Stop()


class LanguageDetectionTests(SimpleTestCase):
    EN = 'What module provides the functions nlargest and nsmallest in the standard library? heapq math collections'
    UZ = "Standart kutubxonadagi nlargest va nsmallest funksiyalarini qaysi modul taqdim etadi? heapq math collections"
    RU = 'Какой модуль предоставляет функции nlargest и nsmallest в стандартной библиотеке языка? heapq math collections'

    def test_english_text_is_not_uzbek_or_russian(self):
        self.assertTrue(ai_exam.language_mismatch('uz', self.EN))
        self.assertTrue(ai_exam.language_mismatch('ru', self.EN))
        self.assertTrue(ai_exam.language_mismatch('uz_cyrl', self.EN))
        self.assertFalse(ai_exam.language_mismatch('en', self.EN))

    def test_uzbek_and_russian_texts_match_their_own_language_only(self):
        self.assertFalse(ai_exam.language_mismatch('uz', self.UZ))
        self.assertTrue(ai_exam.language_mismatch('en', self.UZ))
        self.assertFalse(ai_exam.language_mismatch('ru', self.RU))
        self.assertTrue(ai_exam.language_mismatch('uz', self.RU))
        self.assertTrue(ai_exam.language_mismatch('en', self.RU))

    def test_short_or_unclear_texts_are_never_flagged(self):
        for text in ('Q1?', '2 + 2 = ?', 'x a b c d', 'heapq'):
            for code in ('uz', 'en', 'ru', 'tr'):
                self.assertFalse(ai_exam.language_mismatch(code, text), (code, text))

    def test_language_is_resolved_from_the_subject(self):
        pick = lambda **kw: ai_exam.resolve_language(**{'subject': '', 'exam_name': '', 'rules': '', 'material': '', **kw})  # noqa: E731
        self.assertEqual(pick(subject='english'), 'en')
        self.assertEqual(pick(subject='russian'), 'ru')
        self.assertEqual(pick(subject='turkish'), 'tr')
        self.assertEqual(pick(subject='math', material='English book text'), 'uz')
        self.assertEqual(pick(subject='math', exam_name='IELTS Reading'), 'en')
        self.assertEqual(pick(subject='math', rules='IELTS Academic Reading: 3 passages'), 'en')
        self.assertEqual(pick(material='English book text'), '')  # fan yo'q: eski qoida (material tili)
        self.assertEqual(pick(), 'uz')

    def test_the_writer_prompt_puts_the_language_first_and_auto_adds_nothing(self):
        self.assertTrue(ai_exam._writer_system('Uzbek (Latin script)').startswith('OUTPUT LANGUAGE'))
        self.assertIn('translate the ideas', ai_exam._writer_system('Uzbek (Latin script)'))
        self.assertEqual(ai_exam._writer_system('auto'), ai_exam._WRITER_SYSTEM)


@override_settings(**LLM_ON)
class EnforceLanguageTests(SimpleTestCase):
    def question(self, text, options):
        return {'type': 'single', 'text': text, 'options': [{'text': o, 'is_correct': i == 0} for i, o in enumerate(options)],
                'block': 0}

    def test_english_questions_are_translated_in_place_keeping_the_option_order(self):
        questions = [self.question(LanguageDetectionTests.EN, ['heapq', 'math', 'collections']),
                     self.question(LanguageDetectionTests.UZ, ['heapq', 'math', 'collections'])]

        def fake(system, user, **kwargs):
            sent = json.loads(user)
            self.assertEqual([item['id'] for item in sent['items']], [0])  # faqat inglizcha savol yuborildi
            return {'items': [{'id': 0, 'text': 'Qaysi modul nlargest funksiyasini taqdim etadi?',
                               'options': ['heapq', 'math', 'collections']}]}

        with patch('apps.quizzes.llm.chat_json', side_effect=fake) as chat:
            ai_exam._enforce_language('Uzbek (Latin script)', questions)
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(questions[0]['text'], 'Qaysi modul nlargest funksiyasini taqdim etadi?')
        self.assertEqual([o['is_correct'] for o in questions[0]['options']], [True, False, False])
        self.assertEqual(questions[1]['text'], LanguageDetectionTests.UZ)

    def test_a_translation_that_changes_the_option_count_is_ignored(self):
        questions = [self.question(LanguageDetectionTests.EN, ['heapq', 'math', 'collections'])]
        bad = {'items': [{'id': 0, 'text': 'Boshqa matn bu yerda yoziladi', 'options': ['faqat bitta']}]}
        with patch('apps.quizzes.llm.chat_json', return_value=bad):
            ai_exam._enforce_language('Uzbek (Latin script)', questions)
        self.assertEqual(questions[0]['text'], LanguageDetectionTests.EN)

    def test_a_failing_translation_never_breaks_the_test(self):
        from . import llm
        questions = [self.question(LanguageDetectionTests.EN, ['heapq', 'math', 'collections'])]
        with patch('apps.quizzes.llm.chat_json', side_effect=llm.LLMError('503')):
            ai_exam._enforce_language('Uzbek (Latin script)', questions)
        self.assertEqual(questions[0]['text'], LanguageDetectionTests.EN)

    def test_auto_language_is_left_alone(self):
        questions = [self.question(LanguageDetectionTests.EN, ['heapq', 'math', 'collections'])]
        with patch('apps.quizzes.llm.chat_json') as chat:
            ai_exam._enforce_language('auto', questions)
        chat.assert_not_called()


@override_settings(**LLM_ON)
class JobLanguageTests(QuizTestBase):
    def setUp(self):
        super().setUp()
        self.writers = []

        def fake(url, json=None, **kwargs):  # oddiy reja (AI rejalashtirmaydi): yozuvchi so'ralgan sondagi savollarni qaytaradi
            system, payload = json['messages'][0]['content'], __import__('json').loads(json['messages'][1]['content'])
            if 'section_spec' not in payload:
                return completion({'items': payload.get('items', []), 'verdicts': []})
            self.writers.append(system)
            wanted = payload['section_spec']['blocks'][0]['count']
            return completion({'passage': '', 'questions': [mcq(i) for i in range(wanted)]})

        patcher = patch('apps.quizzes.llm.requests.post', side_effect=fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def course_with(self, subject):
        teacher = Course.objects.get(pk=self.course_id).teacher
        return Course.objects.create(teacher=teacher, title=f'{subject} guruhi', subject=subject)

    def run_job(self, course, **extra):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.management import call_command
        import io

        self.auth(self.teacher_token)
        data = {'file': SimpleUploadedFile('m.txt', (LONG * 5).encode(), content_type='text/plain'), 'topic': 'Bees',
                'question_count': 10, 'course': str(course.id), **extra}
        response = self.client.post('/api/v1/quizzes/ai-generate/', data, format='multipart')
        self.assertEqual(response.status_code, 202, response.content)
        call_command('sync_ai_quizzes', stdout=io.StringIO())
        job = AiQuizJob.objects.get(pk=response.json()['id'])
        self.assertEqual(job.status, 'done', job.error)
        return job

    def test_a_language_subject_makes_the_test_in_that_language_without_choosing_it(self):
        for subject, expected in (('english', 'English'), ('russian', 'Russian'), ('turkish', 'Turkish')):
            job = self.run_job(self.course_with(subject))
            self.assertEqual((job.language, job.plan['plan']['language']), ('', expected), subject)

    def test_another_subject_defaults_to_uzbek_even_with_foreign_material(self):
        job = self.run_job(self.course_with('math'))
        self.assertEqual(job.plan['plan']['language'], 'Uzbek (Latin script)')

    def test_an_explicit_choice_is_still_respected(self):
        job = self.run_job(self.course_with('english'), language='ru')
        self.assertEqual(job.plan['plan']['language'], 'Russian')

    def test_the_writer_is_told_the_language_first(self):
        self.run_job(self.course_with('english'))
        self.assertTrue(self.writers)
        self.assertTrue(all(s.startswith('OUTPUT LANGUAGE') and 'in English' in s[:200] for s in self.writers))

    def test_turkish_is_an_accepted_language(self):
        self.auth(self.teacher_token)
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = self.client.post('/api/v1/quizzes/ai-generate/', {
            'file': SimpleUploadedFile('m.txt', (LONG * 5).encode(), content_type='text/plain'), 'topic': 'Bees',
            'question_count': 10, 'language': 'tr'}, format='multipart')
        self.assertEqual(response.status_code, 202, response.content)
        self.assertEqual(AiQuizJob.objects.get(pk=response.json()['id']).language, 'tr')

