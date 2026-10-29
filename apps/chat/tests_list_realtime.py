"""Chat ro'yxati uchun realtime: `last_message.sender_id`, `typing.kind`, `chat_typing` va `chat_activity` (ws/notifications/)."""
from unittest.mock import patch

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.lessons.models import Course, Enrollment

from . import services
from .models import ChatRoom


def make(username, role, first_name=''):
    user = User(username=username, role=role, first_name=first_name)
    user.set_password('x')
    user.save()
    return user


class LastMessageSenderIdTests(TestCase):
    def test_sender_id_tells_apart_two_people_with_the_same_first_name(self):
        teacher = make('lm_t', User.Role.TEACHER, 'Aziza')
        student = make('lm_s', User.Role.STUDENT, 'Aziza')  # bir xil ism
        course = Course.objects.create(teacher=teacher, title='Algebra')
        services.ensure_course_room(course)
        Enrollment.objects.create(course=course, student=student, status=Enrollment.Status.APPROVED)
        room = course.chat_room
        services.send_message(user=teacher, room_id=room.id, text='Salom')

        def last(viewer):
            api = APIClient()
            api.force_authenticate(viewer)
            return api.get('/api/v1/chat/rooms/').json()['results'][0]['last_message']

        for viewer in (teacher, student):
            message = last(viewer)
            self.assertEqual((message['sender'], message['sender_id']), ('Aziza', str(teacher.id)))


class ChatListRealtimeTests(TransactionTestCase):
    """Consumer DB'ga alohida thread'dan kiradi — TransactionTestCase (chat/tests.py bilan bir xil)."""

    def setUp(self):
        cache.clear()
        self.teacher = make('rt_t', User.Role.TEACHER, 'Ustoz')
        self.student = make('rt_s', User.Role.STUDENT, 'Bobur')
        self.other = make('rt_o', User.Role.STUDENT, 'Sardor')
        self.course = Course.objects.create(teacher=self.teacher, title='Realtime')
        services.ensure_course_room(self.course)
        for student in (self.student, self.other):
            Enrollment.objects.create(course=self.course, student=student, status=Enrollment.Status.APPROVED)
        self.room = self.course.chat_room

    def socket(self, path, user):
        from root.asgi import application

        return WebsocketCommunicator(application, f'{path}?token={AccessToken.for_user(user)}')

    async def open(self, path, user):
        comm = self.socket(path, user)
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        return comm

    async def room_socket(self, user):
        return await self.open(f'/ws/chat/{self.room.id}/', user)

    async def notice_socket(self, user):
        return await self.open('/ws/notifications/', user)

    # ── typing.kind ──
    async def test_typing_kind_is_passed_on_and_defaults_to_text(self):
        teacher, student = await self.room_socket(self.teacher), await self.room_socket(self.student)
        for sent, expected in (({'type': 'typing', 'kind': 'voice'}, 'voice'), ({'type': 'typing'}, 'text'),
                               ({'type': 'typing', 'kind': 'zzz'}, 'text'), ({'type': 'typing', 'kind': 'text'}, 'text')):
            await student.send_json_to(sent)
            event = await teacher.receive_json_from(timeout=3)
            self.assertEqual((event['type'], event['user_id'], event['kind']), ('typing', str(self.student.id), expected))
        await teacher.disconnect()
        await student.disconnect()

    # ── chat_typing (ws/notifications/) ──
    async def test_typing_reaches_members_who_have_the_room_closed_but_not_the_typist(self):
        student_room = await self.room_socket(self.student)
        teacher_notice = await self.notice_socket(self.teacher)
        other_notice = await self.notice_socket(self.other)
        student_notice = await self.notice_socket(self.student)
        await student_room.send_json_to({'type': 'typing', 'kind': 'voice'})
        for comm in (teacher_notice, other_notice):
            event = await comm.receive_json_from(timeout=3)
            self.assertEqual(event, {'type': 'chat_typing', 'room': str(self.room.id), 'user_id': str(self.student.id),
                                     'name': 'Bobur', 'kind': 'voice'})
        self.assertTrue(await student_notice.receive_nothing(timeout=0.4))  # yozayotganning o'ziga kelmaydi
        for comm in (student_room, teacher_notice, other_notice, student_notice):
            await comm.disconnect()

    async def test_typing_fanout_is_throttled_but_the_room_signal_is_not(self):
        teacher_room, student_room = await self.room_socket(self.teacher), await self.room_socket(self.student)
        teacher_notice = await self.notice_socket(self.teacher)
        for _ in range(3):
            await student_room.send_json_to({'type': 'typing'})
        for _ in range(3):  # xonaning o'zida hammasi keladi
            self.assertEqual((await teacher_room.receive_json_from(timeout=3))['type'], 'typing')
        self.assertEqual((await teacher_notice.receive_json_from(timeout=3))['type'], 'chat_typing')
        self.assertTrue(await teacher_notice.receive_nothing(timeout=0.4))  # ro'yxatga 2 soniyada bir marta
        for comm in (teacher_room, student_room, teacher_notice):
            await comm.disconnect()

    async def test_no_list_fanout_for_huge_groups(self):
        student_room = await self.room_socket(self.student)
        teacher_notice = await self.notice_socket(self.teacher)
        with patch('apps.chat.consumers.TYPING_FANOUT_MAX_MEMBERS', 2):  # 3 a'zo (o'qituvchi + 2 o'quvchi) > 2
            await student_room.send_json_to({'type': 'typing'})
            self.assertTrue(await teacher_notice.receive_nothing(timeout=0.5))
        await student_room.disconnect()
        await teacher_notice.disconnect()

    # ── chat_activity (ws/notifications/) ──
    async def test_new_message_reaches_every_member_including_the_sender_without_the_room_open(self):
        notices = {user: await self.notice_socket(user) for user in (self.teacher, self.student, self.other)}
        message = await database_sync_to_async(services.send_message)(user=self.teacher, room_id=self.room.id, text='Salom')
        for user, comm in notices.items():  # yuboruvchining o'ziga ham (boshqa qurilmalari uchun)
            event = await comm.receive_json_from(timeout=3)
            self.assertEqual((event['type'], event['room'], event['message_id'], event['sender_id']),
                             ('chat_activity', str(self.room.id), str(message.id), str(self.teacher.id)), user.username)
            self.assertIn('created_at', event)
        for comm in notices.values():
            await comm.disconnect()

    async def test_outsiders_do_not_get_chat_activity(self):
        stranger = await database_sync_to_async(make)('rt_x', User.Role.STUDENT)
        notice = await self.notice_socket(stranger)
        await database_sync_to_async(services.send_message)(user=self.teacher, room_id=self.room.id, text='Yopiq')
        self.assertTrue(await notice.receive_nothing(timeout=0.5))
        await notice.disconnect()

    async def test_direct_room_activity_goes_to_both_sides_only(self):
        direct = await database_sync_to_async(
            lambda: ChatRoom.objects.create(kind=ChatRoom.Kind.DIRECT, teacher=self.teacher, student=self.student)
        )()
        teacher = await self.notice_socket(self.teacher)
        student = await self.notice_socket(self.student)
        other = await self.notice_socket(self.other)
        await database_sync_to_async(services.send_message)(user=self.student, room_id=direct.id, text='Salom, ustoz')
        for comm in (teacher, student):
            self.assertEqual((await comm.receive_json_from(timeout=3))['room'], str(direct.id))
        self.assertTrue(await other.receive_nothing(timeout=0.4))
        for comm in (teacher, student, other):
            await comm.disconnect()
