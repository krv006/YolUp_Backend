"""Bir so'rovda bir nechta dars qo'shish — Trello "dars yaratish qismda ... bir vaqtda bir qancha dars", 2026-11-10."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import Course, Lesson


def make(username, role):
    user = User(username=username, role=role, is_approved=True)
    user.set_password('x')
    user.save()
    return user


class BulkLessonTests(TestCase):
    def setUp(self):
        self.teacher = make('bl_t', User.Role.TEACHER)
        self.other = make('bl_o', User.Role.TEACHER)
        self.student = make('bl_s', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        self.client = APIClient()

    def post(self, payload, user=None):
        self.client.force_authenticate(user or self.teacher)
        return self.client.post('/api/v1/lessons/bulk/', payload, format='json')

    def item(self, days, hour=18, **extra):
        when = (timezone.now() + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
        return {'title': f'Dars {days}', 'starts_at': when.isoformat(), 'duration_min': 60, **extra}

    def test_several_different_lessons_are_created_at_once(self):
        resp = self.post({'course': str(self.course.id), 'lessons': [self.item(2), self.item(3, 10), self.item(9)]})
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data['count'], 3)
        self.assertEqual(Lesson.objects.filter(course=self.course).count(), 3)
        self.assertEqual({l['title'] for l in resp.data['lessons']}, {'Dars 2', 'Dars 3', 'Dars 9'})

    def test_one_bad_lesson_creates_nothing_and_names_its_index(self):
        past = self.item(-1)
        resp = self.post({'course': str(self.course.id), 'lessons': [self.item(2), past, self.item(3)]})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('1', resp.data['error']['details']['lessons'])  # xato 2-darsda (indeks 1)
        self.assertEqual(Lesson.objects.count(), 0)

    def test_empty_and_too_many_are_rejected(self):
        self.assertEqual(self.post({'course': str(self.course.id), 'lessons': []}).status_code, 400)
        many = [self.item(2, 8 + i % 10) for i in range(51)]
        self.assertEqual(self.post({'course': str(self.course.id), 'lessons': many}).status_code, 400)

    def test_cannot_add_lessons_to_someone_elses_group(self):
        resp = self.post({'course': str(self.course.id), 'lessons': [self.item(2)]}, user=self.other)
        self.assertIn(resp.status_code, (400, 403, 404))
        self.assertEqual(Lesson.objects.count(), 0)

    def test_students_cannot_use_it(self):
        resp = self.post({'course': str(self.course.id), 'lessons': [self.item(2)]}, user=self.student)
        self.assertEqual(resp.status_code, 403)

    def test_each_lesson_may_name_its_own_group(self):
        second = Course.objects.create(teacher=self.teacher, title='Geometriya')
        resp = self.post({'lessons': [
            self.item(2, course=str(self.course.id)), self.item(3, course=str(second.id)),
        ]})
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Lesson.objects.filter(course=second).count(), 1)
