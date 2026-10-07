"""Uy vazifasi mustahkamlash: fayl nomlari, qotib qolgan tekshiruvlar,
bildirishnomalar, yuk/suiiste'mol chegaralari, tasdiqlash validatsiyasi."""
import re
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import ParentChildLink, User
from apps.core import uploads
from apps.lessons.models import Course, Enrollment

from .models import Submission
from .tests import FAKE_RESULT, make, pdf_upload

GRADE = 'apps.homework.services.ai.grade_file'


class HomeworkBase(TestCase):
    """Soddalashtirilgan sozlash: o'qituvchi, o'quvchi (kursga yozilgan), ota-ona."""

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media, HOMEWORK_CHECK_ASYNC=False)
        override.enable()
        self.addCleanup(override.disable)

        self.teacher = make('t1', User.Role.TEACHER)
        self.student = make('s1', User.Role.STUDENT)
        self.parent = make('p1', User.Role.PARENT)
        ParentChildLink.objects.create(
            parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)
        self.course = Course.objects.create(
            teacher=self.teacher, title='Algebra · 7-sinf', subject=Course.Subject.MATH)
        Enrollment.objects.create(
            course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        self.client = APIClient()

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client

    def assignment(self, **extra):
        resp = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id), 'title': 'Kvadrat tenglamalar', **extra}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.data['id']

    def submit(self, assignment_id, upload=None, user=None):
        return self.api(user or self.student).post(
            f'/api/v1/homework/assignments/{assignment_id}/submit/', {'file': upload or pdf_upload()})


class UploadNameTests(SimpleTestCase):
    def test_names_are_random_keep_extension_and_date_folders(self):
        first = uploads.homework_submission_path(None, 'IMG_1234.JPG')
        second = uploads.homework_submission_path(None, 'IMG_1234.JPG')
        pattern = r'^homework/\d{4}/\d{2}/[0-9a-f]{32}\.jpg$'
        self.assertRegex(first, pattern)
        self.assertNotEqual(first, second)
        self.assertNotIn('IMG_1234', first)

    def test_other_folders(self):
        self.assertRegex(uploads.homework_task_path(None, 'Topshiriq.docx'),
                         r'^homework/tasks/\d{4}/\d{2}/[0-9a-f]{32}\.docx$')
        self.assertRegex(uploads.certificate_path(None, 'diplom.pdf'),
                         r'^certificates/\d{4}/\d{2}/[0-9a-f]{32}\.pdf$')

    def test_file_without_extension(self):
        self.assertRegex(uploads.certificate_path(None, 'diplom'), r'/[0-9a-f]{32}$')


class StoredFileNameTests(HomeworkBase):
    @patch(GRADE, return_value=FAKE_RESULT)
    def test_submission_is_stored_under_a_random_name_but_downloads_under_the_original(self, _):
        resp = self.submit(self.assignment(), pdf_upload('Ali_daftari.pdf'))
        self.assertEqual(resp.status_code, 201, resp.content)
        submission = Submission.objects.get()
        self.assertRegex(submission.file.name, r'^homework/\d{4}/\d{2}/[0-9a-f]{32}\.pdf$')
        self.assertEqual(submission.original_name, 'Ali_daftari.pdf')
        # API orqali yuklab olinganda asl nom qaytadi
        download = self.api(self.teacher).get(f'/api/v1/homework/submissions/{submission.id}/file/')
        self.assertEqual(download.status_code, 200)
        self.assertIn('Ali_daftari.pdf', download['Content-Disposition'])

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_same_name_twice_does_not_collide(self, _):
        assignment_id = self.assignment()
        self.submit(assignment_id, pdf_upload('vazifa.pdf'))
        self.submit(assignment_id, pdf_upload('vazifa.pdf'))
        names = set(Submission.objects.values_list('file', flat=True))
        self.assertEqual(len(names), 2)

    def test_assignment_attachment_is_stored_under_a_random_name(self):
        resp = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id), 'title': 'Word vazifa',
            'attachment': SimpleUploadedFile('topshiriq.docx', b'PK fake docx'),
        }, format='multipart')
        self.assertEqual(resp.status_code, 201, resp.content)
        from .models import Assignment
        stored = Assignment.objects.get().attachment.name
        self.assertRegex(stored, r'^homework/tasks/\d{4}/\d{2}/[0-9a-f]{32}\.docx$')
        self.assertEqual(resp.data['attachment_name'], 'topshiriq.docx')
        # o'quvchi API orqali asl nom bilan oladi
        download = self.api(self.student).get(f"/api/v1/homework/assignments/{resp.data['id']}/file/")
        self.assertEqual(download.status_code, 200)
        self.assertIn('topshiriq.docx', download['Content-Disposition'])


class CaddyConfigTests(SimpleTestCase):
    def test_homework_media_is_not_served_publicly(self):
        """`/media/homework/*` umumiy `/media/*` dan OLDIN yopilgan bo'lishi shart
        (Caddy birinchi mos handle'ni ishlatadi)."""
        from pathlib import Path

        text = (Path(__file__).resolve().parents[2] / 'deploy' / 'Caddyfile').read_text(encoding='utf-8')
        blocked = text.index('handle /media/homework/*')
        public = text.index('handle /media/* {')
        self.assertLess(blocked, public)
        self.assertRegex(text[blocked:public], r'respond 404')
        self.assertIsNotNone(re.search(r'handle /media/homework/\*\s*\{\s*respond 404', text))


class RecoverStuckChecksTests(HomeworkBase):
    def stuck(self, minutes_ago=30, attempts=1):
        from datetime import timedelta

        from django.utils import timezone

        submission = Submission.objects.create(
            assignment_id=self.assignment(), student=self.student, file=pdf_upload('x.pdf'),
            original_name='x.pdf', status=Submission.Status.CHECKING, check_attempts=attempts,
        )
        Submission.objects.filter(pk=submission.pk).update(
            updated_at=timezone.now() - timedelta(minutes=minutes_ago))
        return submission

    def run_recovery(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('recover_stuck_submissions', stdout=out)
        return out.getvalue()

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_stuck_submission_is_rechecked(self, grade):
        submission = self.stuck()
        self.assertIn('Qayta tekshirildi: 1', self.run_recovery())
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.PENDING_REVIEW)
        self.assertEqual(submission.check_attempts, 2)  # 1 (avvalgi) + 1 (shu tiklash urinishi)
        grade.assert_called_once()

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_recent_checks_are_left_alone(self, grade):
        submission = self.stuck(minutes_ago=3)
        self.assertIn('Qayta tekshirildi: 0', self.run_recovery())
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.CHECKING)
        grade.assert_not_called()

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_gives_up_after_max_attempts(self, grade):
        submission = self.stuck(attempts=3)
        self.assertIn("xatoga o'tkazildi: 1", self.run_recovery())
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.ERROR)
        self.assertIn('qayta tekshirish', submission.error)
        grade.assert_not_called()

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_finished_submissions_are_ignored(self, grade):
        submission = self.stuck()
        Submission.objects.filter(pk=submission.pk).update(status=Submission.Status.DONE)
        self.run_recovery()
        grade.assert_not_called()

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_teacher_recheck_resets_the_attempt_counter(self, _):
        submission = self.stuck(attempts=3)
        resp = self.api(self.teacher).post(f'/api/v1/homework/submissions/{submission.id}/recheck/')
        self.assertEqual(resp.status_code, 200, resp.content)
        submission.refresh_from_db()
        self.assertEqual(submission.check_attempts, 1)
        self.assertEqual(submission.status, Submission.Status.PENDING_REVIEW)

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_second_run_does_not_recheck_again(self, grade):
        self.stuck()
        self.run_recovery()
        self.run_recovery()
        grade.assert_called_once()


class HomeworkNotificationTests(HomeworkBase):
    def received(self, user, kind):
        from apps.notifications.models import NotificationRecipient

        return list(NotificationRecipient.objects.filter(user=user, notification__kind=kind)
                    .select_related('notification'))

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_teacher_is_told_when_a_submission_is_ready_for_review(self, _):
        resp = self.submit(self.assignment())
        rows = self.received(self.teacher, 'homework_pending_review')
        self.assertEqual(len(rows), 1)
        notification = rows[0].notification
        self.assertEqual(notification.link_type, 'submission')
        self.assertEqual(notification.link_id, resp.data['id'])
        self.assertIn('tekshirishga tayyor', notification.description)
        self.assertIn('Kvadrat tenglamalar', notification.description)
        # o'quvchiga hali hech narsa (natija tasdiqlanmagan)
        self.assertEqual(self.received(self.student, 'homework_reviewed'), [])

    @patch(GRADE, side_effect=RuntimeError('kvota tugadi'))
    def test_no_teacher_notification_when_the_ai_check_failed(self, _):
        self.submit(self.assignment())
        self.assertEqual(self.received(self.teacher, 'homework_pending_review'), [])

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_student_is_told_when_the_teacher_approves(self, _):
        submission_id = self.submit(self.assignment()).data['id']
        self.api(self.teacher).post(f'/api/v1/homework/submissions/{submission_id}/review/')
        rows = self.received(self.student, 'homework_reviewed')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].notification.link_id, submission_id)
        self.assertIn('natijasi tayyor', rows[0].notification.description)

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_notification_failure_never_breaks_the_check_or_review(self, _):
        assignment_id = self.assignment()
        with patch('apps.notifications.services.send_notification', side_effect=RuntimeError('boom')):
            resp = self.submit(assignment_id)
            self.assertEqual(resp.status_code, 201)
            self.assertEqual(resp.data['status'], 'pending_review')
            review = self.api(self.teacher).post(f"/api/v1/homework/submissions/{resp.data['id']}/review/")
            self.assertEqual(review.status_code, 200)


class RetryDelayTests(SimpleTestCase):
    def test_rate_limit_errors_wait_much_longer(self):
        from . import ai

        class RateLimited(Exception):
            code = 429

        self.assertEqual(ai.retry_delay(RateLimited('x'), 0), 15.0)
        self.assertEqual(ai.retry_delay(RateLimited('x'), 1), 30.0)
        self.assertEqual(ai.retry_delay(RuntimeError('RESOURCE_EXHAUSTED: quota'), 0), 15.0)
        self.assertEqual(ai.retry_delay(RuntimeError('429 Too Many Requests'), 0), 15.0)

    def test_other_errors_keep_the_short_delay(self):
        from . import ai

        self.assertEqual(ai.retry_delay(RuntimeError('connection reset'), 0), 1.5)
        self.assertEqual(ai.retry_delay(RuntimeError('connection reset'), 2), 4.5)


class ConcurrencyLimitTests(SimpleTestCase):
    def test_no_more_than_the_allowed_number_of_gemini_calls_run_at_once(self):
        import threading
        import time

        from . import services

        state = {'now': 0, 'max': 0}
        lock = threading.Lock()

        def slow_grade(*args, **kwargs):
            with lock:
                state['now'] += 1
                state['max'] = max(state['max'], state['now'])
            time.sleep(0.05)
            with lock:
                state['now'] -= 1
            return FAKE_RESULT

        with patch.object(services, '_ai_slots', threading.BoundedSemaphore(2)), \
                patch('apps.homework.services.ai.grade_file', side_effect=slow_grade):
            threads = [threading.Thread(target=services._grade_limited, args=('f.pdf',)) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertLessEqual(state['max'], 2)
        self.assertGreaterEqual(state['max'], 1)


class SubmitThrottleTests(HomeworkBase):
    @patch(GRADE, return_value=FAKE_RESULT)
    def test_per_assignment_hourly_limit(self, grade):
        from . import services

        assignment_id = self.assignment()
        for _n in range(services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR):
            self.assertEqual(self.submit(assignment_id).status_code, 201)
        blocked = self.submit(assignment_id)
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('file', blocked.json()['error']['details'])
        self.assertEqual(grade.call_count, services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR)  # Gemini'ga bormadi

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_overall_hourly_limit_across_assignments(self, _):
        from . import services

        sent = 0
        for _a in range(services.MAX_SUBMITS_PER_HOUR // services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR):
            assignment_id = self.assignment()
            for _n in range(services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR):
                self.assertEqual(self.submit(assignment_id).status_code, 201)
                sent += 1
        self.assertEqual(sent, services.MAX_SUBMITS_PER_HOUR)
        self.assertEqual(self.submit(self.assignment()).status_code, 400)

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_old_submissions_do_not_count(self, _):
        from datetime import timedelta

        from django.utils import timezone

        from . import services

        assignment_id = self.assignment()
        for _n in range(services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR):
            self.submit(assignment_id)
        Submission.objects.update(created_at=timezone.now() - timedelta(hours=2))
        self.assertEqual(self.submit(assignment_id).status_code, 201)

    @patch(GRADE, return_value=FAKE_RESULT)
    def test_other_students_are_not_affected(self, _):
        from . import services

        other = make('s9', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course, student=other, status=Enrollment.Status.APPROVED)
        assignment_id = self.assignment()
        for _n in range(services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR):
            self.submit(assignment_id)
        self.assertEqual(self.submit(assignment_id, user=other).status_code, 201)
