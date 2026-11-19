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


class PracticeSoundnessTests(TestCase):
    """Mashq savollari uchun: javobi noto'g'ri deb topilgan savol o'quvchiga berilmaydi."""

    def setUp(self):
        cache.clear()
        self.student = User.objects.create_user(username='ai_s2', password='x', role='student')
        self.api = APIClient()
        self.api.force_authenticate(self.student)

    def run_practice(self, questions, verdicts):
        calls = []

        def fake_chat(system, user, **kwargs):
            calls.append(system)
            return {'questions': questions} if 'practice questions' in system else {'verdicts': verdicts}

        with mock.patch.object(llm, 'enabled', return_value=True), mock.patch.object(llm, 'chat_json', side_effect=fake_chat):
            response = self.api.post('/api/v1/ai/student/practice/', {'topic': 'Tenglamalar', 'count': 5}, format='json')
        return response, calls

    def questions(self):
        return [
            {'text': '2x+3=11, x=?', 'options': ['3', '4', '5'], 'correct_index': 1, 'solution': '2x=8', 'explanation': 'x=4'},
            {'text': '5x-2=3x+6, x=?', 'options': ['2', '4', '3'], 'correct_index': 0, 'solution': '?', 'explanation': 'x=2'},
        ]

    def test_a_question_the_reviewer_rejects_is_not_given_to_the_student(self):
        response, calls = self.run_practice(self.questions(), [{'id': 0, 'ok': True}, {'id': 1, 'ok': False, 'problem': 'wrong key'}])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([q['text'] for q in response.json()['questions']], ['2x+3=11, x=?'])
        self.assertEqual(len(calls), 2)  # yaratish + tekshirish

    def test_the_prompt_asks_for_the_working_before_the_answer_index(self):
        _, calls = self.run_practice(self.questions(), [])
        system = calls[0]
        self.assertIn('"solution"', system)
        self.assertLess(system.index('"solution"'), system.index('"correct_index"'))

    def test_if_the_reviewer_fails_the_questions_stay(self):
        with mock.patch.object(llm, 'enabled', return_value=True), mock.patch.object(
                llm, 'chat_json', side_effect=[{'questions': self.questions()}, llm.LLMError('down')]):
            response = self.api.post('/api/v1/ai/student/practice/', {'topic': 'Tenglamalar'}, format='json')
        self.assertEqual(len(response.json()['questions']), 2)

    def test_if_the_reviewer_rejects_everything_it_is_ignored_as_unreliable(self):
        response, _ = self.run_practice(self.questions(), [{'id': 0, 'ok': False}, {'id': 1, 'ok': False}])
        self.assertEqual(len(response.json()['questions']), 2)  # >60% rad: tekshiruvchining o'zi adashgan bo'lishi mumkin

    def test_a_wrong_key_is_repaired_when_the_right_value_is_among_the_options(self):
        questions = [{'text': '4x-3=2x+9, x=?', 'equation': '4*x-3=2*x+9', 'options': ['2', '6', '1', '5'], 'correct_index': 3}]
        response, _ = self.run_practice(questions, [])
        self.assertEqual(response.status_code, 200, response.content)
        [question] = response.json()['questions']
        self.assertEqual(question['options'][question['correct_index']], '6')

    def test_an_equation_question_with_no_right_option_is_dropped(self):
        good = {'text': '2x+3=11, x=?', 'equation': '2*x+3=11', 'options': ['3', '4', '5'], 'correct_index': 1}
        bad = {'text': '5-2x=3x+1, x=?', 'equation': '5-2*x=3*x+1', 'options': ['0', '2', '1', '4'], 'correct_index': 0}
        response, _ = self.run_practice([good, bad], [])
        self.assertEqual([q['text'] for q in response.json()['questions']], ['2x+3=11, x=?'])
