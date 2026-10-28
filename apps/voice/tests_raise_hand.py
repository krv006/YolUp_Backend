"""Ovozli xonada qo'l ko'tarish."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment

from .models import VoiceRoom


class RaiseHandTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='vh_t', password='x', role='teacher', is_approved=True)
        self.student = User.objects.create_user(username='vh_s', password='x', role='student')
        self.student2 = User.objects.create_user(username='vh_s2', password='x', role='student')
        self.outsider = User.objects.create_user(username='vh_o', password='x', role='student')
        course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        for user in (self.student, self.student2):
            Enrollment.objects.create(course=course, student=user, status='approved')
        self.room = VoiceRoom.objects.create(course=course, created_by=self.teacher, status='live')
        self.url = f'/api/v1/voice-rooms/{self.room.id}/raise-hand/'

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_raise_list_allow_and_lower(self):
        self.assertEqual(self.api(self.student).post(self.url).status_code, 201)
        self.assertEqual(self.api(self.student).post(self.url).status_code, 201)  # takroriy chaqiruv dublikat yaratmaydi
        hands = self.api(self.teacher).get(self.url).json()
        self.assertEqual([(h['name'], h['status']) for h in hands], [('vh_s', 'raised')])
        allowed = self.api(self.teacher).post(f'{self.url}{self.student.id}/allow/').json()
        self.assertEqual(allowed[0]['status'], 'allowed')
        self.assertEqual(self.api(self.student).delete(self.url).status_code, 204)
        self.assertEqual(self.api(self.teacher).get(self.url).json(), [])

    def test_only_owner_sees_list_and_decides(self):
        self.api(self.student).post(self.url)
        self.assertEqual(self.api(self.student2).get(self.url).status_code, 403)
        self.assertEqual(self.api(self.student2).post(f'{self.url}{self.student.id}/allow/').status_code, 403)

    def test_outsider_and_ended_room_rejected(self):
        self.assertEqual(self.api(self.outsider).post(self.url).status_code, 403)
        VoiceRoom.objects.filter(pk=self.room.pk).update(status='ended')
        self.assertEqual(self.api(self.student).post(self.url).status_code, 400)

    def test_dismiss_removes_hand_and_unknown_is_404(self):
        self.api(self.student).post(self.url)
        self.assertEqual(self.api(self.teacher).post(f'{self.url}{self.student.id}/dismiss/').json(), [])
        self.assertEqual(self.api(self.teacher).post(f'{self.url}{self.student.id}/dismiss/').status_code, 404)
