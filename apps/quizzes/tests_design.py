"""Yangi dizayn: urinishlarda vaqt va to'g'ri/jami soni, savollar bo'yicha xato foizi, xato savollardan mini-test."""
from django.test import override_settings

from apps.quizzes.models import AiQuizJob, Option, Question

from .tests_question_types import QuizTestBase

QUESTIONS = [
    {'type': 'single', 'text': 'Birinchi savol', 'points': 2, 'options': [
        {'text': "to'g'ri", 'is_correct': True}, {'text': 'xato', 'is_correct': False}]},
    {'type': 'single', 'text': '  Ikkinchi\nsavol  ', 'points': 2, 'options': [
        {'text': "to'g'ri", 'is_correct': True}, {'text': 'xato', 'is_correct': False}]},
]


class DesignBase(QuizTestBase):
    def setUp(self):
        super().setUp()
        self.quiz = self.make_quiz(QUESTIONS).json()
        self.ids = [q['id'] for q in self.quiz['questions']]

    def answers(self, first=True, second=True):
        out = []
        for question_id, correct in zip(self.ids, (first, second)):
            option = Option.objects.get(question_id=question_id, is_correct=correct)
            out.append({'question': question_id, 'selected_option': str(option.id)})
        return out

    def attempt(self, first=True, second=True, **extra):
        self.auth(self.child_token)
        resp = self.client.post(
            f'/api/v1/quizzes/{self.quiz["id"]}/attempts/', {'answers': self.answers(first, second), **extra}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()


class AttemptFieldsTests(DesignBase):
    def test_result_and_list_have_time_and_counts(self):
        result = self.attempt(first=True, second=False, duration_seconds=312)
        self.assertEqual((result['duration_seconds'], result['correct_count'], result['question_count']), (312, 1, 2))
        self.auth(self.teacher_token)
        rows = self.client.get(f'/api/v1/quizzes/{self.quiz["id"]}/attempts/').json()
        self.assertEqual((rows[0]['duration_seconds'], rows[0]['correct_count'], rows[0]['question_count']), (312, 1, 2))

    def test_duration_is_optional_and_validated(self):
        self.assertIsNone(self.attempt()['duration_seconds'])
        self.auth(self.child_token)
        for bad in (-1, 24 * 3600 + 1, 'abc'):
            resp = self.client.post(
                f'/api/v1/quizzes/{self.quiz["id"]}/attempts/', {'answers': self.answers(), 'duration_seconds': bad}, format='json')
            self.assertEqual(resp.status_code, 400, bad)


class QuestionStatsTests(DesignBase):
    def test_most_missed_first_with_percentages(self):
        self.attempt(first=True, second=False)
        self.attempt(first=False, second=False)
        self.auth(self.teacher_token)
        rows = self.client.get(f'/api/v1/quizzes/{self.quiz["id"]}/stats/').json()
        self.assertEqual([(r['order'], r['wrong_rate'], r['attempts_count']) for r in rows], [(2, 100, 2), (1, 50, 2)])
        self.assertEqual(rows[0]['label'], 'Ikkinchi savol')  # bo'shliq va qator uzilishi tozalanadi
        self.assertEqual(rows[0]['question_id'], self.ids[1])

    def test_no_attempts_and_permissions(self):
        self.auth(self.teacher_token)
        self.assertEqual(self.client.get(f'/api/v1/quizzes/{self.quiz["id"]}/stats/').json(), [])
        self.auth(self.child_token)
        self.assertEqual(self.client.get(f'/api/v1/quizzes/{self.quiz["id"]}/stats/').status_code, 403)
        self.auth(self.parent_token)
        self.assertEqual(self.client.get(f'/api/v1/quizzes/{self.quiz["id"]}/stats/').status_code, 403)


class MiniTestTests(DesignBase):
    URL = '/api/v1/quizzes/ai-generate/mini/'

    def post(self, data, token=None):
        self.auth(token or self.teacher_token)
        return self.client.post(self.URL, data, format='json')

    @override_settings(OPENAI_API_KEY='sk-test')
    def test_creates_an_ai_job_from_the_missed_questions(self):
        resp = self.post({'quiz_id': self.quiz['id'], 'wrong_question_ids': [self.ids[1]]})
        self.assertEqual(resp.status_code, 202, resp.content)
        job = AiQuizJob.objects.get(pk=resp.json()['id'])
        self.assertEqual((job.status, job.question_count, str(job.course_id)), ('queued', 5, self.course_id))
        self.assertIn('Ikkinchi savol', job.source_text)
        self.assertNotIn('Birinchi savol', job.source_text)
        self.assertIn("✓ to'g'ri", job.source_text)  # to'g'ri javob belgilangan

    @override_settings(OPENAI_API_KEY='sk-test')
    def test_validation_and_permissions(self):
        good = {'quiz_id': self.quiz['id'], 'wrong_question_ids': [self.ids[0]]}
        self.assertEqual(self.post({**good, 'wrong_question_ids': []}).status_code, 400)
        self.assertEqual(self.post({**good, 'wrong_question_ids': 'x'}).status_code, 400)
        self.assertEqual(self.post({**good, 'wrong_question_ids': ['00000000-0000-0000-0000-000000000000']}).status_code, 400)
        self.assertEqual(self.post({**good, 'quiz_id': 'abc'}).status_code, 400)
        self.assertEqual(self.post({**good, 'quiz_id': '00000000-0000-0000-0000-000000000000'}).status_code, 404)
        self.assertEqual(self.post(good, token=self.child_token).status_code, 403)

    @override_settings(OPENAI_API_KEY='')
    def test_without_the_ai_key_it_is_refused_clearly(self):
        resp = self.post({'quiz_id': self.quiz['id'], 'wrong_question_ids': [self.ids[0]]})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(AiQuizJob.objects.count(), 0)
