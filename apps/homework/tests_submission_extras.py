"""Topshirishda izoh va bir nechta fayl; AI tekshiruvni vazifa bo'yicha o'chirish; fayl hajmi va dars sanasi."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.lessons.models import Lesson

from .models import Submission
from .tests_hardening import HomeworkBase, pdf_upload


def png_upload(name='rasm.png'):
    return SimpleUploadedFile(name, b'\x89PNG\r\n\x1a\n' + b'0' * 200, content_type='image/png')


class SubmissionExtrasTests(HomeworkBase):
    def post(self, assignment_id, **data):
        return self.api(self.student).post(f'/api/v1/homework/assignments/{assignment_id}/submit/', data, format='multipart')

    def test_comment_is_saved_and_returned_to_the_teacher(self):
        resp = self.post(self.assignment(), file=pdf_upload(), comment='  Savol bor edi  ')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data['comment'], 'Savol bor edi')
        teacher_view = self.api(self.teacher).get(f"/api/v1/homework/submissions/{resp.data['id']}/").json()
        self.assertEqual(teacher_view['comment'], 'Savol bor edi')

    def test_several_files_are_stored_and_listed(self):
        resp = self.post(self.assignment(), files=[pdf_upload(), png_upload('a.png'), png_upload('b.png')])
        self.assertEqual(resp.status_code, 201, resp.content)
        files = resp.data['files']
        self.assertEqual([f['name'] for f in files][1:], ['a.png', 'b.png'])
        self.assertEqual(len(files), 3)
        self.assertTrue(all(f['size'] for f in files))
        self.assertEqual(files[1]['mime'], 'image/png')
        self.assertEqual(Submission.objects.get(pk=resp.data['id']).extra_files.count(), 2)

    def test_extra_file_can_be_downloaded_by_index(self):
        resp = self.post(self.assignment(), files=[pdf_upload(), png_upload('a.png')])
        url = f"/api/v1/homework/submissions/{resp.data['id']}/file/"
        first = self.api(self.teacher).get(url)
        second = self.api(self.teacher).get(url + '?index=1')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertIn('a.png', second['Content-Disposition'])
        self.assertEqual(self.api(self.teacher).get(url + '?index=9').status_code, 404)

    def test_more_than_five_files_rejected(self):
        resp = self.post(self.assignment(), files=[png_upload(f'{i}.png') for i in range(6)])
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Submission.objects.count(), 0)

    def test_every_file_is_validated(self):
        bad = SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream')
        resp = self.post(self.assignment(), files=[pdf_upload(), bad])
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Submission.objects.count(), 0)

    def test_single_file_keeps_working(self):
        resp = self.post(self.assignment(), file=pdf_upload())
        self.assertEqual((resp.status_code, len(resp.data['files'])), (201, 1))
        self.assertEqual(resp.data['comment'], '')


class AssignmentExtrasTests(HomeworkBase):
    def test_ai_check_defaults_true_and_can_be_switched_off(self):
        assignment_id = self.assignment()
        detail = self.api(self.teacher).get(f'/api/v1/homework/assignments/{assignment_id}/').json()
        self.assertTrue(detail['ai_check'])
        patched = self.api(self.teacher).patch(f'/api/v1/homework/assignments/{assignment_id}/', {'ai_check': False}, format='json')
        self.assertEqual(patched.status_code, 200, patched.content)
        self.assertFalse(patched.json()['ai_check'])

    def test_ai_check_off_skips_the_ai_even_when_configured(self):
        from unittest import mock

        assignment_id = self.assignment(ai_check=False)
        with mock.patch('apps.homework.services._start_ai_check') as ai:
            resp = self.submit(assignment_id)
        self.assertEqual(resp.status_code, 201)
        ai.assert_not_called()
        self.assertEqual(Submission.objects.get(pk=resp.data['id']).status, Submission.Status.PENDING_REVIEW)

    def test_ai_check_on_still_calls_the_ai(self):
        from unittest import mock

        with mock.patch('apps.homework.services._start_ai_check', return_value=True) as ai:
            self.submit(self.assignment())
        ai.assert_called_once()

    def test_attachment_size_and_lesson_start_are_returned(self):
        lesson = Lesson.objects.create(course=self.course, title='Present Perfect', starts_at=timezone.now(), status=Lesson.Status.FINISHED)
        resp = self.api(self.teacher).post('/api/v1/homework/assignments/', {
            'course_id': str(self.course.id), 'title': 'Fayli bor', 'lesson_id': str(lesson.id), 'attachment': pdf_upload('d.pdf'),
        }, format='multipart')
        self.assertEqual(resp.status_code, 201, resp.content)
        detail = self.api(self.student).get(f"/api/v1/homework/assignments/{resp.data['id']}/").json()
        self.assertGreater(detail['attachment_size'], 0)
        self.assertEqual(detail['lesson_title'], 'Present Perfect')
        self.assertIsNotNone(detail['lesson_starts_at'])

    def test_no_attachment_means_null_size_and_date(self):
        detail = self.api(self.student).get(f'/api/v1/homework/assignments/{self.assignment()}/').json()
        self.assertIsNone(detail['attachment_size'])
        self.assertIsNone(detail['lesson_starts_at'])
