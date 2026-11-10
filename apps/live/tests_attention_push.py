"""Diqqat tekshiruvi: vaqti kelganda server o'quvchining doska socketiga yuboradi (mijoz har 6 soniyada so'ramaydi)."""
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.chat import services as chat_services
from apps.lessons.models import AttentionCheck, Course, Enrollment, Lesson
from apps.lessons.tests_schedule_extras import ScheduleBase

from . import services


class PushDueAttentionTests(ScheduleBase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.live = self.lesson(status=Lesson.Status.LIVE)
        self.now = timezone.now()

    def check(self, seconds_ago, student=None, **extra):
        return AttentionCheck.objects.create(
            lesson=extra.pop('lesson', self.live), student=student or self.student,
            due_at=self.now - timedelta(seconds=seconds_ago), **extra,
        )

    def push(self, at=None):
        with patch('apps.board.realtime.broadcast_attention') as send:
            count = services.push_due_attention(now=at or self.now)
        return count, send

    def test_due_check_is_sent_once_to_that_student(self):
        check = self.check(1)
        count, send = self.push()
        self.assertEqual(count, 1)
        send.assert_called_once_with(self.live.id, self.student.id, check.id, check.due_at)
        count, send = self.push()        # shu soniyadagi ikkinchi chaqiruv — takror yuborilmaydi
        self.assertEqual(count, 0)
        send.assert_not_called()

    def test_second_push_after_six_seconds_if_unanswered(self):
        self.check(1)
        self.push()
        count, _send = self.push(self.now + timedelta(seconds=3))
        self.assertEqual(count, 0)
        count, _send = self.push(self.now + timedelta(seconds=7))
        self.assertEqual(count, 1)
        count, _send = self.push(self.now + timedelta(seconds=8))
        self.assertEqual(count, 0)       # ko'pi bilan 2 marta

    def test_not_due_answered_expired_or_finished_are_skipped(self):
        AttentionCheck.objects.create(lesson=self.live, student=self.student, due_at=self.now + timedelta(seconds=30))  # hali vaqti kelmagan
        self.check(2, answered_at=self.now)                                                                           # javob berilgan
        self.check(20, student=self.student2)                                                                         # oyna (15 s) tugagan
        finished = self.lesson(status=Lesson.Status.FINISHED)
        self.check(1, lesson=finished)                                                                                # dars tugagan
        count, send = self.push()
        self.assertEqual(count, 0)
        send.assert_not_called()

    def test_each_student_gets_only_their_own(self):
        mine = self.check(1, self.student)
        theirs = self.check(1, self.student2)
        _count, send = self.push()
        targets = {(call.args[1], call.args[2]) for call in send.call_args_list}
        self.assertEqual(targets, {(self.student.id, mine.id), (self.student2.id, theirs.id)})

    def test_cache_failure_does_not_break_the_cron(self):
        self.check(1)
        with patch('apps.live.services.cache.add', side_effect=RuntimeError('redis down')):
            self.assertEqual(services.push_due_attention(now=self.now), 0)

    def test_command_runs(self):
        from django.core.management import call_command

        self.check(1)
        with patch('apps.board.realtime.broadcast_attention') as send:
            call_command('push_attention')
        send.assert_called_once()


class AttentionSocketTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.teacher = User.objects.create_user(username='ap_t', password='x', role=User.Role.TEACHER, is_approved=True)
        self.student = User.objects.create_user(username='ap_s', password='x', role=User.Role.STUDENT)
        self.other = User.objects.create_user(username='ap_o', password='x', role=User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='AP', subject=Course.Subject.MATH)
        chat_services.ensure_course_room(self.course)
        for student in (self.student, self.other):
            Enrollment.objects.create(course=self.course, student=student, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(course=self.course, starts_at=timezone.now(), duration_min=45, status=Lesson.Status.LIVE)
        self.check = AttentionCheck.objects.create(lesson=self.lesson, student=self.student, due_at=timezone.now() - timedelta(seconds=1))

    def ws(self, user):
        from channels.testing import WebsocketCommunicator
        from rest_framework_simplejwt.tokens import AccessToken

        from root.asgi import application

        return WebsocketCommunicator(application, f'/ws/board/{self.lesson.id}/?token={AccessToken.for_user(user)}')

    async def test_only_the_target_student_receives_the_check(self):
        from channels.db import database_sync_to_async

        mine, theirs = self.ws(self.student), self.ws(self.other)
        await mine.connect()
        await theirs.connect()
        pushed = await database_sync_to_async(services.push_due_attention)()
        self.assertEqual(pushed, 1)
        event = await mine.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'attention')
        self.assertEqual(event['check']['id'], str(self.check.id))
        self.assertIn('due_at', event['check'])
        self.assertTrue(await theirs.receive_nothing(timeout=0.5))   # boshqa o'quvchi (va umuman guruh) ko'rmaydi
        await mine.disconnect()
        await theirs.disconnect()
