"""AI bilan test yaratish: tashqi Test-creator xizmati bilan integratsiya (HTTP so'rovlar soxta)."""
import json
import shutil
import tempfile
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import requests
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from apps.notifications.models import Notification

from . import tc_client
from .models import AiQuizJob, Quiz
from .tests_question_types import QuizTestBase

TC_ON = dict(
    TEST_CREATOR_URL='http://tc-api:8000/api/v1', TEST_CREATOR_EMAIL='svc@edu.uz',
    TEST_CREATOR_PASSWORD='x' * 12, TEST_CREATOR_GIVE_UP_MINUTES=45,
)

EXPORT = {
    'title': 'Quadratic equations',
    'questions': [
        {'order': 1, 'question_text': '2+2 = ?', 'question_type': 'multiple_choice', 'points': 1,
         'options': [{'label': 'A', 'text': '3'}, {'label': 'B', 'text': '4'}], 'correct_options': ['B']},
        {'order': 2, 'question_text': 'x^2 = 9, x = ?', 'question_type': 'multiple_choice', 'points': 2,
         'options': [{'label': 'A', 'text': '3'}, {'label': 'B', 'text': '5'}], 'correct_options': ['A']},
    ],
}


def reply(status=200, body=None, content=None):
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = body if body is not None else {}
    mock.text = json.dumps(body) if body is not None else ''
    mock.content = content if content is not None else b''
    return mock


class FakeTestCreator:
    """Test-creator HTTP API'sining qisqa nusxasi. `requests.request` o'rniga qo'yiladi."""

    def __init__(self):
        self.calls = []
        self.registered = True           # False: birinchi login 401 beradi
        self.extraction = 'done'         # status endpoint qaytaradigan holat
        self.extraction_error = None
        self.export = json.dumps(EXPORT).encode()
        self.generate_status = 200
        self.upload_params = None

    def __call__(self, method, url, **kwargs):
        path = url.split('/api/v1', 1)[1]
        self.calls.append((method, path))
        if path == '/auth/login':
            if not self.registered:
                return reply(401, {'detail': 'Invalid email or password'})
            return reply(200, {'access_token': 'tok'})
        if path == '/auth/register':
            self.registered = True
            return reply(201, {'access_token': 'tok'})
        assert kwargs['headers']['Authorization'] == 'Bearer tok'
        if path == '/subjects':
            return reply(200, [{'id': 'sub-math', 'code': 'MATH'}, {'id': 'sub-gen', 'code': 'GENERAL'}])
        if path == '/documents':
            self.upload_params = kwargs.get('params')
            return reply(201, {'id': 'doc-1'})
        if path == '/documents/doc-1/process':
            return reply(202, {'job_id': 'j'})
        if path == '/documents/doc-1/status':
            return reply(200, {
                'extraction_status': self.extraction, 'error_message': self.extraction_error,
            })
        if path.startswith('/standards/') and path.endswith('/versions'):
            return reply(200, [{'id': 'ver-old', 'status': 'draft'}, {'id': 'ver-1', 'status': 'active'}])
        if path == '/blueprints':
            self.blueprint_payload = kwargs['json']
            return reply(201, {'id': 'bp-1'})
        if path == '/tests/generate':
            return reply(self.generate_status, {'test': {'id': 'test-1'}} if self.generate_status < 400 else {'detail': 'boom'})
        if path == '/tests/test-1/export':
            return reply(200, content=self.export)
        raise AssertionError(f'kutilmagan so\'rov: {method} {path}')


@override_settings(**TC_ON)
class AiQuizJobTests(QuizTestBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        tc_client._state['token'] = None
        self.fake = FakeTestCreator()
        patcher = patch('apps.quizzes.tc_client.requests.request', side_effect=self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def upload(self, name='material.pdf', size=2048):
        return SimpleUploadedFile(name, b'%PDF-1.4 ' + b'x' * size, content_type='application/pdf')

    def start(self, **extra):
        self.auth(self.teacher_token)
        data = {'file': self.upload(), 'topic': 'Kvadrat tenglamalar', 'standard': 'uzbmb',
                'question_count': 10, 'course': self.course_id, **extra}
        return self.client.post('/api/v1/quizzes/ai-generate/', data, format='multipart')

    def sync(self):
        call_command('sync_ai_quizzes', stdout=StringIO())

    # ── yaratish ──────────────────────────────────────────────────────

    def test_start_returns_202_and_queues_a_job(self):
        resp = self.start()
        self.assertEqual(resp.status_code, 202, resp.content)
        body = resp.json()
        self.assertEqual((body['status'], body['standard'], body['question_count']), ('queued', 'uzbmb', 10))
        self.assertIsNone(body['quiz'])
        self.assertEqual(self.fake.calls, [])  # so'rov ichida xizmatga murojaat yo'q

    def test_disabled_without_service_url(self):
        with override_settings(TEST_CREATOR_URL=''):
            resp = self.start()
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(AiQuizJob.objects.count(), 0)

    def test_student_and_parent_cannot_start(self):
        for token in (self.child_token, self.parent_token):
            self.auth(token)
            resp = self.client.post('/api/v1/quizzes/ai-generate/', {
                'file': self.upload(), 'topic': 'X', 'standard': 'sat', 'course': self.course_id,
            }, format='multipart')
            self.assertEqual(resp.status_code, 403)

    def test_validation(self):
        self.assertEqual(self.start(file=self.upload('virus.exe')).status_code, 400)
        self.assertEqual(self.start(question_count=2).status_code, 400)
        self.assertEqual(self.start(question_count=200).status_code, 400)
        self.assertEqual(self.start(standard='toefl').status_code, 400)
        self.assertEqual(self.start(topic='  ').status_code, 400)
        self.assertEqual(self.start(course='', subject='').status_code, 400)  # guruh ham fan ham yo'q
        self.auth(self.teacher_token)
        no_file = self.client.post('/api/v1/quizzes/ai-generate/', {
            'topic': 'X', 'standard': 'sat', 'course': self.course_id}, format='multipart')
        self.assertEqual(no_file.status_code, 400)

    def test_subject_only_job_is_allowed(self):
        resp = self.start(course='', subject='math')
        self.assertEqual(resp.status_code, 202, resp.content)

    def test_foreign_course_rejected(self):
        from apps.accounts.tests import login, register
        register(self.client, 't2', 'teacher')
        other = login(self.client, 't2')
        self.auth(other)
        resp = self.client.post('/api/v1/quizzes/ai-generate/', {
            'file': self.upload(), 'topic': 'X', 'standard': 'sat', 'course': self.course_id,
        }, format='multipart')
        self.assertEqual(resp.status_code, 403)

    def test_active_job_limit(self):
        for _ in range(3):
            self.assertEqual(self.start().status_code, 202)
        resp = self.start()
        self.assertEqual(resp.status_code, 400)

    def test_daily_limit(self):
        for _ in range(10):
            self.assertEqual(self.start().status_code, 202)
            AiQuizJob.objects.update(status='done')
        self.assertEqual(self.start().status_code, 400)

    # ── yurgizish ─────────────────────────────────────────────────────

    def test_full_flow_creates_a_draft_quiz_and_notifies(self):
        job_id = self.start().json()['id']
        self.sync()  # queued -> processing -> (status done) -> generating -> done, bir siklda
        job = AiQuizJob.objects.get(pk=job_id)
        self.assertEqual(job.status, 'done', job.error)
        quiz = Quiz.objects.get(pk=job.quiz_id)
        self.assertEqual(quiz.status, Quiz.Status.DRAFT)
        self.assertEqual(str(quiz.course_id), str(self.course_id))
        self.assertEqual(quiz.questions.count(), 2)
        self.assertEqual(sorted(quiz.questions.values_list('points', flat=True)), [1, 2])
        self.assertFalse(job.source_file)  # material o'chirilgan
        # Xizmatga to'g'ri chaqiriqlar
        self.assertEqual(self.fake.blueprint_payload['standard_version_id'], 'ver-1')  # faol versiya
        self.assertEqual(self.fake.blueprint_payload['requested_total'], 10)
        self.assertEqual(self.fake.blueprint_payload['document_id'], 'doc-1')
        self.assertEqual(self.fake.upload_params['subject_id'], 'sub-math')
        note = Notification.objects.get(kind='ai_quiz_ready')
        self.assertEqual(note.link_id, str(quiz.id))

    def test_polling_waits_until_processing_is_done(self):
        self.fake.extraction = 'embedding'
        job_id = self.start().json()['id']
        self.sync()
        self.assertEqual(AiQuizJob.objects.get(pk=job_id).status, 'processing')
        self.sync()
        self.assertEqual(AiQuizJob.objects.get(pk=job_id).status, 'processing')
        self.assertEqual(self.fake.calls.count(('POST', '/documents')), 1)  # qayta yuklanmaydi
        self.fake.extraction = 'done'
        self.sync()
        self.assertEqual(AiQuizJob.objects.get(pk=job_id).status, 'done')

    def test_processing_failure_fails_the_job_with_reason(self):
        self.fake.extraction = 'failed'
        self.fake.extraction_error = 'skanerlangan PDF'
        job_id = self.start().json()['id']
        self.sync()
        job = AiQuizJob.objects.get(pk=job_id)
        self.assertEqual(job.status, 'failed')
        self.assertIn('skanerlangan', job.error)
        self.assertTrue(Notification.objects.filter(kind='ai_quiz_failed').exists())
        self.assertFalse(job.source_file)

    def test_service_rejecting_generation_is_a_permanent_failure(self):
        self.fake.generate_status = 400
        job_id = self.start().json()['id']
        self.sync()
        self.assertEqual(AiQuizJob.objects.get(pk=job_id).status, 'failed')

    def test_server_error_is_retried_next_cycle(self):
        self.fake.generate_status = 503
        job_id = self.start().json()['id']
        self.sync()
        self.assertEqual(AiQuizJob.objects.get(pk=job_id).status, 'generating')
        self.fake.generate_status = 200
        self.sync()
        job = AiQuizJob.objects.get(pk=job_id)
        self.assertEqual(job.status, 'done', job.error)
        self.assertEqual(Quiz.objects.filter(status='draft').count(), 1)

    def test_unreachable_service_waits_then_gives_up(self):
        job_id = self.start().json()['id']
        with patch('apps.quizzes.tc_client.requests.request', side_effect=requests.ConnectionError('down')):
            self.sync()
            self.assertEqual(AiQuizJob.objects.get(pk=job_id).status, 'queued')
            AiQuizJob.objects.filter(pk=job_id).update(created_at=timezone.now() - timedelta(minutes=46))
            self.sync()
        job = AiQuizJob.objects.get(pk=job_id)
        self.assertEqual(job.status, 'failed')
        self.assertIn('Vaqt tugadi', job.error)

    def test_empty_export_fails_with_helpful_message(self):
        self.fake.export = json.dumps({'title': 'x', 'questions': []}).encode()
        job_id = self.start().json()['id']
        self.sync()
        job = AiQuizJob.objects.get(pk=job_id)
        self.assertEqual(job.status, 'failed')
        self.assertIn('savol yaratilmadi', job.error)

    def test_garbage_export_fails(self):
        self.fake.export = b'<html>not json'
        job_id = self.start().json()['id']
        self.sync()
        self.assertEqual(AiQuizJob.objects.get(pk=job_id).status, 'failed')

    def test_service_account_is_registered_on_first_login(self):
        self.fake.registered = False
        job_id = self.start().json()['id']
        self.sync()
        self.assertEqual(AiQuizJob.objects.get(pk=job_id).status, 'done')
        self.assertIn(('POST', '/auth/register'), self.fake.calls)

    def test_expired_token_is_refreshed_once(self):
        tc_client._state['token'] = 'stale'
        original = self.fake.__call__
        seen = {'stale_used': False}

        def wrapper(method, url, **kwargs):
            if kwargs.get('headers', {}).get('Authorization') == 'Bearer stale':
                seen['stale_used'] = True
                return reply(401, {'detail': 'expired'})
            return original(method, url, **kwargs)

        with patch('apps.quizzes.tc_client.requests.request', side_effect=wrapper):
            job_id = self.start().json()['id']
            self.sync()
        self.assertTrue(seen['stale_used'])
        self.assertEqual(AiQuizJob.objects.get(pk=job_id).status, 'done')

    def test_command_is_noop_when_disabled(self):
        self.start()
        with override_settings(TEST_CREATOR_URL=''):
            self.sync()
        self.assertEqual(AiQuizJob.objects.get().status, 'queued')
        self.assertEqual(self.fake.calls, [])

    # ── ko'rish ───────────────────────────────────────────────────────

    def test_teacher_sees_only_own_jobs(self):
        job_id = self.start().json()['id']
        self.auth(self.teacher_token)
        listing = self.client.get('/api/v1/quizzes/ai-generate/').json()
        self.assertEqual([j['id'] for j in listing], [job_id])
        self.assertEqual(self.client.get(f'/api/v1/quizzes/ai-generate/{job_id}/').status_code, 200)

        from apps.accounts.tests import login, register
        register(self.client, 't3', 'teacher')
        self.auth(login(self.client, 't3'))
        self.assertEqual(self.client.get('/api/v1/quizzes/ai-generate/').json(), [])
        self.assertEqual(self.client.get(f'/api/v1/quizzes/ai-generate/{job_id}/').status_code, 404)

    def test_finished_job_exposes_the_draft_quiz_id(self):
        job_id = self.start().json()['id']
        self.sync()
        self.auth(self.teacher_token)
        body = self.client.get(f'/api/v1/quizzes/ai-generate/{job_id}/').json()
        self.assertEqual(body['status'], 'done')
        quiz = self.client.get(f"/api/v1/quizzes/{body['quiz']}/").json()
        self.assertEqual(quiz['status'], 'draft')
