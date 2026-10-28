"""LiveKit tokeni: o'qituvchiga mikrofon/kamera/ekran ruxsati ANIQ yoziladi, o'quvchi yopiq boshlanadi."""
from datetime import timedelta

import jwt
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment, Lesson


class TokenGrantTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='tg_t', password='x', role=User.Role.TEACHER, is_approved=True)
        self.student = User.objects.create_user(username='tg_s', password='x', role=User.Role.STUDENT)
        course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        Enrollment.objects.create(course=course, student=self.student, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(
            course=course, title='Dars', starts_at=timezone.now() + timedelta(minutes=5), status=Lesson.Status.SCHEDULED,
        )

    def claims(self, user):
        client = APIClient()
        client.force_authenticate(user)
        response = client.post('/api/v1/live/token/', {'lesson_id': str(self.lesson.id)})
        self.assertEqual(response.status_code, 200, response.content)
        return jwt.decode(response.json()['token'], options={'verify_signature': False})['video']

    def test_teacher_token_lists_all_publish_sources(self):
        video = self.claims(self.teacher)
        self.assertTrue(video['canPublish'])
        self.assertEqual(
            sorted(video['canPublishSources']), ['camera', 'microphone', 'screen_share', 'screen_share_audio'],
        )

    def test_student_starts_with_no_publish_rights(self):
        video = self.claims(self.student)
        self.assertFalse(video.get('canPublish', False))
        self.assertEqual(video.get('canPublishSources', []), [])
