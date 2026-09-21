"""Dars eslatmasi foydalanuvchining ilova ichidagi inbox'ida API orqali ko'rinishi."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User

from . import services
from .models import Course, Enrollment, Lesson


class LessonReminderInboxApiTests(APITestCase):
    def setUp(self):
        def mk(username, role, minutes):
            user = User(username=username, role=role, lesson_reminder_minutes=minutes)
            user.set_password('x')
            user.save()
            return user

        self.teacher = mk('ri_t', User.Role.TEACHER, 10)
        self.student = mk('ri_s', User.Role.STUDENT, 15)
        course = Course.objects.create(teacher=self.teacher, title='Reminder kursi')
        Enrollment.objects.create(course=course, student=self.student, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(
            course=course, starts_at=timezone.now() + timedelta(minutes=10), duration_min=45,
        )

    def inbox(self, user):
        self.client.force_authenticate(user)
        return self.client.get('/api/v1/notifications/').json()['results']

    def test_reminder_visible_in_inbox_with_kind_and_unread_count(self):
        self.assertEqual(services.send_lesson_reminders(), 2)

        for user, minutes in ((self.student, 15), (self.teacher, 10)):
            items = self.inbox(user)
            self.assertEqual(len(items), 1)
            item = items[0]
            self.assertFalse(item['is_read'])
            note = item['notification']
            self.assertEqual(note['kind'], 'lesson_reminder')
            self.assertEqual(note['link_type'], 'lesson')
            self.assertEqual(note['link_id'], str(self.lesson.id))
            self.assertIn(f'{minutes} daqiqadan keyin', note['description'])
            self.assertEqual(self.client.get('/api/v1/notifications/unread-count/').json()['count'], 1)

    def test_marking_read_clears_unread_count(self):
        services.send_lesson_reminders()
        item = self.inbox(self.student)[0]
        self.assertEqual(self.client.post(f'/api/v1/notifications/{item["notification"]["id"]}/read/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/notifications/unread-count/').json()['count'], 0)
        self.assertTrue(self.inbox(self.student)[0]['is_read'])
