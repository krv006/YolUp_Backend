"""Darslar ro'yxati: standart tartib YANGIDAN ESKIGA (Trello 83); `?ordering=starts_at` eskidan yangiga."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import Course, Lesson


class LessonListOrderTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='lo_t', password='x', role=User.Role.TEACHER, is_approved=True)
        course = Course.objects.create(teacher=self.teacher, title='K')
        now = timezone.now()
        self.ids = [
            str(Lesson.objects.create(course=course, title=f'D{day}', starts_at=now + timedelta(days=day)).id)
            for day in (-5, 3, -1, 10, 1)
        ]
        self.client = APIClient()
        self.client.force_authenticate(self.teacher)

    def titles(self, query=''):
        data = self.client.get(f'/api/v1/lessons/{query}').json()
        return [row['title'] for row in data.get('results', data)]

    def test_default_is_newest_first(self):
        self.assertEqual(self.titles(), ['D10', 'D3', 'D1', 'D-1', 'D-5'])

    def test_oldest_first_is_still_available(self):
        self.assertEqual(self.titles('?ordering=starts_at'), ['D-5', 'D-1', 'D1', 'D3', 'D10'])

    def test_first_page_holds_the_newest_lessons(self):
        data = self.client.get('/api/v1/lessons/?page_size=2').json()
        self.assertEqual([row['title'] for row in data['results']], ['D10', 'D3'])
