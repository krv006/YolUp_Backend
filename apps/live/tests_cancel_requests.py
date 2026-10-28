"""O'quvchi mikrofon/kamera so'rovini bekor qiladi; REC belgisi uchun recording_active."""
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import CameraRequest, Course, Enrollment, Lesson, LessonRecording, MicRequest


class CancelRequestTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='cr_t', password='x', role=User.Role.TEACHER, is_approved=True)
        self.student = User.objects.create_user(username='cr_s', password='x', role=User.Role.STUDENT)
        self.other = User.objects.create_user(username='cr_o', password='x', role=User.Role.STUDENT)
        course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        for user in (self.student, self.other):
            Enrollment.objects.create(course=course, student=user, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(course=course, title='D', starts_at=timezone.now(), status=Lesson.Status.LIVE)
        self.api = APIClient()
        self.api.force_authenticate(self.student)

    def test_cancel_mic_request_removes_it_and_broadcasts(self):
        MicRequest.objects.create(lesson=self.lesson, student=self.student)
        MicRequest.objects.create(lesson=self.lesson, student=self.other)
        with mock.patch('apps.board.realtime._send') as send:
            response = self.api.delete(f'/api/v1/live/lesson/{self.lesson.id}/mic-request/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(list(MicRequest.objects.values_list('student__username', flat=True)), ['cr_o'])
        send.assert_called_once_with(self.lesson.id, {'type': 'mic_request_cancelled', 'student_id': str(self.student.id)})

    def test_cancel_is_idempotent_and_silent_when_nothing_to_cancel(self):
        with mock.patch('apps.board.realtime._send') as send:
            self.assertEqual(self.api.delete(f'/api/v1/live/lesson/{self.lesson.id}/mic-request/').status_code, 204)
        send.assert_not_called()

    def test_cancel_camera_request(self):
        CameraRequest.objects.create(lesson=self.lesson, student=self.student)
        with mock.patch('apps.board.realtime._send') as send:
            response = self.api.delete(f'/api/v1/live/lesson/{self.lesson.id}/camera-request/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(CameraRequest.objects.exists())
        self.assertEqual(send.call_args.args[1]['type'], 'camera_request_cancelled')

    def test_cannot_cancel_someone_elses_request(self):
        MicRequest.objects.create(lesson=self.lesson, student=self.other)
        self.api.delete(f'/api/v1/live/lesson/{self.lesson.id}/mic-request/')
        self.assertTrue(MicRequest.objects.filter(student=self.other).exists())


class RecordingActiveTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='ra_t', password='x', role=User.Role.TEACHER, is_approved=True)
        course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        self.live = Lesson.objects.create(course=course, title='Jonli', starts_at=timezone.now(), status=Lesson.Status.LIVE)
        self.quiet = Lesson.objects.create(course=course, title='Yozuvsiz', starts_at=timezone.now() + timedelta(hours=1), status=Lesson.Status.LIVE)
        self.api = APIClient()
        self.api.force_authenticate(self.teacher)

    def rows(self):
        return {row['title']: row for row in self.api.get('/api/v1/lessons/').json()['results']}

    def test_flag_follows_recording_state(self):
        started = timezone.now() - timedelta(minutes=3)
        LessonRecording.objects.create(lesson=self.live, status=LessonRecording.Status.RECORDING, audio_started_at=started)
        rows = self.rows()
        self.assertTrue(rows['Jonli']['recording_active'])
        self.assertIsNotNone(rows['Jonli']['recording_started_at'])
        self.assertFalse(rows['Yozuvsiz']['recording_active'])
        self.assertIsNone(rows['Yozuvsiz']['recording_started_at'])

    def test_finished_recording_is_not_active(self):
        LessonRecording.objects.create(lesson=self.live, status=LessonRecording.Status.COMPLETED)
        self.assertFalse(self.rows()['Jonli']['recording_active'])
