"""O'quvchi AI yordamchisi: tushuntirish va mashq, kunlik limit."""
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.quizzes import llm


class StudentAiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.student = User.objects.create_user(username='ai_s', password='x', role='student')
        self.teacher = User.objects.create_user(username='ai_t', password='x', role='teacher', is_approved=True)
        self.api = APIClient()
        self.api.force_authenticate(self.student)

    def call(self, path, body, result):
        with mock.patch.object(llm, 'enabled', return_value=True), mock.patch.object(llm, 'chat_json', return_value=result):
            return self.api.post(f'/api/v1/ai/student/{path}/', body, format='json')

    def test_explain(self):
        response = self.call('explain', {'question': '2+2?', 'wrong_answer': '5', 'correct_answer': '4'}, {'explanation': 'Qo‘shing', 'tip': 'Sanang'})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((response.json()['explanation'], response.json()['used'], response.json()['limit']), ('Qo‘shing', 1, 20))

    def test_practice_filters_broken_questions(self):
        good = {'text': 'Savol?', 'options': ['a', 'b', 'c'], 'correct_index': 2, 'explanation': 'x'}
        broken = [{'text': 'Yomon', 'options': ['a'], 'correct_index': 0}, {'text': 'Indeks', 'options': ['a', 'b'], 'correct_index': 9}]
        response = self.call('practice', {'topic': 'Kasrlar', 'count': 5}, {'questions': [good, *broken]})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response.json()['questions']), 1)

    def test_all_broken_is_an_error_and_does_not_spend_limit(self):
        response = self.call('practice', {'topic': 'Kasrlar'}, {'questions': [{'text': '', 'options': []}]})
        self.assertEqual(response.status_code, 400)
        ok = self.call('explain', {'question': 'Savol'}, {'explanation': 'ok'})
        self.assertEqual(ok.json()['used'], 1)

    @override_settings(STUDENT_AI_DAILY_LIMIT=2)
    def test_daily_limit(self):
        for _ in range(2):
            self.assertEqual(self.call('explain', {'question': 'Savol'}, {'explanation': 'ok'}).status_code, 200)
        self.assertEqual(self.call('explain', {'question': 'Savol'}, {'explanation': 'ok'}).status_code, 429)

    def test_validation_and_disabled(self):
        self.assertEqual(self.call('explain', {'question': ' '}, {}).status_code, 400)
        self.assertEqual(self.call('practice', {'topic': ''}, {}).status_code, 400)
        with mock.patch.object(llm, 'enabled', return_value=False):
            self.assertEqual(self.api.post('/api/v1/ai/student/explain/', {'question': 'x'}, format='json').status_code, 400)

    def test_teachers_cannot_use_student_ai(self):
        teacher = APIClient()
        teacher.force_authenticate(self.teacher)
        self.assertEqual(teacher.post('/api/v1/ai/student/explain/', {'question': 'x'}, format='json').status_code, 403)

    def test_llm_failure_is_friendly_and_refunded(self):
        with mock.patch.object(llm, 'enabled', return_value=True), mock.patch.object(llm, 'chat_json', side_effect=llm.LLMError('down')):
            self.assertEqual(self.api.post('/api/v1/ai/student/explain/', {'question': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.call('explain', {'question': 'x'}, {'explanation': 'ok'}).json()['used'], 1)
