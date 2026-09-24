"""Import qilingan test DARHOL DB'ga doimiy (draft) yoziladi; e'lon qilinguncha
o'quvchiga ko'rinmaydi; to'liq bo'lgach `publish` bilan e'lon qilinadi."""
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.notifications.models import Notification

from .models import Question, Quiz
from .tests import _build_docx
from .tests_google_forms_scrape import FORM_URL, REAL_FORM_HTML
from .tests_question_types import QuizTestBase

DOCX_LINES = [
    'Fizika testi',
    '1. Yorug\'lik tezligi?', 'A) 300 000', 'B) 150 000', "To'g'ri javob: A",
    '2. Javobi yozilmagan savol?', 'A) x', 'B) y',
]


def _forms_response():
    resp = Mock()
    resp.status_code = 200
    resp.text = REAL_FORM_HTML
    resp.content = REAL_FORM_HTML.encode('utf-8')
    return resp


class ImportSavesDraftTests(QuizTestBase):
    def import_docx(self, **extra):
        self.auth(self.teacher_token)
        upload = SimpleUploadedFile('t.docx', _build_docx(DOCX_LINES))
        return self.client.post(
            '/api/v1/quizzes/import/', {'file': upload, **extra}, format='multipart',
        )

    def test_import_without_topic_is_still_a_non_persisting_preview(self):
        resp = self.import_docx()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Quiz.objects.count(), 0)

    def test_import_with_topic_persists_draft_immediately(self):
        resp = self.import_docx(topic='Yorug\'lik', course=self.course_id)
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body['status'], 'draft')
        self.assertEqual(len(body['questions']), 2)
        self.assertEqual([w['question_number'] for w in body['warnings']], [2])
        quiz = Quiz.objects.get(pk=body['id'])
        self.assertEqual(quiz.status, 'draft')
        self.assertEqual(Question.objects.filter(quiz=quiz).count(), 2)
        # javobi yozilmagan savol ham saqlangan (to'g'ri variant yo'q)
        second = quiz.questions.get(order=1)
        self.assertEqual(second.options.filter(is_correct=True).count(), 0)

    def test_import_needs_course_or_subject_when_saving(self):
        self.assertEqual(self.import_docx(topic='x').status_code, 400)

    def test_google_form_import_saves_ungrouped_draft_by_subject(self):
        self.auth(self.teacher_token)
        with patch('apps.quizzes.google_forms_scrape.requests.get', return_value=_forms_response()):
            resp = self.client.post('/api/v1/quizzes/import-google-form/', {
                'url': FORM_URL, 'topic': 'Kvant', 'subject': 'physics',
            }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body['status'], 'draft')
        self.assertIsNone(body['course'])
        self.assertEqual(body['subject'], 'physics')
        self.assertEqual(len(body['questions']), 2)


class DraftVisibilityAndPublishTests(QuizTestBase):
    SINGLE_NO_ANSWER = [{'type': 'single', 'text': 'Q1', 'options': [{'text': 'a'}, {'text': 'b'}]}]

    def make_draft(self, questions=None):
        self.auth(self.teacher_token)
        return self.client.post('/api/v1/quizzes/', {
            'course': self.course_id, 'topic': 'Mavzu', 'status': 'draft',
            'questions': questions or self.SINGLE_NO_ANSWER,
        }, format='json')

    def test_draft_allows_questions_without_correct_answer_but_published_does_not(self):
        self.assertEqual(self.make_draft().status_code, 201)
        self.auth(self.teacher_token)
        strict = self.client.post('/api/v1/quizzes/', {
            'course': self.course_id, 'topic': 'Mavzu', 'questions': self.SINGLE_NO_ANSWER,
        }, format='json')
        self.assertEqual(strict.status_code, 400)

    def test_draft_hidden_from_students_and_sends_no_notification(self):
        quiz_id = self.make_draft().json()['id']
        self.auth(self.child_token)
        self.assertEqual(self.client.get(f'/api/v1/quizzes/{quiz_id}/').status_code, 404)
        listing = self.client.get('/api/v1/quizzes/').json()
        rows = listing['results'] if isinstance(listing, dict) else listing
        self.assertEqual(rows, [])
        self.assertFalse(Notification.objects.filter(link_type='quiz').exists())
        # o'qituvchi ko'radi
        self.auth(self.teacher_token)
        self.assertEqual(self.client.get(f'/api/v1/quizzes/{quiz_id}/').status_code, 200)

    def test_publish_rejected_until_every_question_has_a_correct_answer(self):
        quiz_id = self.make_draft().json()['id']
        self.auth(self.teacher_token)
        resp = self.client.post(f'/api/v1/quizzes/{quiz_id}/publish/')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('1', str(resp.json()['error']['details']['questions']))
        self.assertEqual(Quiz.objects.get(pk=quiz_id).status, 'draft')

    def test_edit_draft_then_publish_makes_it_visible_and_notifies(self):
        quiz_id = self.make_draft().json()['id']
        self.auth(self.teacher_token)
        # draft'da to'liq bo'lmagan savollar bilan tahrirlash ruxsat
        edited = self.client.patch(f'/api/v1/quizzes/{quiz_id}/', {'questions': self.SINGLE_NO_ANSWER}, format='json')
        self.assertEqual(edited.status_code, 200, edited.content)
        fixed = self.client.patch(f'/api/v1/quizzes/{quiz_id}/', {'questions': [
            {'type': 'single', 'text': 'Q1', 'options': [{'text': 'a', 'is_correct': True}, {'text': 'b'}]},
        ]}, format='json')
        self.assertEqual(fixed.status_code, 200, fixed.content)

        with self.captureOnCommitCallbacks(execute=True):
            published = self.client.post(f'/api/v1/quizzes/{quiz_id}/publish/')
        self.assertEqual(published.status_code, 200, published.content)
        self.assertEqual(published.json()['status'], 'published')
        self.assertTrue(Notification.objects.filter(link_type='quiz').exists())

        self.auth(self.child_token)
        self.assertEqual(self.client.get(f'/api/v1/quizzes/{quiz_id}/').status_code, 200)

    def test_published_quiz_edit_still_requires_correct_answers(self):
        self.auth(self.teacher_token)
        quiz_id = self.client.post('/api/v1/quizzes/', {
            'course': self.course_id, 'topic': 'Mavzu', 'questions': [
                {'type': 'single', 'text': 'Q', 'options': [{'text': 'a', 'is_correct': True}, {'text': 'b'}]},
            ],
        }, format='json').json()['id']
        resp = self.client.patch(f'/api/v1/quizzes/{quiz_id}/', {'questions': self.SINGLE_NO_ANSWER}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_publishing_an_already_published_quiz_is_a_no_op(self):
        self.auth(self.teacher_token)
        published_id = self.client.post('/api/v1/quizzes/', {
            'course': self.course_id, 'topic': 'M', 'questions': [
                {'type': 'single', 'text': 'Q', 'options': [{'text': 'a', 'is_correct': True}, {'text': 'b'}]},
            ],
        }, format='json').json()['id']
        resp = self.client.post(f'/api/v1/quizzes/{published_id}/publish/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'published')

    def test_student_cannot_publish(self):
        quiz_id = self.make_draft().json()['id']
        self.auth(self.child_token)
        self.assertEqual(self.client.post(f'/api/v1/quizzes/{quiz_id}/publish/').status_code, 403)
