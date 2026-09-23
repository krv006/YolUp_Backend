"""Ochiq Google Forms'dan import — haqiqiy formadan olingan fixture bilan
(`tests_fixtures_google_form.html`, 2026-09-23, bitta 'single' va bitta
'multiple' savoli bor haqiqiy forma). `requests.get` mocklanadi."""
import os
from unittest.mock import Mock, patch

from rest_framework.test import APITestCase

from apps.accounts.tests import login, register

FORM_URL = 'https://docs.google.com/forms/d/e/1FAIpQLSeC4ErABolqzKHHVtYFqFGBuv9UO3QjlQMv4-9WmT5USUOooQ/viewform'

_FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'tests_fixtures_google_form.html')
with open(_FIXTURE_PATH, encoding='utf-8') as _f:
    REAL_FORM_HTML = _f.read()


def _mock_response(html, status=200):
    resp = Mock()
    resp.status_code = status
    resp.text = html
    resp.content = html.encode('utf-8')
    return resp


class QuizGoogleFormImportTests(APITestCase):
    def setUp(self):
        register(self.client, 'gf_teacher', 'teacher')
        self.auth(login(self.client, 'gf_teacher'))
        register(self.client, 'gf_student', 'student')
        self.student_token = login(self.client, 'gf_student')

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_imports_real_form_single_and_multiple_types(self):
        with patch('apps.quizzes.google_forms_scrape.requests.get', return_value=_mock_response(REAL_FORM_HTML)) as m:
            resp = self.client.post('/api/v1/quizzes/import-google-form/', {'url': FORM_URL}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body['title'], 'Kvant fizikasi')
        self.assertEqual(len(body['questions']), 2)
        self.assertEqual(body['questions'][0]['type'], 'single')
        self.assertEqual(len(body['questions'][0]['options']), 3)
        self.assertEqual(body['questions'][1]['type'], 'multiple')
        self.assertEqual(len(body['questions'][1]['options']), 4)
        called_url = m.call_args.args[0]
        self.assertEqual(
            called_url,
            'https://docs.google.com/forms/d/e/1FAIpQLSeC4ErABolqzKHHVtYFqFGBuv9UO3QjlQMv4-9WmT5USUOooQ/viewform',
        )

    def test_no_correct_answer_is_ever_marked_and_all_flagged(self):
        with patch('apps.quizzes.google_forms_scrape.requests.get', return_value=_mock_response(REAL_FORM_HTML)):
            resp = self.client.post('/api/v1/quizzes/import-google-form/', {'url': FORM_URL}, format='json')
        body = resp.json()
        for question in body['questions']:
            self.assertTrue(all(not o['is_correct'] for o in question['options']))
        self.assertEqual(len(body['warnings']), 2)
        self.assertTrue(all(w['reason'] == 'answer_not_detected' for w in body['warnings']))

    def test_preview_requires_manual_answer_marking_before_it_becomes_a_real_quiz(self):
        with patch('apps.quizzes.google_forms_scrape.requests.get', return_value=_mock_response(REAL_FORM_HTML)):
            preview = self.client.post(
                '/api/v1/quizzes/import-google-form/', {'url': FORM_URL}, format='json',
            ).json()
        course_id = self.client.post('/api/v1/courses/', {'title': 'Fizika', 'subject': 'physics'}).json()['id']
        questions = preview['questions']
        questions[0]['options'][1]['is_correct'] = True  # o'qituvchi to'g'ri javob(lar)ni belgilaydi
        questions[1]['options'][0]['is_correct'] = True
        create = self.client.post('/api/v1/quizzes/', {
            'course': course_id, 'topic': 'Kvant', 'title': preview['title'],
            'questions': questions,
        }, format='json')
        self.assertEqual(create.status_code, 201, create.content)

    def test_invalid_form_url_rejected_without_network_call(self):
        with patch('apps.quizzes.google_forms_scrape.requests.get') as m:
            resp = self.client.post(
                '/api/v1/quizzes/import-google-form/', {'url': 'https://example.com/nope'}, format='json',
            )
        self.assertEqual(resp.status_code, 400)
        m.assert_not_called()

    def test_missing_url_is_400(self):
        resp = self.client.post('/api/v1/quizzes/import-google-form/', {}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_private_form_rejected(self):
        with patch('apps.quizzes.google_forms_scrape.requests.get', return_value=_mock_response('no data var here', status=200)):
            resp = self.client.post('/api/v1/quizzes/import-google-form/', {'url': FORM_URL}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_network_error_surfaces_as_400(self):
        import requests as requests_module
        with patch('apps.quizzes.google_forms_scrape.requests.get', side_effect=requests_module.Timeout('timed out')):
            resp = self.client.post('/api/v1/quizzes/import-google-form/', {'url': FORM_URL}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_student_cannot_import(self):
        self.auth(self.student_token)
        with patch('apps.quizzes.google_forms_scrape.requests.get') as m:
            resp = self.client.post('/api/v1/quizzes/import-google-form/', {'url': FORM_URL}, format='json')
        self.assertEqual(resp.status_code, 403)
        m.assert_not_called()
