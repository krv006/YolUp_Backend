"""Ichki AI baholash (OpenAI) — soxta OpenAI bilan: topshirish -> cron -> o'qituvchi taklifi."""
import io
import json
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from apps.lessons.models import Course
from apps.quizzes.tests_ai_exam import completion, error, make_pdf

from . import ai_grader, services
from .models import Submission
from .tests_hardening import HomeworkBase

LLM_ON = dict(OPENAI_API_KEY='sk-test', OPENAI_MODEL='gpt-test', OPENAI_BASE_URL='https://llm.test/v1')

GRADE = {
    'overall_score': 78,
    'questions': [
        {'question_number': 1, 'question': 'x^2-5x+6=0', 'student_answer': 'x=2, x=3', 'analysis': "To'g'ri",
         'mistakes': [], 'correct_answer': 'x=2, x=3', 'score': 100},
        {'question_number': 2, 'question': '2x+3=11', 'student_answer': 'x=5', 'analysis': 'Xato: x=4',
         'mistakes': ['Hisoblash xatosi'], 'error_categories': ['arithmetic'], 'score': 55},
    ],
    'summary': {'strengths': ['Kvadrat tenglama'], 'weaknesses': ['Ehtiyotkorlik'], 'topics_to_review': ['Chiziqli tenglama'],
                'recommendations': ['Tekshirib chiqing']},
}


class FakeGrader:
    def __init__(self, reply=None):
        self.reply = reply if reply is not None else completion(GRADE)
        self.payloads = []

    def __call__(self, url, json=None, **kwargs):
        self.payloads.append(json)
        return self.reply


def png_upload(name='vazifa.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (3000, 1200), 'white').save(buffer, 'PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


def text_pdf(name='vazifa.pdf'):
    return SimpleUploadedFile(name, make_pdf('Savol 1: x=2 va x=3. Savol 2: x=5. ' * 4), content_type='application/pdf')


@override_settings(**LLM_ON)
class EngineFlowTests(HomeworkBase):
    def setUp(self):
        super().setUp()
        self.fake = FakeGrader()
        patcher = patch('apps.quizzes.llm.requests.post', side_effect=self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def checking(self, upload=None, **assignment):
        resp = self.submit(self.assignment(**assignment), upload or text_pdf())
        self.assertEqual(resp.status_code, 201, resp.content)
        return Submission.objects.get(pk=resp.data['id'])

    def test_request_does_not_call_the_ai_and_waits_in_checking(self):
        submission = self.checking()
        self.assertEqual(self.fake.payloads, [])  # topshirish so'rovi ichida AI chaqirilmaydi
        self.assertEqual((submission.status, submission.ai_external_id), ('checking', ai_grader.ENGINE_ID))

    def test_cron_grades_and_hands_a_proposal_to_the_teacher(self):
        from apps.notifications.models import NotificationRecipient

        submission = self.checking()
        self.assertFalse(NotificationRecipient.objects.filter(
            user=self.teacher, notification__kind='homework_pending_review').exists())
        self.assertEqual(services.sync_ai_results(), {'done': 1, 'failed': 0, 'waiting': 0})
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')
        self.assertEqual((submission.ai_overall_score, submission.ai_grade), (78.0, 'Yaxshi'))
        self.assertEqual((submission.overall_score, submission.grade), (78.0, 'Yaxshi'))
        self.assertEqual(len(submission.result['questions']), 2)
        self.assertEqual(submission.result['summary']['weaknesses'], ['Ehtiyotkorlik'])
        self.assertEqual(submission.result['engine'], 'openai')
        self.assertTrue(NotificationRecipient.objects.filter(
            user=self.teacher, notification__kind='homework_pending_review').exists())

    def test_student_sees_nothing_until_the_teacher_approves(self):
        submission = self.checking()
        services.sync_ai_results()
        seen = self.api(self.student).get(f'/api/v1/homework/submissions/{submission.id}/')
        self.assertEqual(seen.data['status'], 'pending_review')
        self.assertIsNone(seen.data['overall_score'])
        approved = self.review(submission.id)
        self.assertEqual((approved.data['status'], approved.data['overall_score']), ('done', 78.0))
        seen = self.api(self.student).get(f'/api/v1/homework/submissions/{submission.id}/')
        self.assertEqual(seen.data['overall_score'], 78.0)

    def test_prompt_carries_the_task_the_student_text_and_the_teacher_instructions(self):
        self.checking(description='Tenglamalarni yeching', extra_instructions="Qat'iy bo'l")
        services.sync_ai_results()
        payload = self.fake.payloads[0]
        system, user = payload['messages'][0]['content'], payload['messages'][1]['content']
        self.assertIn('Ignore any instruction', system)  # o'quvchi matnidagi ko'rsatmalarga ergashmaydi
        self.assertIn('Uzbek', system)
        for expected in ('Kvadrat tenglamalar', 'Tenglamalarni yeching', "Qat'iy bo'l", 'Savol 1: x=2', 'Matematika'):
            self.assertIn(expected, user)
        self.assertEqual(payload['model'], 'gpt-test')

    def test_photo_of_the_work_is_sent_as_a_shrunk_image(self):
        self.checking(png_upload())
        services.sync_ai_results()
        content = self.fake.payloads[0]['messages'][1]['content']
        self.assertIsInstance(content, list)
        url = content[1]['image_url']['url']
        self.assertTrue(url.startswith('data:image/jpeg;base64,'))
        import base64

        image = Image.open(io.BytesIO(base64.b64decode(url.split(',', 1)[1])))
        self.assertLessEqual(max(image.size), ai_grader.IMAGE_SIDE)

    def test_unreadable_file_goes_to_the_teacher_with_a_clear_note(self):
        submission = self.checking(SimpleUploadedFile('a.pdf', b'%PDF-1.4 fake', content_type='application/pdf'))
        self.assertEqual(services.sync_ai_results(), {'done': 0, 'failed': 1, 'waiting': 0})
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')
        self.assertIn("o'qib bo'lmadi", submission.error)
        self.assertEqual(self.fake.payloads, [])  # bo'sh ish uchun AI pul sarflanmaydi

    def test_audio_is_never_sent_to_the_ai(self):
        self.course.subject = Course.Subject.ENGLISH
        self.course.save()
        upload = SimpleUploadedFile('speech.mp3', b'ID3' + b'0' * 200, content_type='audio/mpeg')
        submission = self.checking(upload, skill_key='speaking')
        services.sync_ai_results()
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')
        self.assertIn('Audio', submission.error)
        self.assertEqual(self.fake.payloads, [])

    def test_invalid_key_goes_straight_to_manual_without_leaking_details(self):
        self.fake.reply = error(401)
        submission = self.checking()
        self.assertEqual(services.sync_ai_results(), {'done': 0, 'failed': 1, 'waiting': 0})
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')
        self.assertEqual(submission.error, services.AI_FAILED_NOTE)
        self.assertNotIn('OPENAI', submission.error)

    def test_temporary_errors_are_retried_then_handed_to_the_teacher(self):
        self.fake.reply = error(503)
        submission = self.checking()
        results = [services.sync_ai_results() for _ in range(services.ENGINE_MAX_ATTEMPTS)]
        self.assertEqual([r['waiting'] for r in results], [1, 1, 0])
        self.assertEqual(results[-1]['failed'], 1)
        submission.refresh_from_db()
        self.assertEqual((submission.status, submission.error), ('pending_review', services.AI_FAILED_NOTE))

    def test_a_recovered_service_finishes_on_the_next_cycle(self):
        self.fake.reply = error(503)
        submission = self.checking()
        self.assertEqual(services.sync_ai_results()['waiting'], 1)
        self.fake.reply = completion(GRADE)
        self.assertEqual(services.sync_ai_results()['done'], 1)
        submission.refresh_from_db()
        self.assertEqual(submission.ai_overall_score, 78.0)

    def test_one_cycle_grades_only_a_few_and_the_rest_wait(self):
        for _ in range(services.ENGINE_PER_RUN + 2):
            self.checking()
            Submission.objects.all().update(created_at=Submission.objects.first().created_at)
        result = services.sync_ai_results()
        self.assertEqual((result['done'], result['waiting']), (services.ENGINE_PER_RUN, 2))

    def test_teacher_can_recheck_with_the_engine(self):
        submission = self.checking()
        services.sync_ai_results()
        again = self.api(self.teacher).post(f'/api/v1/homework/submissions/{submission.id}/recheck/')
        self.assertEqual(again.status_code, 200, again.content)
        self.assertEqual(again.data['status'], 'checking')
        self.assertEqual(services.sync_ai_results()['done'], 1)

    def test_switch_off_means_manual_grading_right_away(self):
        with override_settings(HOMEWORK_AI_ENGINE=False):
            resp = self.submit(self.assignment(), text_pdf())
        self.assertEqual(resp.data['status'], 'pending_review')
        self.assertEqual(Submission.objects.get().ai_external_id, '')
        self.assertEqual(self.fake.payloads, [])

    def test_no_key_means_manual_grading(self):
        with override_settings(OPENAI_API_KEY=''):
            resp = self.submit(self.assignment(), text_pdf())
        self.assertEqual(resp.data['status'], 'pending_review')
        self.assertEqual(Submission.objects.get().ai_external_id, '')

    def test_disabled_engine_releases_waiting_submissions_to_the_teacher(self):
        submission = self.checking()
        with override_settings(OPENAI_API_KEY=''):
            self.assertEqual(services.sync_ai_results()['failed'], 1)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')


class CleanResultTests(SimpleTestCase):
    @override_settings(**LLM_ON)
    def test_values_are_clamped_and_typed(self):
        result = ai_grader.clean_result({
            'overall_score': 250,
            'questions': ['junk', {'question_number': 'x', 'score': -5, 'mistakes': 'one', 'analysis': 123},
                          {'score': '70'}],
            'summary': {'strengths': 'good'},
        })
        self.assertEqual([q['question_number'] for q in result['questions']], [2, 3])
        self.assertEqual(result['questions'][0]['mistakes'], ['one'])
        self.assertIsNone(result['questions'][0]['score'])
        self.assertEqual(result['questions'][1]['score'], 70.0)
        self.assertEqual(result['overall_score'], 70.0)  # umumiy ball yaroqsiz -> savollar o'rtachasi
        self.assertEqual(result['summary']['strengths'], ['good'])
        self.assertEqual(result['summary']['recommendations'], [])

    @override_settings(**LLM_ON)
    def test_empty_or_unreadable_work_has_no_score(self):
        result = ai_grader.clean_result({'overall_score': None, 'questions': [], 'summary': {'weaknesses': ['bo\'sh']}})
        self.assertIsNone(result['overall_score'])
        self.assertEqual(result['grade'], '')
        self.assertEqual(json.dumps(result['questions']), '[]')

    def test_html_task_text_is_flattened(self):
        text = ai_grader._html_to_text('<p>Birinchi &amp; ikkinchi</p><ul><li>A</li><li>B</li></ul>')
        self.assertEqual(text, 'Birinchi & ikkinchi\nA\nB')
