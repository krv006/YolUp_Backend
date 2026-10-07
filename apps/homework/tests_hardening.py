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
