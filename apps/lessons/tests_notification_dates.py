"""Bildirishnomalarda sana ham bor (faqat soat emas) — Trello "notification da xatolik", 2026-11-10."""
import re
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import ParentChildLink, User
from apps.lessons import services
from apps.lessons.models import Course, Enrollment, Lesson
from apps.notifications.models import Notification, NotificationRecipient

DATE_TIME = re.compile(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}')


def make(username, role):
    user = User(username=username, role=role, is_approved=True)
    user.set_password('x')
    user.save()
    return user


class NotificationDateTests(TestCase):
    def setUp(self):
        self.teacher = make('nd_t', User.Role.TEACHER)
        self.student = make('nd_s', User.Role.STUDENT)
        self.parent = make('nd_p', User.Role.PARENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        ParentChildLink.objects.create(parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)

    def texts(self, user, kind=None):
        qs = NotificationRecipient.objects.filter(user=user)
        if kind:
            qs = qs.filter(notification__kind=kind)
        return [r.notification.description for r in qs]

    def test_lesson_reminder_carries_the_date_and_time_of_the_lesson(self):
        starts = timezone.now() + timedelta(minutes=10)
        Lesson.objects.create(course=self.course, starts_at=starts, duration_min=60, status=Lesson.Status.SCHEDULED)
        services.send_lesson_reminders()
        text = self.texts(self.student, 'lesson_reminder')[0]
        self.assertIn('daqiqadan keyin boshlanadi', text)
        self.assertIn(timezone.localtime(starts).strftime('%d.%m.%Y %H:%M'), text)

    def test_attendance_notification_to_the_parent_has_a_date_not_only_a_clock(self):
        lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(), duration_min=60, status=Lesson.Status.LIVE, live_started_at=timezone.now(),
        )
        services.notify_parents_attendance(lesson=lesson, student=self.student, at=timezone.now())
        texts = self.texts(self.parent)
        self.assertTrue(texts)
        self.assertTrue(all(DATE_TIME.search(t) for t in texts), texts)
