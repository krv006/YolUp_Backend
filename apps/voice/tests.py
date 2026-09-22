from datetime import timedelta
from unittest.mock import AsyncMock, patch

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.tests import login, register

from .models import VoiceRoom


class VoiceRoomTestBase(APITestCase):
    def setUp(self):
        register(self.client, 'v_teacher', 'teacher')
        self.teacher_token = login(self.client, 'v_teacher')
        self.auth(self.teacher_token)
        self.course_id = self.client.post(
            '/api/v1/courses/', {'title': 'Voice kurs', 'subject': 'math'},
        ).json()['id']

        register(self.client, 'v_student', 'student')
        self.student_token = login(self.client, 'v_student')
        register(self.client, 'v_student2', 'student')
        self.other_student_token = login(self.client, 'v_student2')
        self._enroll('v_student')
        self._enroll('v_student2')

        register(self.client, 'v_outsider', 'student')
        self.outsider_token = login(self.client, 'v_outsider')

    def _enroll(self, username):
        self.auth(self.student_token if username == 'v_student' else self.other_student_token)
        self.client.post(f'/api/v1/courses/{self.course_id}/enroll/', {})
        self.auth(self.teacher_token)
        for req in self.client.get('/api/v1/courses/requests/').json()['results']:
            self.client.post('/api/v1/courses/requests/respond/', {
                'enrollment_id': req['id'], 'action': 'approve',
            })

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def create_room(self, token, **extra):
        self.auth(token)
        payload = {'course': self.course_id}
        payload.update(extra)
        return self.client.post('/api/v1/voice-rooms/', payload, format='json')


class VoiceRoomFlowTests(VoiceRoomTestBase):
    def test_student_opens_open_room_and_other_student_joins_directly(self):
        resp = self.create_room(self.student_token)
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body['status'], 'live')
        self.assertEqual(body['access_mode'], 'open')
        room_id = body['id']

        self.auth(self.other_student_token)
        join = self.client.post(f'/api/v1/voice-rooms/{room_id}/join/')
        self.assertEqual(join.status_code, 200, join.content)
        self.assertIn('token', join.json())

    def test_outsider_cannot_create_or_join(self):
        resp = self.create_room(self.outsider_token)
        self.assertEqual(resp.status_code, 403)

        room_id = self.create_room(self.teacher_token).json()['id']
        self.auth(self.outsider_token)
        resp = self.client.post(f'/api/v1/voice-rooms/{room_id}/join/')
        self.assertEqual(resp.status_code, 403)

    def test_only_one_active_room_per_course(self):
        self.create_room(self.teacher_token)
        resp = self.create_room(self.student_token)
        self.assertEqual(resp.status_code, 400)

    def test_new_room_allowed_after_previous_one_closed(self):
        first = self.create_room(self.teacher_token).json()['id']
        self.client.post(f'/api/v1/voice-rooms/{first}/close/')
        resp = self.create_room(self.student_token)
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_room_auto_closes_when_last_participant_leaves(self):
        room_id = self.create_room(self.teacher_token).json()['id']
        self.auth(self.student_token)
        self.client.post(f'/api/v1/voice-rooms/{room_id}/join/')
        self.auth(self.teacher_token)
        self.client.post(f'/api/v1/voice-rooms/{room_id}/join/')

        self.auth(self.student_token)
        self.client.post(f'/api/v1/voice-rooms/{room_id}/leave/')
        self.assertEqual(VoiceRoom.objects.get(pk=room_id).status, 'live')

        self.auth(self.teacher_token)
        self.client.post(f'/api/v1/voice-rooms/{room_id}/leave/')
        room = VoiceRoom.objects.get(pk=room_id)
        self.assertEqual(room.status, 'ended')
        self.assertIsNotNone(room.ended_at)

    def test_invite_only_requires_request_and_approval(self):
        room_id = self.create_room(self.teacher_token, access_mode='invite_only').json()['id']

        self.auth(self.student_token)
        join = self.client.post(f'/api/v1/voice-rooms/{room_id}/join/')
        self.assertEqual(join.status_code, 403)

        req = self.client.post(f'/api/v1/voice-rooms/{room_id}/request-join/')
        self.assertEqual(req.status_code, 201, req.content)
        request_id = req.json()['id']

        # boshqa talaba so'rovlar ro'yxatini ko'ra olmaydi (faqat egasi/o'qituvchi)
        self.auth(self.other_student_token)
        self.assertEqual(self.client.get(f'/api/v1/voice-rooms/{room_id}/requests/').status_code, 403)

        self.auth(self.teacher_token)
        pending = self.client.get(f'/api/v1/voice-rooms/{room_id}/requests/').json()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['status'], 'pending')

        approve = self.client.post(f'/api/v1/voice-rooms/{room_id}/requests/{request_id}/approve/')
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.json()['status'], 'approved')

        self.auth(self.student_token)
        join = self.client.post(f'/api/v1/voice-rooms/{room_id}/join/')
        self.assertEqual(join.status_code, 200, join.content)

    def test_invite_only_denied_request_blocks_join(self):
        room_id = self.create_room(self.teacher_token, access_mode='invite_only').json()['id']
        self.auth(self.student_token)
        req_id = self.client.post(f'/api/v1/voice-rooms/{room_id}/request-join/').json()['id']

        self.auth(self.teacher_token)
        self.client.post(f'/api/v1/voice-rooms/{room_id}/requests/{req_id}/deny/')

        self.auth(self.student_token)
        join = self.client.post(f'/api/v1/voice-rooms/{room_id}/join/')
        self.assertEqual(join.status_code, 403)

    def test_teacher_always_has_access_to_student_opened_room(self):
        room_id = self.create_room(self.student_token, access_mode='invite_only').json()['id']
        self.auth(self.teacher_token)
        join = self.client.post(f'/api/v1/voice-rooms/{room_id}/join/')
        self.assertEqual(join.status_code, 200, join.content)

    def test_scheduled_room_blocks_join_before_time_for_non_moderators(self):
        room_id = self.create_room(
            self.teacher_token,
            scheduled_at=(timezone.now() + timedelta(hours=1)).isoformat(),
        ).json()['id']
        self.assertEqual(VoiceRoom.objects.get(pk=room_id).status, 'scheduled')

        self.auth(self.student_token)
        join = self.client.post(f'/api/v1/voice-rooms/{room_id}/join/')
        self.assertEqual(join.status_code, 400)

        self.auth(self.teacher_token)
        join = self.client.post(f'/api/v1/voice-rooms/{room_id}/join/')
        self.assertEqual(join.status_code, 200, join.content)
        self.assertEqual(VoiceRoom.objects.get(pk=room_id).status, 'live')

    def test_only_owner_or_teacher_can_close(self):
        room_id = self.create_room(self.student_token).json()['id']
        self.auth(self.other_student_token)
        resp = self.client.post(f'/api/v1/voice-rooms/{room_id}/close/')
        self.assertEqual(resp.status_code, 403)

    def test_list_scoped_to_own_courses(self):
        self.create_room(self.teacher_token)
        self.auth(self.outsider_token)
        rooms = self.client.get('/api/v1/voice-rooms/').json()['results']
        self.assertEqual(rooms, [])

        self.auth(self.student_token)
        rooms = self.client.get('/api/v1/voice-rooms/').json()['results']
        self.assertEqual(len(rooms), 1)


class CloseStaleVoiceRoomsCommandTests(VoiceRoomTestBase):
    def test_closes_room_with_no_real_livekit_participants(self):
        from django.core.management import call_command

        room_id = self.create_room(self.teacher_token).json()['id']
        # DB "live" deb hisoblaydi (hech kim leave chaqirmagan), lekin
        # LiveKit'da haqiqatda hech kim yo'q (masalan brauzer qulab tushgan).
        with patch('apps.voice.management.commands.close_stale_voice_rooms.LiveKitAPI') as mock_cls:
            mock_client = mock_cls.return_value
            mock_client.room.list_participants = AsyncMock(return_value=type('R', (), {'participants': []})())
            mock_client.aclose = AsyncMock()
            call_command('close_stale_voice_rooms')

        room = VoiceRoom.objects.get(pk=room_id)
        self.assertEqual(room.status, 'ended')

    def test_leaves_room_alone_when_livekit_still_has_participants(self):
        from django.core.management import call_command

        room_id = self.create_room(self.teacher_token).json()['id']
        with patch('apps.voice.management.commands.close_stale_voice_rooms.LiveKitAPI') as mock_cls:
            mock_client = mock_cls.return_value
            mock_client.room.list_participants = AsyncMock(
                return_value=type('R', (), {'participants': [object()]})(),
            )
            mock_client.aclose = AsyncMock()
            call_command('close_stale_voice_rooms')

        room = VoiceRoom.objects.get(pk=room_id)
        self.assertEqual(room.status, 'live')
