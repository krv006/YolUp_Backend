"""Doskaning joriy sahifasi: o'qituvchi turgan sahifa (chizsa yoki belgilasa), socket hodisasi."""
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.chat import services as chat_services
from apps.lessons.models import Course, Enrollment, Lesson

STROKE = {'type': 'pen', 'points': [[1, 1], [5, 5]], 'color': '#000000', 'width': 2}


class CurrentSheetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.teacher = User.objects.create_user(username='cs_t', password='x', role='teacher', is_approved=True)
        self.student = User.objects.create_user(username='cs_s', password='x', role='student')
        course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        chat_services.ensure_course_room(course)
        Enrollment.objects.create(course=course, student=self.student, status='approved')
        self.lesson = Lesson.objects.create(course=course, starts_at=timezone.now(), duration_min=45)
        self.t = APIClient()
        self.t.force_authenticate(self.teacher)
        self.s = APIClient()
        self.s.force_authenticate(self.student)
        for _ in range(2):
            self.t.post(f'/api/v1/board/{self.lesson.id}/sheet/', {}, format='json')  # birinchi chaqiruv 0-sahifani, ikkinchisi 1-sahifani yaratadi

    def board(self, client):
        return client.get(f'/api/v1/board/{self.lesson.id}/').json()

    def test_defaults_to_last_sheet(self):
        self.assertEqual(self.board(self.s)['current_sheet'], 1)

    def test_teacher_sets_current_sheet_and_students_see_it(self):
        with mock.patch('apps.board.realtime._send') as send:
            response = self.t.post(f'/api/v1/board/{self.lesson.id}/current-sheet/', {'sheet': 0}, format='json')
        self.assertEqual((response.status_code, response.json()['current_sheet']), (200, 0))
        send.assert_called_once_with(self.lesson.id, {'type': 'current_sheet', 'sheet': 0})
        self.assertEqual(self.board(self.s)['current_sheet'], 0)

    def test_same_value_is_not_broadcast_twice(self):
        self.t.post(f'/api/v1/board/{self.lesson.id}/current-sheet/', {'sheet': 1}, format='json')
        with mock.patch('apps.board.realtime._send') as send:
            self.t.post(f'/api/v1/board/{self.lesson.id}/current-sheet/', {'sheet': 1}, format='json')
        send.assert_not_called()

    def test_drawing_by_teacher_moves_current_sheet(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.t.post(f'/api/v1/board/{self.lesson.id}/stroke/', {'sheet': 0, 'stroke': STROKE}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.board(self.s)['current_sheet'], 0)

    def test_students_cannot_set_and_bad_values_rejected(self):
        self.assertEqual(self.s.post(f'/api/v1/board/{self.lesson.id}/current-sheet/', {'sheet': 0}, format='json').status_code, 403)
        self.assertEqual(self.t.post(f'/api/v1/board/{self.lesson.id}/current-sheet/', {'sheet': 99}, format='json').status_code, 400)
        self.assertEqual(self.t.post(f'/api/v1/board/{self.lesson.id}/current-sheet/', {'sheet': 'x'}, format='json').status_code, 400)
