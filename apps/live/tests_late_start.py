"""Darsni kechikib/ertaroq boshlash (2026-11-07): o'qituvchi kuni o'tib ketgan, hali boshlanmagan darsni ham boshlay oladi;
o'quvchi esa o'qituvchi boshlagandan keyingina kira oladi. Kech boshlangan darsda diqqat tekshiruvlari baribir qo'yiladi."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.lessons.models import AttentionCheck, Attendance, Course, Enrollment, Lesson

PASSWORD = 'StrongPass123!'


def make(username, role):
    user = User(username=username, role=role)
    user.set_password(PASSWORD)
    user.save()
    return user


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class LateStartTests(APITestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.student = make('s1', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        self.now = timezone.now()

    def lesson(self, **extra):
        defaults = dict(course=self.course, starts_at=self.now - timedelta(days=2), duration_min=45, status=Lesson.Status.SCHEDULED)
        return Lesson.objects.create(**{**defaults, **extra})

    def token(self, user, lesson):
        return client_for(user).post('/api/v1/live/token/', {'lesson_id': str(lesson.pk)})

    def test_teacher_can_start_a_lesson_whose_day_has_passed(self):
        lesson = self.lesson()
        response = self.token(self.teacher, lesson)
        self.assertEqual(response.status_code, 200, response.content)
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, Lesson.Status.LIVE)
        self.assertIsNotNone(lesson.live_started_at)

    def test_student_cannot_join_a_past_day_lesson_before_the_teacher_starts_it(self):
        lesson = self.lesson()
        response = self.token(self.student, lesson)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Attendance.objects.filter(lesson=lesson).exists())  # soxta "kirdi" davomati yozilmaydi

    def test_student_can_join_once_the_teacher_started_the_late_lesson(self):
        lesson = self.lesson()
        self.assertEqual(self.token(self.teacher, lesson).status_code, 200)
        response = self.token(self.student, lesson)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(Attendance.objects.filter(lesson=lesson, student=self.student, joined_at__isnull=False).exists())

    def test_outsiders_and_finished_lessons_stay_blocked(self):
        stranger = make('boshqa', User.Role.TEACHER)
        self.assertEqual(self.token(stranger, self.lesson()).status_code, 403)
        done = self.lesson(status=Lesson.Status.FINISHED)
        self.assertEqual(self.token(self.teacher, done).status_code, 400)
        cancelled = self.lesson(status=Lesson.Status.CANCELLED)
        self.assertEqual(self.token(self.teacher, cancelled).status_code, 400)

    def test_early_start_of_a_future_lesson_still_works(self):
        lesson = self.lesson(starts_at=self.now + timedelta(days=1))
        self.assertEqual(self.token(self.teacher, lesson).status_code, 200)
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, Lesson.Status.LIVE)
        self.assertEqual(self.token(self.student, lesson).status_code, 200)

    def test_attention_checks_are_scheduled_for_a_late_started_lesson(self):
        """Dars 2 kun oldingi soatga rejalangan, lekin hozir boshlandi: tekshiruvlar HAQIQIY boshlanishdan hisoblanadi."""
        lesson = self.lesson(duration_min=60)
        self.assertEqual(self.token(self.teacher, lesson).status_code, 200)
        self.assertEqual(self.token(self.student, lesson).status_code, 200)
        checks = AttentionCheck.objects.filter(lesson=lesson, student=self.student)
        self.assertGreaterEqual(checks.count(), 3)
        for check in checks:
            self.assertGreater(check.due_at, self.now)
            self.assertLess(check.due_at, self.now + timedelta(minutes=61))
