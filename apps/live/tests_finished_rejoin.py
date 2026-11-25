"""Tugagan darsga qayta kirishning oldini olish (Trello 84): token muddati qisqa + ochiq qolgan xonani yopuvchi cron."""
from datetime import timedelta
from unittest import mock
from unittest.mock import AsyncMock

import jwt
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment, Lesson
from apps.live import services


class TokenLifetimeTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='tl_t', password='x', role=User.Role.TEACHER, is_approved=True)
        self.course = Course.objects.create(teacher=self.teacher, title='K', subject='math')

    def ttl(self, starts_in, duration=60):
        lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now() + starts_in, duration_min=duration, status=Lesson.Status.SCHEDULED)
        client = APIClient()
        client.force_authenticate(self.teacher)
        response = client.post('/api/v1/live/token/', {'lesson_id': str(lesson.id)})
        self.assertEqual(response.status_code, 200, response.content)
        claims = jwt.decode(response.json()['token'], options={'verify_signature': False})
        return timedelta(seconds=claims['exp'] - claims['nbf'])

    def hours(self, delta):
        return delta.total_seconds() / 3600

    def test_regular_lesson_token_is_end_plus_two_hours_not_eight(self):
        self.assertAlmostEqual(self.hours(self.ttl(timedelta(minutes=0))), 3, delta=0.05)  # 1 soatlik dars + 2 soat

    def test_a_lesson_started_long_after_its_planned_end_still_gets_two_hours(self):
        self.assertAlmostEqual(self.hours(self.ttl(timedelta(days=-3))), 2, delta=0.05)

    def test_token_never_lives_longer_than_eight_hours(self):
        self.assertLessEqual(self.hours(self.ttl(timedelta(hours=2), duration=600)), 8.01)
        self.assertAlmostEqual(self.hours(self.ttl(timedelta(hours=2), duration=600)), 8, delta=0.05)


class CloseFinishedRoomsTests(TestCase):
    def setUp(self):
        teacher = User.objects.create_user(username='cf_t', password='x', role=User.Role.TEACHER, is_approved=True)
        course = Course.objects.create(teacher=teacher, title='K')

        def lesson(status):
            return Lesson.objects.create(course=course, starts_at=timezone.now(), status=status)
        self.finished, self.cancelled, self.live = (
            lesson(Lesson.Status.FINISHED), lesson(Lesson.Status.CANCELLED), lesson(Lesson.Status.LIVE))

    def rooms(self, *lessons, empty=()):
        def room(name, people):
            return type('Room', (), {'name': name, 'num_participants': people})()
        rooms = [room(item.room_name, 3) for item in lessons] + [room(name, 0) for name in empty]
        rooms.append(room('voice-abc', 5))  # dars xonasi emas — tegilmaydi
        return type('Result', (), {'rooms': rooms})()

    def run_command(self, result):
        with mock.patch.object(services, 'LiveKitAPI') as api, mock.patch.object(services, 'end_room') as end_room:
            api.return_value.room.list_rooms = AsyncMock(return_value=result)
            api.return_value.aclose = AsyncMock()
            call_command('close_finished_lesson_rooms')
        return [call.args[0].room_name for call in end_room.call_args_list]

    def test_only_finished_and_cancelled_lessons_with_people_in_them_are_closed(self):
        closed = self.run_command(self.rooms(self.finished, self.cancelled, self.live))
        self.assertCountEqual(closed, [self.finished.room_name, self.cancelled.room_name])  # jonli dars va voice tegilmadi

    def test_an_empty_room_is_left_alone(self):
        self.assertEqual(self.run_command(self.rooms(empty=[self.finished.room_name])), [])

    def test_livekit_down_does_not_crash_the_cron(self):
        with mock.patch.object(services, 'LiveKitAPI') as api, mock.patch.object(services, 'end_room') as end_room:
            api.return_value.room.list_rooms = AsyncMock(side_effect=RuntimeError('down'))
            api.return_value.aclose = AsyncMock()
            call_command('close_finished_lesson_rooms')
        end_room.assert_not_called()
