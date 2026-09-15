"""Chat oqimi testlari — guruh, direct so'rov/qabul/block, ruxsatlar, WebSocket."""
import io

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.chat.models import ChatRoom, Message
from apps.lessons.models import Course, Enrollment

from . import services


def make(username, role):
    u = User(username=username, role=role)
    u.set_password('x')
    u.save()
    return u


def make_image():
    buf = io.BytesIO()
    Image.new('RGB', (10, 10), 'blue').save(buf, format='PNG')
    buf.seek(0)
    return buf


class ChatFlowTests(TestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.student = make('s1', User.Role.STUDENT)
        self.stranger = make('s2', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        services.ensure_course_room(self.course)
        Enrollment.objects.create(
            course=self.course, student=self.student, status=Enrollment.Status.APPROVED,
        )
        self.client = APIClient()

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client

    def test_course_room_visible_to_members_only(self):
        r = self.api(self.teacher).get('/api/v1/chat/rooms/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        r = self.api(self.stranger).get('/api/v1/chat/rooms/')
        self.assertEqual(len(r.data['results']), 0)

    def test_send_and_read_group_message(self):
        room = self.course.chat_room
        r = self.api(self.student).post(f'/api/v1/chat/rooms/{room.id}/send/', {'text': 'Salom!'})
        self.assertEqual(r.status_code, 201)
        r = self.api(self.teacher).get(f'/api/v1/chat/rooms/{room.id}/messages/')
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]['text'], 'Salom!')

    def test_stranger_cannot_write_group(self):
        room = self.course.chat_room
        r = self.api(self.stranger).post(f'/api/v1/chat/rooms/{room.id}/send/', {'text': 'hey'})
        self.assertEqual(r.status_code, 403)

    def test_direct_request_flow(self):
        # so'rov -> pending, yozib bo'lmaydi
        r = self.api(self.student).post('/api/v1/chat/rooms/direct/request/', {'teacher': 't1'})
        self.assertEqual(r.status_code, 201)
        room_id = r.data['id']
        r = self.api(self.student).post(f'/api/v1/chat/rooms/{room_id}/send/', {'text': 'salom'})
        self.assertEqual(r.status_code, 403)
        # o'qituvchi qabul qildi -> yoziladi
        self.api(self.teacher).post(
            '/api/v1/chat/rooms/direct/respond/', {'room_id': room_id, 'action': 'accept'},
        )
        r = self.api(self.student).post(f'/api/v1/chat/rooms/{room_id}/send/', {'text': 'salom'})
        self.assertEqual(r.status_code, 201)
        # block -> yana yozib bo'lmaydi
        self.api(self.teacher).post(
            '/api/v1/chat/rooms/direct/respond/', {'room_id': room_id, 'action': 'block'},
        )
        r = self.api(self.student).post(f'/api/v1/chat/rooms/{room_id}/send/', {'text': 'salom'})
        self.assertEqual(r.status_code, 403)
        # qayta so'rov -> pending
        r = self.api(self.student).post('/api/v1/chat/rooms/direct/request/', {'teacher': 't1'})
        self.assertEqual(r.data['direct_status'], ChatRoom.DirectStatus.PENDING)

    def test_student_cannot_request_foreign_teacher(self):
        other = make('t2', User.Role.TEACHER)
        r = self.api(self.student).post('/api/v1/chat/rooms/direct/request/', {'teacher': other.username})
        self.assertEqual(r.status_code, 403)

    def test_parent_has_no_chat(self):
        parent = make('p1', User.Role.PARENT)
        r = self.api(parent).get('/api/v1/chat/rooms/')
        self.assertEqual(r.status_code, 403)

    def test_teacher_sets_group_image(self):
        room = self.course.chat_room
        r = self.api(self.teacher).post(
            f'/api/v1/chat/rooms/{room.id}/image/', {'image': make_image()}, format='multipart',
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('/media/group_images/', r.data['image'])

    def test_student_cannot_set_group_image(self):
        room = self.course.chat_room
        r = self.api(self.student).post(
            f'/api/v1/chat/rooms/{room.id}/image/', {'image': make_image()}, format='multipart',
        )
        self.assertEqual(r.status_code, 403)

    def test_live_lesson_shown_in_room_list(self):
        from django.utils import timezone

        from apps.lessons.models import Lesson

        lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(), duration_min=45,
        )
        r = self.api(self.student).get('/api/v1/chat/rooms/')
        self.assertIsNone(r.data['results'][0]['live_lesson'])

        self.api(self.teacher).post('/api/v1/live/token/', {'lesson_id': lesson.id})
        r = self.api(self.student).get('/api/v1/chat/rooms/')
        self.assertEqual(r.data['results'][0]['live_lesson']['id'], str(lesson.id))

        self.api(self.teacher).post(f'/api/v1/lessons/{lesson.id}/finish/')
        r = self.api(self.student).get('/api/v1/chat/rooms/')
        self.assertIsNone(r.data['results'][0]['live_lesson'])


class ChatWebSocketTests(TransactionTestCase):
    """WebSocket oqimi: JWT ulanish, ruxsat, xabar broadcast, typing.

    TransactionTestCase — consumer DB'ga alohida thread'dan kiradi
    (database_sync_to_async), oddiy TestCase tranzaksiyasi unga ko'rinmaydi.
    """

    def setUp(self):
        self.teacher = make('wt1', User.Role.TEACHER)
        self.student = make('ws1', User.Role.STUDENT)
        self.stranger = make('ws2', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='WS Algebra')
        services.ensure_course_room(self.course)
        Enrollment.objects.create(
            course=self.course, student=self.student, status=Enrollment.Status.APPROVED,
        )
        self.room = self.course.chat_room

    def ws(self, user):
        from rest_framework_simplejwt.tokens import AccessToken

        from root.asgi import application
        token = str(AccessToken.for_user(user))
        return WebsocketCommunicator(application, f'/ws/chat/{self.room.id}/?token={token}')

    async def _connect(self, user):
        comm = self.ws(user)
        connected, code = await comm.connect()
        return comm, connected, code

    async def test_member_connects_and_receives_broadcast(self):
        comm, connected, _ = await self._connect(self.student)
        self.assertTrue(connected)
        # REST/service orqali yuborilgan xabar WS'dan keladi
        await database_sync_to_async(services.send_message)(
            user=self.teacher, room_id=self.room.id, text='Salom WS!',
        )
        event = await comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'message')
        self.assertEqual(event['message']['text'], 'Salom WS!')
        self.assertEqual(event['message']['sender']['username'], 'wt1')
        await comm.disconnect()

    async def test_send_via_websocket(self):
        teacher_comm, _, _ = await self._connect(self.teacher)
        student_comm, _, _ = await self._connect(self.student)
        await student_comm.send_json_to({'type': 'message', 'text': 'WS orqali'})
        event = await teacher_comm.receive_json_from(timeout=3)
        self.assertEqual(event['message']['text'], 'WS orqali')
        # bazaga ham yozilgan
        count = await database_sync_to_async(
            lambda: Message.objects.filter(room=self.room, text='WS orqali').count()
        )()
        self.assertEqual(count, 1)
        await teacher_comm.disconnect()
        await student_comm.disconnect()

    async def test_typing_relayed(self):
        teacher_comm, _, _ = await self._connect(self.teacher)
        student_comm, _, _ = await self._connect(self.student)
        await student_comm.send_json_to({'type': 'typing'})
        event = await teacher_comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'typing')
        self.assertEqual(event['user_id'], str(self.student.id))
        await teacher_comm.disconnect()
        await student_comm.disconnect()

    async def test_stranger_rejected(self):
        comm, connected, _ = await self._connect(self.stranger)
        self.assertFalse(connected)
        await comm.disconnect()

    async def test_no_token_rejected(self):
        from root.asgi import application
        comm = WebsocketCommunicator(application, f'/ws/chat/{self.room.id}/')
        connected, _ = await comm.connect()
        self.assertFalse(connected)
        await comm.disconnect()

    async def test_lesson_live_and_ended_broadcast(self):
        from django.utils import timezone

        from apps.lessons import services as lesson_services
        from apps.lessons.models import Lesson
        from apps.live import services as live_services

        lesson = await database_sync_to_async(Lesson.objects.create)(
            course=self.course, starts_at=timezone.now(), duration_min=45,
        )
        comm, connected, _ = await self._connect(self.student)
        self.assertTrue(connected)

        await database_sync_to_async(live_services.issue_room_token)(
            user=self.teacher, lesson_id=lesson.id,
        )
        event = await comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'lesson_live')
        self.assertEqual(event['lesson']['id'], str(lesson.id))

        await database_sync_to_async(lesson_services.finish_lesson)(
            teacher=self.teacher, lesson=lesson,
        )
        event = await comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'lesson_ended')
        self.assertEqual(event['lesson_id'], str(lesson.id))
        await comm.disconnect()

    async def test_unenroll_closes_removed_students_socket(self):
        from apps.lessons import services as lesson_services

        student_comm, connected, _ = await self._connect(self.student)
        self.assertTrue(connected)
        teacher_comm, _, _ = await self._connect(self.teacher)

        await database_sync_to_async(lesson_services.unenroll)(
            course_id=self.course.id, by_user=self.teacher, student_id=self.student.id,
        )

        event = await student_comm.receive_json_from(timeout=3)
        self.assertEqual(event['type'], 'removed')
        closed = await student_comm.receive_output(timeout=3)
        self.assertEqual(closed['type'], 'websocket.close')

        # boshqalarga ta'sir qilmaydi — o'qituvchi ulanishda qolaveradi
        await database_sync_to_async(services.send_message)(
            user=self.teacher, room_id=self.room.id, text='Hali shu yerdaman',
        )
        event = await teacher_comm.receive_json_from(timeout=3)
        self.assertEqual(event['message']['text'], 'Hali shu yerdaman')
        await teacher_comm.disconnect()
