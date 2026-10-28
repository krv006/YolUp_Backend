"""Shaxsiy eslatmalar (dars va imtihon): qo'yish, bekor qilish, vaqti kelganda yuborish."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.exams.models import Exam
from apps.lessons import services
from apps.lessons.models import Course, Enrollment, Lesson, ReminderPref
from apps.notifications.models import NotificationRecipient


class ReminderTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='rm_t', password='x', role='teacher', is_approved=True)
        self.student = User.objects.create_user(username='rm_s', password='x', role='student', lesson_reminder_minutes=15)
        self.outsider = User.objects.create_user(username='rm_o', password='x', role='student')
        self.course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        Enrollment.objects.create(course=self.course, student=self.student, status='approved')
        self.now = timezone.now()
        self.lesson = Lesson.objects.create(course=self.course, title='Dars', starts_at=self.now + timedelta(hours=3), status='scheduled')
        self.api = APIClient()
        self.api.force_authenticate(self.student)

    def url(self):
        return f'/api/v1/lessons/{self.lesson.id}/reminder/'

    def test_set_shows_up_on_lesson_and_can_be_removed(self):
        response = self.api.post(self.url(), {'minutes_before': 60}, format='json')
        self.assertEqual((response.status_code, response.json()['minutes_before']), (200, 60))
        row = self.api.get(f'/api/v1/lessons/{self.lesson.id}/').json()
        self.assertEqual((row['has_reminder'], row['reminder_minutes']), (True, 60))
        self.assertEqual(self.api.delete(self.url()).status_code, 204)
        row = self.api.get(f'/api/v1/lessons/{self.lesson.id}/').json()
        self.assertEqual((row['has_reminder'], row['reminder_minutes']), (False, None))

    def test_default_minutes_come_from_user_setting_and_values_validated(self):
        self.assertEqual(self.api.post(self.url(), {}, format='json').json()['minutes_before'], 15)
        self.assertEqual(self.api.post(self.url(), {'minutes_before': 0}, format='json').status_code, 400)
        self.assertEqual(self.api.post(self.url(), {'minutes_before': 5000}, format='json').status_code, 400)
        self.assertEqual(self.api.post(self.url(), {'minutes_before': 'abc'}, format='json').status_code, 400)

    def test_cannot_set_on_invisible_or_started_lesson(self):
        other = APIClient()
        other.force_authenticate(self.outsider)
        self.assertEqual(other.post(self.url(), {}, format='json').status_code, 404)
        Lesson.objects.filter(pk=self.lesson.pk).update(status='live')
        self.assertEqual(self.api.post(self.url(), {}, format='json').status_code, 400)

    def test_personal_reminder_replaces_default_and_is_sent_once(self):
        ReminderPref.objects.create(user=self.student, kind='lesson', target_id=self.lesson.id, minutes_before=120)
        self.assertEqual(services.send_lesson_reminders(now=self.now + timedelta(minutes=30)), 0)  # 120 daqiqa hali kelmadi
        sent = services.send_lesson_reminders(now=self.now + timedelta(hours=1))
        self.assertGreaterEqual(sent, 1)
        notes = NotificationRecipient.objects.filter(user=self.student, notification__kind='lesson_reminder')
        self.assertEqual(notes.count(), 1)
        self.assertIn('120 daqiqadan', notes.first().notification.description)
        services.send_lesson_reminders(now=self.now + timedelta(hours=1, minutes=1))
        self.assertEqual(notes.count(), 1)  # takror yuborilmaydi

    def test_exam_reminder_flow(self):
        exam = Exam.objects.create(course=self.course, title='Mock', created_by=self.teacher, starts_at=self.now + timedelta(hours=5),
                                   ends_at=self.now + timedelta(hours=6))
        url = f'/api/v1/exams/{exam.id}/reminder/'
        self.assertEqual(self.api.post(url, {'minutes_before': 30}, format='json').status_code, 200)
        rows = self.api.get('/api/v1/exams/').json()
        self.assertEqual((rows[0]['has_reminder'], rows[0]['reminder_minutes']), (True, 30))
        self.assertEqual(services.send_personal_reminders(now=self.now + timedelta(hours=4, minutes=40)), 1)
        self.assertTrue(NotificationRecipient.objects.filter(user=self.student, notification__kind='exam_reminder').exists())
        self.assertEqual(self.api.delete(url).status_code, 204)
        self.assertFalse(ReminderPref.objects.filter(target_id=exam.id).exists())

    def test_past_targets_are_dropped(self):
        ReminderPref.objects.create(user=self.student, kind='lesson', target_id=self.lesson.id, minutes_before=10)
        services.send_personal_reminders(now=self.now + timedelta(days=1))
        self.assertFalse(ReminderPref.objects.exists())
