"""Uy vazifasi (AI'siz): fayl nomlari, bildirishnomalar, topshirish chegaralari,
baholash validatsiyasi, eski holatlarni tuzatuvchi migratsiya."""
import importlib
import re
import shutil
import tempfile
from unittest.mock import patch

from django.apps import apps as django_apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import ParentChildLink, User
from apps.core import uploads
from apps.lessons.models import Course, Enrollment

from .models import Assignment, Submission
from .tests import make, pdf_upload


class HomeworkBase(TestCase):
    """Soddalashtirilgan sozlash: o'qituvchi, o'quvchi (kursga yozilgan), ota-ona."""

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media)
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

    def review(self, submission_id, payload=None):
        return self.api(self.teacher).post(
            f'/api/v1/homework/submissions/{submission_id}/review/', payload or {}, format='json')


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
    def test_submission_is_stored_under_a_random_name_but_downloads_under_the_original(self):
        resp = self.submit(self.assignment(), pdf_upload('Ali_daftari.pdf'))
        self.assertEqual(resp.status_code, 201, resp.content)
        submission = Submission.objects.get()
        self.assertRegex(submission.file.name, r'^homework/\d{4}/\d{2}/[0-9a-f]{32}\.pdf$')
        self.assertEqual(submission.original_name, 'Ali_daftari.pdf')
        download = self.api(self.teacher).get(f'/api/v1/homework/submissions/{submission.id}/file/')
        self.assertEqual(download.status_code, 200)
        self.assertIn('Ali_daftari.pdf', download['Content-Disposition'])

    def test_same_name_twice_does_not_collide(self):
        assignment_id = self.assignment()
        self.submit(assignment_id, pdf_upload('vazifa.pdf'))
        self.submit(assignment_id, pdf_upload('vazifa.pdf'))
        self.assertEqual(len(set(Submission.objects.values_list('file', flat=True))), 2)

    def test_assignment_attachment_is_stored_under_a_random_name(self):
        resp = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id), 'title': 'Word vazifa',
            'attachment': SimpleUploadedFile('topshiriq.docx', b'PK fake docx'),
        }, format='multipart')
        self.assertEqual(resp.status_code, 201, resp.content)
        stored = Assignment.objects.get().attachment.name
        self.assertRegex(stored, r'^homework/tasks/\d{4}/\d{2}/[0-9a-f]{32}\.docx$')
        self.assertEqual(resp.data['attachment_name'], 'topshiriq.docx')
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
        self.assertIsNotNone(re.search(r'handle /media/homework/\*\s*\{\s*respond 404', text))


class NoAiTests(HomeworkBase):
    def test_the_ai_modules_are_gone(self):
        for module in ('apps.homework.ai', 'apps.exams.writing', 'apps.exams.writing_ai'):
            with self.assertRaises(ModuleNotFoundError, msg=module):
                importlib.import_module(module)

    def test_no_gemini_settings_remain(self):
        from django.conf import settings

        self.assertFalse(hasattr(settings, 'GEMINI_API_KEY'))
        self.assertFalse(hasattr(settings, 'GEMINI_MODEL'))

    def test_submission_waits_for_the_teacher(self):
        resp = self.submit(self.assignment())
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['status'], 'pending_review')


class HomeworkNotificationTests(HomeworkBase):
    def received(self, user, kind):
        from apps.notifications.models import NotificationRecipient

        return list(NotificationRecipient.objects.filter(user=user, notification__kind=kind)
                    .select_related('notification'))

    def test_teacher_is_told_about_a_new_submission(self):
        resp = self.submit(self.assignment())
        rows = self.received(self.teacher, 'homework_pending_review')
        self.assertEqual(len(rows), 1)
        notification = rows[0].notification
        self.assertEqual(notification.link_type, 'submission')
        self.assertEqual(notification.link_id, resp.data['id'])
        self.assertIn('vazifani topshirdi', notification.description)
        self.assertIn('Baholashingiz kerak', notification.description)
        self.assertIn('Kvadrat tenglamalar', notification.description)
        self.assertEqual(self.received(self.student, 'homework_reviewed'), [])

    def test_student_is_told_when_the_teacher_grades(self):
        submission_id = self.submit(self.assignment()).data['id']
        self.review(submission_id, {'overall_score': 80})
        rows = self.received(self.student, 'homework_reviewed')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].notification.link_id, submission_id)
        self.assertIn('natijasi tayyor', rows[0].notification.description)

    def test_notification_failure_never_breaks_submitting_or_reviewing(self):
        assignment_id = self.assignment()
        with patch('apps.notifications.services.send_notification', side_effect=RuntimeError('boom')):
            resp = self.submit(assignment_id)
            self.assertEqual(resp.status_code, 201)
            self.assertEqual(resp.data['status'], 'pending_review')
            graded = self.review(resp.data['id'], {'overall_score': 70})
            self.assertEqual(graded.status_code, 200)


class SubmitThrottleTests(HomeworkBase):
    def test_per_assignment_hourly_limit(self):
        from . import services

        assignment_id = self.assignment()
        for _n in range(services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR):
            self.assertEqual(self.submit(assignment_id).status_code, 201)
        blocked = self.submit(assignment_id)
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('file', blocked.json()['error']['details'])

    def test_overall_hourly_limit_across_assignments(self):
        from . import services

        for _a in range(services.MAX_SUBMITS_PER_HOUR // services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR):
            assignment_id = self.assignment()
            for _n in range(services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR):
                self.assertEqual(self.submit(assignment_id).status_code, 201)
        self.assertEqual(self.submit(self.assignment()).status_code, 400)

    def test_old_submissions_do_not_count(self):
        from datetime import timedelta

        from django.utils import timezone

        from . import services

        assignment_id = self.assignment()
        for _n in range(services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR):
            self.submit(assignment_id)
        Submission.objects.update(created_at=timezone.now() - timedelta(hours=2))
        self.assertEqual(self.submit(assignment_id).status_code, 201)

    def test_other_students_are_not_affected(self):
        from . import services

        other = make('s9', User.Role.STUDENT)
        Enrollment.objects.create(course=self.course, student=other, status=Enrollment.Status.APPROVED)
        assignment_id = self.assignment()
        for _n in range(services.MAX_SUBMITS_PER_ASSIGNMENT_HOUR):
            self.submit(assignment_id)
        self.assertEqual(self.submit(assignment_id, user=other).status_code, 201)


class ReviewValidationTests(HomeworkBase):
    def pending(self):
        return self.submit(self.assignment()).data['id']

    def test_score_must_be_between_0_and_100(self):
        submission_id = self.pending()
        for bad in (101, -1, 1e9, 'nan', 'inf', 'abc'):
            resp = self.review(submission_id, {'overall_score': bad})
            self.assertEqual(resp.status_code, 400, bad)
            self.assertIn('overall_score', resp.json()['error']['details'], bad)
        self.assertEqual(Submission.objects.get().status, Submission.Status.PENDING_REVIEW)
        self.assertEqual(self.review(submission_id, {'overall_score': 100}).status_code, 200)

    def test_score_is_required(self):
        submission_id = self.pending()
        self.assertEqual(self.review(submission_id, {}).status_code, 400)
        self.assertEqual(self.review(submission_id, {'grade': "A'lo"}).status_code, 400)

    def test_result_must_be_an_object(self):
        submission_id = self.pending()
        self.assertEqual(self.review(submission_id, {'overall_score': 70, 'result': 'matn'}).status_code, 400)
        self.assertEqual(self.review(submission_id, {'overall_score': 70, 'result': ['x']}).status_code, 400)
        self.assertEqual(
            self.review(submission_id, {'overall_score': 70, 'result': {'summary': {}}}).status_code, 200)

    def test_grade_label_defaults_from_the_score_and_can_be_overridden(self):
        submission_id = self.pending()
        self.assertEqual(self.review(submission_id, {'overall_score': 95}).data['grade'], "A'lo")
        self.assertEqual(self.review(submission_id, {'overall_score': 40}).data['grade'],
                         'Jiddiy yaxshilash kerak')
        self.assertEqual(self.review(submission_id, {'overall_score': 40, 'grade': 'Ko\'rib chiqing'}).data['grade'],
                         "Ko'rib chiqing")

    def test_approved_result_can_be_corrected_and_student_is_told(self):
        from apps.notifications.models import NotificationRecipient

        submission_id = self.pending()
        self.review(submission_id, {'overall_score': 70})
        resp = self.review(submission_id, {'overall_score': 55, 'grade': 'Qoniqarli'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual((resp.data['overall_score'], resp.data['grade']), (55.0, 'Qoniqarli'))
        texts = list(NotificationRecipient.objects.filter(
            user=self.student, notification__kind='homework_reviewed',
        ).values_list('notification__description', flat=True))
        self.assertEqual(len(texts), 2)
        self.assertTrue(any('natijasi yangilandi' in t for t in texts))
        seen = self.api(self.student).get(f'/api/v1/homework/submissions/{submission_id}/')
        self.assertEqual(seen.data['overall_score'], 55.0)

    def test_checking_and_error_submissions_cannot_be_reviewed(self):
        submission_id = self.pending()
        for status in (Submission.Status.CHECKING, Submission.Status.ERROR):
            Submission.objects.filter(pk=submission_id).update(status=status)
            self.assertEqual(self.review(submission_id, {'overall_score': 70}).status_code, 400, status)

    def test_only_the_course_teacher_can_review(self):
        submission_id = self.pending()
        other = make('t9', User.Role.TEACHER)
        resp = self.api(other).post(f'/api/v1/homework/submissions/{submission_id}/review/', {'overall_score': 70},
                                    format='json')
        self.assertEqual(resp.status_code, 403)


class UnstickMigrationTests(HomeworkBase):
    def test_checking_and_error_submissions_become_pending_review(self):
        migration = importlib.import_module('apps.homework.migrations.0009_unstick_ai_statuses')
        assignment_id = self.assignment()
        ids = {}
        for status in ('checking', 'error', 'pending_review', 'done'):
            submission = Submission.objects.create(
                assignment_id=assignment_id, student=self.student, file=pdf_upload('x.pdf'),
                original_name='x.pdf', status=status, error='AI xato' if status == 'error' else '',
            )
            ids[status] = submission.pk
        migration.unstick(django_apps, None)
        statuses = {name: Submission.objects.get(pk=pk).status for name, pk in ids.items()}
        self.assertEqual(statuses, {
            'checking': 'pending_review', 'error': 'pending_review',
            'pending_review': 'pending_review', 'done': 'done',
        })
        self.assertEqual(Submission.objects.get(pk=ids['error']).error, '')
