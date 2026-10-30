"""O'qituvchi darsni qo'lda yakunlasa, LiveKit xonasi ham yopiladi (2026-10-30: o'quvchi xonada qolib ketardi)."""
import time
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.lessons import services as lesson_services
from apps.lessons.models import Course, Lesson
from apps.live import services as live_services


class FinishLessonClosesTheRoomTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='fc_t', password='x', role=User.Role.TEACHER)
        course = Course.objects.create(teacher=self.teacher, title='Close')
        self.lesson = Lesson.objects.create(course=course, starts_at=timezone.now(), duration_min=45, status=Lesson.Status.LIVE)

    @override_settings(BACKGROUND_ASYNC=True)
    def test_the_room_is_closed_a_few_seconds_after_finishing_not_instantly(self):
        with mock.patch('threading.Timer') as timer:
            lesson_services.finish_lesson(teacher=self.teacher, lesson=self.lesson)
        timer.assert_called_once()
        delay, func = timer.call_args.args[:2]
        self.assertEqual((delay, func), (live_services.ROOM_CLOSE_DELAY_SECONDS, live_services.end_room))
        self.assertEqual(timer.call_args.kwargs['args'][0].room_name, self.lesson.room_name)
        timer.return_value.start.assert_called_once()
        self.assertTrue(timer.return_value.daemon)
        self.assertGreaterEqual(live_services.ROOM_CLOSE_DELAY_SECONDS, 3)  # o'qituvchi chiqib ulgurishi uchun

    @override_settings(BACKGROUND_ASYNC=False)
    def test_nothing_is_scheduled_when_background_work_is_off_as_in_tests(self):
        with mock.patch('threading.Timer') as timer:
            lesson_services.finish_lesson(teacher=self.teacher, lesson=self.lesson)
        timer.assert_not_called()

    @override_settings(BACKGROUND_ASYNC=True)
    def test_a_broken_scheduler_does_not_break_finishing(self):
        with mock.patch('threading.Timer', side_effect=RuntimeError('boom')):
            lesson_services.finish_lesson(teacher=self.teacher, lesson=self.lesson)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.status, Lesson.Status.FINISHED)

    def test_the_timer_really_calls_end_room_with_the_room_name(self):
        with mock.patch.object(live_services, 'end_room') as end_room:
            live_services.schedule_room_close('lesson-abc', delay=0.05)
            for _ in range(40):
                if end_room.called:
                    break
                time.sleep(0.05)
        end_room.assert_called_once()
        self.assertEqual(end_room.call_args.args[0].room_name, 'lesson-abc')
