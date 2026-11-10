"""Diqqat tekshiruvi jadvali: dars bo'ylab TENG yoyiladi (2 soat = 5 ta), kech kirganga siqilmaydi."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import AttentionCheck, Course, Enrollment, Lesson
from apps.live import services


class AttentionScheduleTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='as_t', password='x', role=User.Role.TEACHER, is_approved=True)
        self.s1 = User.objects.create_user(username='as_s1', password='x', role=User.Role.STUDENT)
        self.s2 = User.objects.create_user(username='as_s2', password='x', role=User.Role.STUDENT)
        self.outsider = User.objects.create_user(username='as_s3', password='x', role=User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        for s in (self.s1, self.s2):
            Enrollment.objects.create(course=self.course, student=s, status=Enrollment.Status.APPROVED)

    def make_lesson(self, *, minutes=120, started_ago=0, status=Lesson.Status.LIVE):
        now = timezone.now()
        return Lesson.objects.create(
            course=self.course, title='Dars', duration_min=minutes,
            starts_at=now - timedelta(minutes=started_ago),
            status=status,
            live_started_at=now - timedelta(minutes=started_ago) if status == Lesson.Status.LIVE else None,
        )

    def join(self, user, lesson):
        client = APIClient()
        client.force_authenticate(user)
        response = client.post('/api/v1/live/token/', {'lesson_id': str(lesson.id)})
        self.assertEqual(response.status_code, 200, response.content)

    def offsets(self, lesson, student):
        return [
            (c.due_at - lesson.live_started_at).total_seconds()
            for c in AttentionCheck.objects.filter(lesson=lesson, student=student).order_by('due_at')
        ]

    def test_two_hour_lesson_gets_five_evenly_spread_checks(self):
        lesson = self.make_lesson(minutes=120)
        # kirish paytiga ta'sir qilmasligi uchun jadvalni to'g'ridan-to'g'ri hisoblaymiz
        offsets = services._attention_offsets(lesson, lesson.live_started_at)
        self.assertEqual(len(offsets), 5)
        self.assertEqual(offsets, sorted(offsets))
        self.assertGreaterEqual(offsets[0], 120)
        self.assertLessEqual(offsets[-1], 120 * 60 - 120)
        gaps = [b - a for a, b in zip(offsets, offsets[1:])]
        # har bo'lak ~1392s, chetidan 15% padding => qo'shni tekshiruvlar orasi kamida ~417s
        self.assertTrue(all(g >= 400 for g in gaps), gaps)
        # birinchi tekshiruv dars boshida, oxirgisi oxirida to'planib qolmaydi
        self.assertLess(offsets[0], 30 * 60)
        self.assertGreater(offsets[-1], 90 * 60)

    def test_count_scales_with_duration(self):
        for minutes, expected in ((30, 3), (60, 3), (90, 4), (120, 5), (180, 8)):
            lesson = self.make_lesson(minutes=minutes)
            self.assertEqual(len(services._attention_offsets(lesson, lesson.live_started_at)), expected, minutes)

    def test_join_creates_full_schedule_for_student_who_joins_at_start(self):
        lesson = self.make_lesson(minutes=120)
        self.join(self.s1, lesson)
        self.assertEqual(len(self.offsets(lesson, self.s1)), 5)

    def test_all_students_get_same_times(self):
        lesson = self.make_lesson(minutes=120)
        self.join(self.s1, lesson)
        self.join(self.s2, lesson)
        self.assertEqual(self.offsets(lesson, self.s1), self.offsets(lesson, self.s2))

    def test_late_joiner_only_gets_remaining_checks_not_squeezed(self):
        lesson = self.make_lesson(minutes=120, started_ago=70)
        self.join(self.s1, lesson)
        full = services._attention_offsets(lesson, lesson.live_started_at)
        now_off = 70 * 60
        expected_remaining = [o for o in full if o >= now_off + 60]
        got = self.offsets(lesson, self.s1)
        self.assertEqual([int(g) for g in got], expected_remaining)
        self.assertLess(len(got), 5)

    def test_joining_before_teacher_starts_creates_nothing_then_schedule_follows_real_start(self):
        lesson = self.make_lesson(minutes=120, status=Lesson.Status.SCHEDULED)
        self.join(self.s1, lesson)
        self.assertEqual(AttentionCheck.objects.filter(lesson=lesson).count(), 0)
        # o'qituvchi keyin boshlaydi
        self.join(self.teacher, lesson)
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, Lesson.Status.LIVE)
        # o'quvchining polling'i jadvalni HAQIQIY boshlanishdan yaratadi
        services.pending_attention(user=self.s1, lesson_id=lesson.id)
        self.assertEqual(len(self.offsets(lesson, self.s1)), 5)

    def test_polling_does_not_duplicate_and_ignores_teacher_and_outsiders(self):
        lesson = self.make_lesson(minutes=120)
        for _ in range(3):
            services.pending_attention(user=self.s1, lesson_id=lesson.id)
        self.assertEqual(len(self.offsets(lesson, self.s1)), 5)
        services.pending_attention(user=self.teacher, lesson_id=lesson.id)
        services.pending_attention(user=self.outsider, lesson_id=lesson.id)
        self.assertEqual(AttentionCheck.objects.filter(lesson=lesson).exclude(student=self.s1).count(), 0)

    def test_check_becomes_pending_when_due(self):
        lesson = self.make_lesson(minutes=120)
        AttentionCheck.objects.create(lesson=lesson, student=self.s1, due_at=timezone.now() - timedelta(seconds=3))
        check = services.pending_attention(user=self.s1, lesson_id=lesson.id)
        self.assertIsNotNone(check)
