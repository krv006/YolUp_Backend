"""Savollar banki: AI yaratgan savollar eslab qolinadi, keyingi testda takrorlanmasligi uchun AI'ga ko'rsatiladi."""
import io
import json
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings

from . import bank
from .models import AiQuizJob, BankQuestion
from .tests_ai_exam import IELTS_RULES, LLM_ON, LONG, FakeOpenAI
from .tests_question_types import QuizTestBase


class RecordingOpenAI(FakeOpenAI):
    def __init__(self):
        super().__init__()
        self.sections = []  # yozuvchiga ketgan so'rovlar

    def __call__(self, url, json=None, **kwargs):
        system, user = json['messages'][0]['content'], json['messages'][1]['content']
        if not system.startswith('You are an exam designer'):
            self.sections.append(__import__('json').loads(user))
        return super().__call__(url, json=json, **kwargs)


@override_settings(**LLM_ON)
class QuestionBankTests(QuizTestBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        self.fake = RecordingOpenAI()
        patcher = patch('apps.quizzes.llm.requests.post', side_effect=self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def generate(self, exam_name='IELTS Reading', token=None):
        self.auth(token or self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/ai-generate/', {
            'file': SimpleUploadedFile('m.txt', (LONG * 5).encode(), content_type='text/plain'),
            'topic': 'Bees', 'question_count': 10, 'course': self.course_id, 'exam_name': exam_name,
            'rules_text': IELTS_RULES,
        }, format='multipart')
        self.assertEqual(resp.status_code, 202, resp.content)
        call_command('sync_ai_quizzes', stdout=io.StringIO())
        job = AiQuizJob.objects.get(pk=resp.json()['id'])
        self.assertEqual(job.status, 'done', job.error)
        return job

    def test_generated_questions_are_remembered_without_the_block_instruction(self):
        job = self.generate()
        rows = BankQuestion.objects.filter(teacher=job.teacher)
        self.assertEqual(rows.count(), job.quiz.questions.count())
        texts = set(rows.values_list('text', flat=True))
        self.assertIn('Bees live alone.', texts)  # ko'rsatma ("Do the statements agree...") olib tashlangan
        self.assertTrue(all('\n\n' not in t or 'Complete' not in t.split('\n\n')[0] for t in texts))
        sample = rows.get(text='Bees live alone.')
        self.assertEqual((sample.kind, sample.exam_key), ('single', 'ielts reading'))
        self.assertTrue(any(o['is_correct'] for o in sample.payload['options']))  # javob kaliti saqlangan

    def test_the_first_test_sends_no_avoid_list_and_the_second_does(self):
        self.generate()
        self.assertTrue(all('avoid_questions' not in s for s in self.fake.sections))
        self.fake.sections.clear()
        self.generate()
        sent = self.fake.sections[0]['avoid_questions']
        self.assertIn('Bees live alone.', sent)

    def test_the_same_questions_are_not_stored_twice(self):
        self.generate()
        first = BankQuestion.objects.count()
        self.generate()
        self.assertEqual(BankQuestion.objects.count(), first)

    def test_another_exam_or_another_teacher_does_not_see_them(self):
        job = self.generate()
        other_exam = type('J', (), {'teacher': job.teacher, 'exam_name': 'SAT', 'topic': 'x'})
        from apps.accounts.models import User

        stranger = User.objects.create_user(username='t2', password='x', role=User.Role.TEACHER, is_approved=True)
        other_teacher = type('J', (), {'teacher': stranger, 'exam_name': 'IELTS Reading', 'topic': 'x'})
        self.assertEqual(bank.recent_texts(other_exam), [])
        self.assertEqual(bank.recent_texts(other_teacher), [])
        self.assertTrue(bank.recent_texts(job))

    def test_digest_ignores_case_spacing_and_punctuation(self):
        self.assertEqual(bank.digest('Bees  live ALONE.'), bank.digest('bees live alone'))
        self.assertNotEqual(bank.digest('Bees live alone.'), bank.digest('Bees live together.'))

    def test_a_broken_bank_never_stops_test_creation(self):
        with patch('apps.quizzes.models.BankQuestion.objects.bulk_create', side_effect=RuntimeError('db')):
            job = self.generate()
        self.assertTrue(job.quiz_id)
        with patch('apps.quizzes.models.BankQuestion.objects.filter', side_effect=RuntimeError('db')):
            self.assertEqual(bank.recent_texts(job), [])
            self.assertEqual(bank.remember(job, {'sections': []}, {}), 0)

    def test_the_avoid_list_is_short(self):
        job = self.generate()
        for number in range(60):
            BankQuestion.objects.create(
                teacher=job.teacher, exam_key=bank.exam_key(job), text='x' * 500 + str(number), digest=f'd{number}')
        texts = bank.recent_texts(job)
        self.assertEqual(len(texts), bank.AVOID_LIMIT)
        self.assertTrue(all(len(t) <= bank.AVOID_CHARS for t in texts))
        json.dumps(texts)
