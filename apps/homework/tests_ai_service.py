"""Tashqi AI-home-checker xizmati bilan integratsiya (HTTP so'rovlar soxta)."""
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import requests
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from . import ai_client
from .models import Submission
from .tests import pdf_upload
from .tests_hardening import HomeworkBase

AI_ON = dict(
    HOMEWORK_AI_URL='http://checker:8000', HOMEWORK_AI_ORG_KEY='hwck_test',
    HOMEWORK_AI_INTERNAL_KEY='internal-test', HOMEWORK_AI_GIVE_UP_MINUTES=15,
)
AI_RESULT = {
    'overall_score': 84, 'grade': 'Very Good',
    'questions': [{'question_number': 1, 'score': 84}], 'summary': {'strengths': ['yaxshi']},
}


def response(status=200, body=None):
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = body if body is not None else {}
    mock.text = str(body)
    return mock


class SubjectMappingTests(SimpleTestCase):
    def test_standard_subjects(self):
        self.assertEqual(ai_client.subject_fields('math', '')['subject_key'], 'math')
        self.assertEqual(ai_client.subject_fields('astronomy', '')['subject_key'], 'physics')
        self.assertEqual(ai_client.subject_fields('literature', '')['subject_key'], 'essay')

    def test_other_subjects_use_general_with_a_name(self):
        fields = ai_client.subject_fields('geography', '')
        self.assertEqual((fields['subject_key'], fields['custom_subject_name']), ('general', 'Geography'))

    def test_language_with_skill_uses_the_language_mode(self):
        fields = ai_client.subject_fields('english', 'speaking')
        self.assertEqual((fields['language_key'], fields['skill_key']), ('english', 'speaking'))

    def test_language_without_skill_falls_back_to_general(self):
        fields = ai_client.subject_fields('english', '')
        self.assertEqual((fields['language_key'], fields['skill_key']), ('', ''))
        self.assertEqual(fields['custom_subject_name'], 'English')

    def test_unsupported_language_uses_general(self):
        fields = ai_client.subject_fields('german', 'writing')
        self.assertEqual((fields['subject_key'], fields['language_key']), ('general', ''))

    def test_unknown_subject(self):
        self.assertEqual(ai_client.subject_fields('???', '')['subject_key'], 'general')


class DisabledByDefaultTests(HomeworkBase):
    def test_without_configuration_nothing_is_sent_and_the_teacher_grades_manually(self):
        with patch('apps.homework.ai_client.requests.post') as post:
            resp = self.submit(self.assignment())
        post.assert_not_called()
        self.assertEqual(resp.data['status'], 'pending_review')

    def test_enabled_needs_both_url_and_org_key(self):
        with override_settings(HOMEWORK_AI_URL='http://x', HOMEWORK_AI_ORG_KEY=''):
            self.assertFalse(ai_client.enabled())
        with override_settings(HOMEWORK_AI_URL='', HOMEWORK_AI_ORG_KEY='k'):
            self.assertFalse(ai_client.enabled())
        with override_settings(**AI_ON):
            self.assertTrue(ai_client.enabled())


@override_settings(**AI_ON)
class SubmitToServiceTests(HomeworkBase):
    def test_submission_is_sent_with_both_keys_and_the_right_fields(self):
        with patch('apps.homework.ai_client.requests.post', return_value=response(200, {'id': 'ext-1'})) as post:
            resp = self.submit(self.assignment())
        self.assertEqual(resp.status_code, 201)
        call = post.call_args
        self.assertEqual(call.args[0], 'http://checker:8000/submissions')
        self.assertEqual(call.kwargs['headers'], {
            'X-Organization-Api-Key': 'hwck_test', 'X-Internal-Api-Key': 'internal-test'})
        data = call.kwargs['data']
        self.assertEqual(data['subject_key'], 'math')
        self.assertEqual(data['external_submission_id'], resp.data['id'])
        self.assertEqual(data['teacher_external_id'], str(self.teacher.id))
        self.assertEqual(data['student_external_id'], str(self.student.id))
        self.assertEqual(call.kwargs['files']['file'][0], 'vazifa.pdf')
        submission = Submission.objects.get()
        self.assertEqual((submission.status, submission.ai_external_id), ('checking', 'ext-1'))

    def test_students_never_see_that_an_ai_is_working(self):
        with patch('apps.homework.ai_client.requests.post', return_value=response(200, {'id': 'ext-1'})):
            resp = self.submit(self.assignment())
        self.assertEqual(resp.data['status'], 'pending_review')  # `checking` o'quvchiga ko'rinmaydi
        self.assertIsNone(resp.data['overall_score'])
        teacher_view = self.api(self.teacher).get(f"/api/v1/homework/submissions/{resp.data['id']}/")
        self.assertEqual(teacher_view.data['status'], 'checking')

    def test_teacher_is_not_notified_until_the_ai_result_arrives(self):
        from apps.notifications.models import NotificationRecipient

        with patch('apps.homework.ai_client.requests.post', return_value=response(200, {'id': 'ext-1'})):
            self.submit(self.assignment())
        self.assertFalse(NotificationRecipient.objects.filter(
            user=self.teacher, notification__kind='homework_pending_review').exists())

    def test_service_down_falls_back_to_manual_grading(self):
        from apps.notifications.models import NotificationRecipient

        with patch('apps.homework.ai_client.requests.post', side_effect=requests.ConnectionError('down')):
            resp = self.submit(self.assignment())
        self.assertEqual(resp.status_code, 201)
        submission = Submission.objects.get()
        self.assertEqual(submission.status, 'pending_review')
        self.assertEqual(submission.ai_external_id, '')
        self.assertTrue(NotificationRecipient.objects.filter(
            user=self.teacher, notification__kind='homework_pending_review').exists())

    def test_service_errors_fall_back_to_manual_grading(self):
        for bad in (response(500, {'detail': 'boom'}), response(401, {}), response(200, {})):
            Submission.objects.all().delete()
            with patch('apps.homework.ai_client.requests.post', return_value=bad):
                resp = self.submit(self.assignment())
            self.assertEqual(resp.data['status'], 'pending_review')
            self.assertEqual(Submission.objects.get().ai_external_id, '')


@override_settings(**AI_ON)
class SyncResultsTests(HomeworkBase):
    def checking(self, external_id='ext-1'):
        with patch('apps.homework.ai_client.requests.post', return_value=response(200, {'id': external_id})):
            resp = self.submit(self.assignment())
        return Submission.objects.get(pk=resp.data['id'])

    def sync(self, payload=None, error=None):
        from . import services

        target = 'apps.homework.ai_client.requests.get'
        if error:
            with patch(target, side_effect=error):
                return services.sync_ai_results()
        with patch(target, return_value=response(200, payload)):
            return services.sync_ai_results()

    def test_ready_result_goes_to_the_teacher_prefilled(self):
        submission = self.checking()
        result = self.sync({'status': 'pending_review', 'ai_result': AI_RESULT})
        self.assertEqual(result, {'done': 1, 'failed': 0, 'waiting': 0})
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')
        self.assertEqual((submission.ai_overall_score, submission.ai_grade), (84.0, "Juda yaxshi"))
        self.assertEqual((submission.overall_score, submission.grade), (84.0, 'Juda yaxshi'))
        self.assertEqual(submission.result['questions'][0]['score'], 84)

    def test_teacher_can_approve_the_ai_proposal_without_typing_a_score(self):
        submission = self.checking()
        self.sync({'status': 'pending_review', 'ai_result': AI_RESULT})
        approved = self.review(submission.id)
        self.assertEqual(approved.status_code, 200, approved.content)
        self.assertEqual((approved.data['status'], approved.data['overall_score']), ('done', 84.0))

    def test_student_still_sees_nothing_until_approval(self):
        submission = self.checking()
        self.sync({'status': 'pending_review', 'ai_result': AI_RESULT})
        seen = self.api(self.student).get(f'/api/v1/homework/submissions/{submission.id}/')
        self.assertEqual((seen.data['status'], seen.data['overall_score'], seen.data['result']),
                         ('pending_review', None, None))

    def test_teacher_is_notified_when_the_result_arrives(self):
        from apps.notifications.models import NotificationRecipient

        self.checking()
        self.sync({'status': 'pending_review', 'ai_result': AI_RESULT})
        self.assertEqual(NotificationRecipient.objects.filter(
            user=self.teacher, notification__kind='homework_pending_review').count(), 1)

    def test_still_running_waits(self):
        submission = self.checking()
        self.assertEqual(self.sync({'status': 'pending_ai'}), {'done': 0, 'failed': 0, 'waiting': 1})
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'checking')

    def test_grading_failed_is_released_for_manual_grading(self):
        submission = self.checking()
        self.assertEqual(self.sync({'status': 'grading_failed'})['failed'], 1)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')
        self.assertIn("o'zingiz baholang", submission.error)

    def test_unreachable_service_keeps_waiting_then_gives_up(self):
        submission = self.checking()
        self.assertEqual(self.sync(error=requests.ConnectionError('x'))['waiting'], 1)
        Submission.objects.filter(pk=submission.pk).update(updated_at=timezone.now() - timedelta(minutes=30))
        self.assertEqual(self.sync(error=requests.ConnectionError('x'))['failed'], 1)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')

    def test_a_submission_that_never_finishes_is_released(self):
        submission = self.checking()
        Submission.objects.filter(pk=submission.pk).update(updated_at=timezone.now() - timedelta(minutes=30))
        self.assertEqual(self.sync({'status': 'pending_ai'})['failed'], 1)

    def test_bad_scores_from_the_service_are_not_trusted(self):
        for bad in (150, -5, 'abc', None):
            Submission.objects.all().delete()
            submission = self.checking()
            self.sync({'status': 'pending_review', 'ai_result': {**AI_RESULT, 'overall_score': bad}})
            submission.refresh_from_db()
            self.assertIsNone(submission.overall_score, bad)
            # ball yo'q bo'lsa o'qituvchi uni o'zi kiritishi shart
            self.assertEqual(self.review(submission.id).status_code, 400)

    def test_missing_service_config_releases_for_manual_grading(self):
        submission = self.checking()
        with override_settings(HOMEWORK_AI_URL=''):
            from . import services

            self.assertEqual(services.sync_ai_results()['failed'], 1)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'pending_review')

    def test_management_command(self):
        self.checking()
        out = StringIO()
        with patch('apps.homework.ai_client.requests.get',
                   return_value=response(200, {'status': 'pending_review', 'ai_result': AI_RESULT})):
            call_command('sync_homework_ai', stdout=out)
        self.assertIn('tayyor 1', out.getvalue())
        out = StringIO()
        call_command('sync_homework_ai', stdout=out)  # endi hech narsa kutilmayapti
        self.assertEqual(out.getvalue(), '')


@override_settings(**AI_ON)
class RecheckTests(HomeworkBase):
    def finished(self):
        with patch('apps.homework.ai_client.requests.post', return_value=response(200, {'id': 'ext-1'})):
            resp = self.submit(self.assignment())
        from . import services

        with patch('apps.homework.ai_client.requests.get',
                   return_value=response(200, {'status': 'pending_review', 'ai_result': AI_RESULT})):
            services.sync_ai_results()
        return resp.data['id']

    def recheck(self, submission_id, user=None):
        return self.api(user or self.teacher).post(f'/api/v1/homework/submissions/{submission_id}/recheck/')

    def test_teacher_can_rerun_the_ai_with_a_fresh_external_id(self):
        submission_id = self.finished()
        with patch('apps.homework.ai_client.requests.post', return_value=response(200, {'id': 'ext-2'})) as post:
            resp = self.recheck(submission_id)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data['status'], 'checking')
        self.assertTrue(post.call_args.kwargs['data']['external_submission_id'].endswith('-r1'))
        self.assertEqual(Submission.objects.get().ai_external_id, 'ext-2')

    def test_students_cannot_recheck_and_running_or_approved_cannot_be_rechecked(self):
        submission_id = self.finished()
        self.assertEqual(self.recheck(submission_id, self.student).status_code, 403)
        Submission.objects.update(status='checking')
        self.assertEqual(self.recheck(submission_id).status_code, 400)
        Submission.objects.update(status='done')
        self.assertEqual(self.recheck(submission_id).status_code, 400)

    def test_recheck_when_the_service_is_down_is_a_clear_error(self):
        submission_id = self.finished()
        with patch('apps.homework.ai_client.requests.post', side_effect=requests.ConnectionError('down')):
            resp = self.recheck(submission_id)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Submission.objects.get().status, 'pending_review')

    @override_settings(HOMEWORK_AI_URL='')
    def test_recheck_without_the_service_explains_manual_grading(self):
        sub = Submission.objects.create(
            assignment_id=self.assignment(), student=self.student, file=pdf_upload('x.pdf'),
            original_name='x.pdf', status='pending_review')
        resp = self.recheck(sub.id)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("AI tekshiruv o'chirilgan", resp.json()['error']['details']['detail'])
