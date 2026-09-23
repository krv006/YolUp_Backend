"""Ochiq Google Docs havolasidan test import qilish — `requests.get` mocklanadi."""
from unittest.mock import Mock, patch

from rest_framework.test import APITestCase

from apps.accounts.tests import login, register

DOC_URL = 'https://docs.google.com/document/d/1AbC-xyz_123/edit'

SAMPLE_TEXT = (
    "Fizika 1-bob testi\n\n"
    "1. Yorug'lik tezligi qancha?\n"
    "A) 300 000 km/s\n"
    "B) 150 000 km/s\n"
    "To'g'ri javob: A\n\n"
    "2. Suv formulasi?\n"
    "A) CO2\n"
    "B) H2O\n"
    "To'g'ri javob: B\n"
)


def _mock_response(text, status=200, content_type='text/plain; charset=UTF-8'):
    resp = Mock()
    resp.status_code = status
    resp.headers = {'Content-Type': content_type}
    resp.text = text
    resp.content = text.encode('utf-8')
    return resp


class QuizGoogleDocImportTests(APITestCase):
    def setUp(self):
        register(self.client, 'gd_teacher', 'teacher')
        self.auth(login(self.client, 'gd_teacher'))
        register(self.client, 'gd_student', 'student')
        self.student_token = login(self.client, 'gd_student')

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_imports_well_formed_public_doc(self):
        with patch('apps.quizzes.google_docs_import.requests.get', return_value=_mock_response(SAMPLE_TEXT)) as m:
            resp = self.client.post('/api/v1/quizzes/import-google-doc/', {'url': DOC_URL}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body['title'], 'Fizika 1-bob testi')
        self.assertEqual(len(body['questions']), 2)
        self.assertEqual(body['questions'][0]['options'][0]['is_correct'], True)
        self.assertEqual(body['warnings'], [])
        called_url = m.call_args.args[0]
        self.assertEqual(called_url, 'https://docs.google.com/document/d/1AbC-xyz_123/export?format=txt')

    def test_preview_can_be_submitted_as_real_quiz(self):
        with patch('apps.quizzes.google_docs_import.requests.get', return_value=_mock_response(SAMPLE_TEXT)):
            preview = self.client.post(
                '/api/v1/quizzes/import-google-doc/', {'url': DOC_URL}, format='json',
            ).json()
        course_id = self.client.post('/api/v1/courses/', {'title': 'Fizika', 'subject': 'physics'}).json()['id']
        create = self.client.post('/api/v1/quizzes/', {
            'course': course_id, 'topic': 'Import qilingan', 'title': preview['title'],
            'questions': preview['questions'],
        }, format='json')
        self.assertEqual(create.status_code, 201, create.content)
        self.assertEqual(len(create.json()['questions']), 2)

    def test_invalid_url_rejected_without_network_call(self):
        with patch('apps.quizzes.google_docs_import.requests.get') as m:
            resp = self.client.post(
                '/api/v1/quizzes/import-google-doc/', {'url': 'https://example.com/not-google-docs'}, format='json',
            )
        self.assertEqual(resp.status_code, 400)
        m.assert_not_called()

    def test_private_doc_login_redirect_is_rejected(self):
        html = _mock_response('<html>Sign in</html>', content_type='text/html; charset=UTF-8')
        with patch('apps.quizzes.google_docs_import.requests.get', return_value=html):
            resp = self.client.post('/api/v1/quizzes/import-google-doc/', {'url': DOC_URL}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('url', resp.json()['error']['details'])

    def test_empty_doc_rejected(self):
        with patch('apps.quizzes.google_docs_import.requests.get', return_value=_mock_response('   \n  ')):
            resp = self.client.post('/api/v1/quizzes/import-google-doc/', {'url': DOC_URL}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_doc_with_no_detected_questions_rejected(self):
        with patch('apps.quizzes.google_docs_import.requests.get', return_value=_mock_response('Faqat sarlavha, savol yoq')):
            resp = self.client.post('/api/v1/quizzes/import-google-doc/', {'url': DOC_URL}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_student_cannot_import(self):
        self.auth(self.student_token)
        with patch('apps.quizzes.google_docs_import.requests.get') as m:
            resp = self.client.post('/api/v1/quizzes/import-google-doc/', {'url': DOC_URL}, format='json')
        self.assertEqual(resp.status_code, 403)
        m.assert_not_called()

    def test_missing_url_is_400(self):
        resp = self.client.post('/api/v1/quizzes/import-google-doc/', {}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_network_error_surfaces_as_400(self):
        import requests as requests_module
        with patch('apps.quizzes.google_docs_import.requests.get', side_effect=requests_module.Timeout('timed out')):
            resp = self.client.post('/api/v1/quizzes/import-google-doc/', {'url': DOC_URL}, format='json')
        self.assertEqual(resp.status_code, 400)
