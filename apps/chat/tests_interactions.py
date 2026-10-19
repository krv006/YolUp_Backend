"""Xabar bilan ishlash amallari (BACKEND_MESSAGE_INTERACTIONS.md): bir nechta qadash, uzatish manbasi, reaksiya
qo'shish/olish, o'qilganlik sinxronlash, @eslatish, ovozli xabar endpointi, `capabilities`, `{type, payload}` hodisalar."""
import uuid
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase

from apps.accounts.models import User
from apps.chat import services
from apps.chat.models import Message
from apps.lessons.models import Course, Enrollment
from apps.notifications.models import NotificationRecipient

from .tests import make
from .tests_v2 import ChatV2Base


class MultiplePinsTests(ChatV2Base):
    def pinned(self, user, room=None):
        room = room or self.room
        return self.api(user).get(f'{self.base}/rooms/{room.id}/pinned/')

    def test_several_messages_can_be_pinned_and_listed(self):
        first, second = self.send(self.student, 'bir'), self.send(self.student, 'ikki')
        url = f'{self.base}/rooms/{self.room.id}/pinned/'
        self.assertEqual(self.api(self.teacher).post(url, {'message_id': first['id']}, format='json').status_code, 200)
        resp = self.api(self.teacher).post(url, {'message_id': second['id']}, format='json')
        rows = resp.json()
        self.assertEqual([r['message_id'] for r in rows], [second['id'], first['id']])  # oxirgi qadalgan birinchi
        self.assertEqual((rows[0]['author_name'], rows[0]['text'], rows[0]['message_type']), ('s1', 'ikki', 'text'))
        self.assertTrue(rows[0]['pinned_at'])
        self.assertEqual(len(self.pinned(self.student).json()), 2)  # hamma a'zo ko'radi
        info = self.room_info(self.student)
        self.assertEqual([p['message_id'] for p in info['pinned_messages']], [second['id'], first['id']])
        self.assertEqual(info['pinned_message']['id'], second['id'])  # eski maydon = oxirgisi

    def test_pinning_twice_is_harmless_and_unpin_one(self):
        first, second = self.send(self.student, 'bir'), self.send(self.student, 'ikki')
        url = f'{self.base}/rooms/{self.room.id}/pinned/'
        for message in (first, first, second):
            self.api(self.teacher).post(url, {'message_id': message['id']}, format='json')
        self.assertEqual(len(self.pinned(self.teacher).json()), 2)
        resp = self.api(self.teacher).delete(f'{url}{first["id"]}/')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual([r['message_id'] for r in resp.json()], [second['id']])
        self.assertEqual(self.api(self.teacher).delete(f'{url}{first["id"]}/').status_code, 200)  # takror xato emas

    def test_only_the_teacher_pins_in_a_group_and_old_endpoint_still_works(self):
        message = self.send(self.student, 'Muhim')
        url = f'{self.base}/rooms/{self.room.id}/pinned/'
        self.assertEqual(self.api(self.student).post(url, {'message_id': message['id']}, format='json').status_code, 403)
        self.assertEqual(self.api(self.student).delete(f'{url}{message["id"]}/').status_code, 403)
        self.assertEqual(self.api(self.stranger).get(url).status_code, 403)
        # eski endpoint: POST pin/ qo'shadi, DELETE pin/ — eng oxirgisini oladi
        old = f'{self.base}/rooms/{self.room.id}/pin/'
        self.api(self.teacher).post(old, {'message_id': message['id']}, format='json')
        self.assertEqual(len(self.pinned(self.student).json()), 1)
        self.assertEqual(self.api(self.teacher).delete(old).status_code, 200)
        self.assertEqual(self.pinned(self.student).json(), [])

    def test_deleted_messages_leave_the_pins_and_the_cap_holds(self):
        sent = [self.send(self.student, f'm{i}') for i in range(3)]
        url = f'{self.base}/rooms/{self.room.id}/pinned/'
        for message in sent:
            self.api(self.teacher).post(url, {'message_id': message['id']}, format='json')
        self.api(self.teacher).delete(f'{self.base}/messages/{sent[0]["id"]}/?scope=everyone')
        self.assertEqual([r['message_id'] for r in self.pinned(self.teacher).json()], [sent[2]['id'], sent[1]['id']])
        with mock.patch.object(services, 'MAX_PINS', 2):
            extra = self.send(self.student, 'ortiqcha')
            resp = self.api(self.teacher).post(url, {'message_id': extra['id']}, format='json')
            self.assertEqual(resp.status_code, 400)

    def test_events_have_both_names(self):
        message = self.send(self.student, 'x')
        with mock.patch('apps.chat.realtime.broadcast_event') as broadcast, self.captureOnCommitCallbacks(execute=True):
            self.api(self.teacher).post(f'{self.base}/rooms/{self.room.id}/pinned/', {'message_id': message['id']}, format='json')
        events = {c.args[1]['type']: c.args[1] for c in broadcast.call_args_list}
        self.assertEqual(set(events), {'pinned', 'room_pinned_changed'})
        self.assertEqual(events['room_pinned_changed']['payload']['room_id'], str(self.room.id))


class EditAndDeleteEventTests(ChatV2Base):
    def test_edit_sends_message_edited(self):
        message = self.send(self.student, 'xato')
        with mock.patch('apps.chat.realtime.broadcast_event') as broadcast, self.captureOnCommitCallbacks(execute=True):
            self.api(self.student).patch(f'{self.base}/messages/{message["id"]}/', {'text': "to'g'ri"}, format='json')
        events = {c.args[1]['type']: c.args[1] for c in broadcast.call_args_list}
        payload = events['message_edited']['payload']
        self.assertEqual((payload['id'], payload['room_id'], payload['text']), (message['id'], str(self.room.id), "to'g'ri"))
        self.assertTrue(payload['edited_at'])
        self.assertIn('message_updated', events)

    def test_delete_for_me_only_notifies_my_own_devices(self):
        message = self.send(self.student, 'x')
        with mock.patch('apps.chat.realtime.broadcast_event') as room_events, \
                mock.patch('apps.chat.realtime.broadcast_user_event') as user_events, \
                self.captureOnCommitCallbacks(execute=True):
            self.api(self.teacher).delete(f'{self.base}/messages/{message["id"]}/?scope=me')
        room_events.assert_not_called()
        user_id, event = user_events.call_args.args
        self.assertEqual(user_id, self.teacher.id)
        self.assertEqual(
            (event['type'], event['payload']),
            ('messages_removed', {'room_id': str(self.room.id), 'message_ids': [message['id']], 'scope': 'me'}),
        )

    def test_bulk_delete_accepts_message_ids(self):
        sent = [self.send(self.student, f'm{i}') for i in range(60)]
        resp = self.api(self.student).post(
            f'{self.base}/messages/bulk-delete/', {'message_ids': [m['id'] for m in sent], 'scope': 'everyone'}, format='json',
        )
        self.assertEqual((resp.status_code, resp.json()['deleted']), (200, 60))
        self.assertEqual(self.messages(self.teacher).json(), [])


class ForwardTests(ChatV2Base):
    def test_forward_to_several_rooms_with_the_original_source(self):
        direct = self.direct_room()
        original = self.send(self.teacher, 'Ertaga imtihon')
        resp = self.api(self.teacher).post(
            f'{self.base}/messages/forward/',
            {'message_ids': [original['id']], 'target_room_ids': [str(direct.id), str(self.room.id)]}, format='json',
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        copies = resp.json()
        self.assertEqual({c['room'] for c in copies}, {str(direct.id), str(self.room.id)})
        for copy in copies:
            self.assertEqual(copy['text'], 'Ertaga imtihon')
            self.assertEqual(copy['forwarded_from'], {
                'message_id': original['id'], 'author_id': str(self.teacher.id), 'author_name': 't1',
                'room_id': str(self.room.id),
            })
            self.assertEqual(copy['forwarded_from_name'], 't1')  # eski maydon
        self.assertEqual(self.messages(self.student, room=direct).status_code, 200)

    def test_chain_keeps_the_first_author_and_plain_messages_have_none(self):
        direct = self.direct_room()
        original = self.send(self.student, 'asl')
        self.assertIsNone(original['forwarded_from'])
        first = self.api(self.teacher).post(
            f'{self.base}/messages/forward/', {'message_ids': [original['id']], 'target_room_ids': [str(direct.id)]}, format='json',
        ).json()[0]
        second = self.api(self.student).post(
            f'{self.base}/messages/forward/', {'message_ids': [first['id']], 'target_room_ids': [str(self.room.id)]}, format='json',
        ).json()[0]
        self.assertEqual(second['forwarded_from']['author_name'], 's1')
        self.assertEqual(second['forwarded_from']['message_id'], original['id'])
        self.assertEqual(second['forwarded_from']['room_id'], str(self.room.id))

    def test_all_or_nothing_across_rooms(self):
        direct = self.direct_room()
        original = self.send(self.teacher, 'x')
        resp = self.api(self.student2).post(
            f'{self.base}/messages/forward/',
            {'message_ids': [original['id']], 'target_room_ids': [str(self.room.id), str(direct.id)]}, format='json',
        )
        self.assertEqual(resp.status_code, 403)  # s3 direct chatga yoza olmaydi
        self.assertEqual(Message.objects.filter(forwarded_from_message__isnull=False).count(), 0)
        self.assertEqual(self.api(self.teacher).post(f'{self.base}/messages/forward/', {'message_ids': [original['id']], 'target_room_ids': []}, format='json').status_code, 400)
        eleven = [str(self.room.id)] + [str(uuid.uuid4()) for _ in range(10)]
        too_many = self.api(self.teacher).post(
            f'{self.base}/messages/forward/', {'message_ids': [original['id']], 'target_room_ids': eleven}, format='json',
        )
        self.assertEqual(too_many.status_code, 400)


class ReactionApiTests(ChatV2Base):
    def url(self, message):
        return f'{self.base}/messages/{message["id"]}/reactions/'

    def test_post_adds_idempotently_and_delete_removes(self):
        message = self.send(self.student, 'zo\'r')
        first = self.api(self.teacher).post(self.url(message), {'emoji': '👍'}, format='json')
        again = self.api(self.teacher).post(self.url(message), {'emoji': '👍'}, format='json')
        self.assertEqual((first.status_code, again.status_code), (200, 200))
        self.assertEqual(again.json()['reactions'], [{'emoji': '👍', 'count': 1, 'reacted': True}])
        removed = self.api(self.teacher).delete(self.url(message), {'emoji': '👍'}, format='json')
        self.assertEqual(removed.json()['reactions'], [])
        self.assertEqual(self.api(self.teacher).delete(self.url(message) + '?emoji=👍').status_code, 200)  # yo'q bo'lsa ham xato emas

    def test_repeated_add_sends_no_event_and_toggle_is_still_available(self):
        message = self.send(self.student, 'x')
        self.api(self.teacher).post(self.url(message), {'emoji': '🔥'}, format='json')
        with mock.patch('apps.chat.realtime.broadcast_event') as broadcast, self.captureOnCommitCallbacks(execute=True):
            self.api(self.teacher).post(self.url(message), {'emoji': '🔥'}, format='json')
        broadcast.assert_not_called()
        toggled = self.api(self.teacher).post(self.url(message), {'emoji': '🔥', 'toggle': True}, format='json')
        self.assertEqual(toggled.json()['reactions'], [])

    def test_event_carries_every_reaction_with_user_ids(self):
        message = self.send(self.student, 'x')
        self.api(self.student2).post(self.url(message), {'emoji': '🔥'}, format='json')
        with mock.patch('apps.chat.realtime.broadcast_event') as broadcast, self.captureOnCommitCallbacks(execute=True):
            self.api(self.teacher).post(self.url(message), {'emoji': '🔥'}, format='json')
        payload = {c.args[1]['type']: c.args[1] for c in broadcast.call_args_list}['message_reaction']['payload']
        self.assertEqual(payload['reactions'][0]['count'], 2)
        self.assertEqual(set(payload['reactions'][0]['user_ids']), {str(self.student2.id), str(self.teacher.id)})


class ReadSyncTests(ChatV2Base):
    def test_last_read_message_id_alias_and_room_field(self):
        first = self.send(self.student, 'bir')
        second = self.send(self.student, 'ikki')
        self.assertIsNone(self.room_info(self.teacher)['last_read_message_id'])
        resp = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/read/', {'last_read_message_id': first['id']}, format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        info = self.room_info(self.teacher)
        self.assertEqual((info['last_read_message_id'], info['unread_count']), (first['id'], 1))
        self.assertEqual(info['first_unread_message_id'], second['id'])
        self.api(self.teacher).post(f'{self.base}/rooms/{self.room.id}/read/', {'last_message_id': second['id']}, format='json')
        self.assertEqual(self.room_info(self.teacher)['last_read_message_id'], second['id'])

    def test_room_read_goes_to_the_readers_own_devices_only(self):
        sent = self.send(self.student, 'salom')
        with mock.patch('apps.chat.realtime.broadcast_event') as room_events, \
                mock.patch('apps.chat.realtime.broadcast_user_event') as user_events, \
                self.captureOnCommitCallbacks(execute=True):
            self.api(self.teacher).post(f'{self.base}/rooms/{self.room.id}/read/', {}, format='json')
        self.assertEqual(room_events.call_args.args[1]['type'], 'read')  # boshqalar uchun galochka
        user_id, event = user_events.call_args.args
        self.assertEqual(user_id, self.teacher.id)
        self.assertEqual(event, {'type': 'room_read', 'payload': {
            'room_id': str(self.room.id), 'user_id': str(self.teacher.id), 'last_read_message_id': sent['id'],
        }})


class MentionTests(ChatV2Base):
    def mention(self, user, text, ids, **extra):
        return self.api(user).post(
            f'{self.base}/rooms/{self.room.id}/send/', {'text': text, 'mentions': ids, **extra}, format='json',
        )

    def test_mentions_are_stored_returned_and_notified(self):
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.mention(self.teacher, '@s1 vazifani ko\'ring', [str(self.student.id), str(self.student2.id)])
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(set(body['mentions']), {str(self.student.id), str(self.student2.id)})
        self.assertEqual({u['name'] for u in body['mentioned_users']}, {'s1', 's3'})
        for student in (self.student, self.student2):
            inbox = NotificationRecipient.objects.filter(user=student, notification__kind='mention')
            self.assertEqual(inbox.count(), 1)
            notification = inbox.get().notification
            self.assertEqual((notification.link_type, notification.link_id), ('chat_room', str(self.room.id)))
            self.assertIn('Algebra', notification.description)
        history = self.messages(self.student, query='?mark_read=0').json()
        self.assertEqual(set(history[0]['mentions']), {str(self.student.id), str(self.student2.id)})

    def test_non_members_self_and_duplicates_are_dropped_and_bad_ids_refused(self):
        resp = self.mention(self.student, 'salom', [str(self.stranger.id), str(self.student.id), str(self.student2.id), str(self.student2.id)])
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()['mentions'], [str(self.student2.id)])
        self.assertFalse(NotificationRecipient.objects.filter(user=self.stranger).exists())
        self.assertEqual(self.mention(self.student, 'x', ['nope']).status_code, 400)
        self.assertEqual(self.mention(self.student, 'x', {'a': 1}).status_code, 400)
        many = [str(User.objects.create_user(username=f'u{i}', password='x').id) for i in range(21)]
        self.assertEqual(self.mention(self.teacher, 'x', many).status_code, 400)

    def test_has_unread_mention_flag(self):
        self.send(self.teacher, 'oddiy xabar')
        self.assertFalse(self.room_info(self.student)['has_unread_mention'])
        self.mention(self.teacher, '@s1', [str(self.student.id)])
        self.assertTrue(self.room_info(self.student)['has_unread_mention'])
        self.assertFalse(self.room_info(self.student2)['has_unread_mention'])
        self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/read/', {}, format='json')
        self.assertFalse(self.room_info(self.student)['has_unread_mention'])

    def test_mentions_work_in_multipart_and_a_failing_notification_does_not_break_sending(self):
        resp = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/send/',
            {'text': 'hamma', 'mentions': [str(self.student.id), str(self.student2.id)]}, format='multipart',
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(len(resp.json()['mentions']), 2)
        with mock.patch('apps.notifications.services.send_notification', side_effect=RuntimeError('boom')), \
                self.captureOnCommitCallbacks(execute=True):
            ok = self.mention(self.teacher, 'yana', [str(self.student.id)])
        self.assertEqual(ok.status_code, 201)

    def test_members_search_by_query(self):
        url = f'{self.base}/rooms/{self.room.id}/members/'
        User.objects.filter(pk=self.student.pk).update(first_name='Aziza', last_name='Rahimova')
        names = [r['name'] for r in self.api(self.teacher).get(url + '?query=azi').json()]
        self.assertEqual(names, ['Aziza Rahimova'])
        self.assertEqual([r['name'] for r in self.api(self.teacher).get(url + '?query=s3').json()], ['s3'])
        self.assertEqual(len(self.api(self.teacher).get(url).json()), 3)


class VoiceEndpointTests(ChatV2Base):
    def voice(self, name='ovoz.webm', content=b'0123456789' * 10, **extra):
        file = SimpleUploadedFile(name, content, content_type='application/octet-stream')
        return self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/voice/', {'file': file, **extra}, format='multipart')

    def test_voice_endpoint_with_milliseconds_and_attachment_object(self):
        resp = self.voice(duration_ms='24300', waveform='[3, 7, 12]')
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual((body['message_type'], body['duration']), ('voice', 25))  # soniyaga yuqoriga yaxlitlanadi
        self.assertEqual(body['attachment'], {
            'type': 'voice', 'url': body['file_url'], 'name': 'ovoz.webm', 'size': 100, 'mime': 'audio/webm',
            'page_count': None, 'duration_ms': 25000, 'waveform': [3, 7, 12],
        })

    def test_formats_and_limits(self):
        self.assertEqual(self.voice(name='safari.mp4', duration_ms='3000').status_code, 201)  # Safari: audio/mp4
        self.assertEqual(self.voice(name='x.m4a', duration_ms='3000').status_code, 201)
        self.assertEqual(self.voice(duration_ms='0').status_code, 400)
        self.assertEqual(self.voice().status_code, 400)  # davomiylik shart
        self.assertEqual(self.voice(duration_ms='300001').status_code, 400)  # 5 daqiqadan uzun
        self.assertEqual(self.voice(duration_ms='300000').status_code, 201)
        self.assertEqual(self.voice(name='x.pdf', duration_ms='3000').status_code, 400)
        with mock.patch('apps.chat.attachments.MAX_VOICE_BYTES', 50):
            self.assertEqual(self.voice(duration_ms='3000').status_code, 400)  # 10 MB chegarasi

    def test_mp4_is_refused_outside_voice_messages_and_idempotency_works(self):
        file = SimpleUploadedFile('kino.mp4', b'1234', content_type='video/mp4')
        resp = self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/send/', {'file': file}, format='multipart')
        self.assertEqual(resp.status_code, 400)
        first = self.voice(duration_ms='2000', client_message_id='v-1')
        again = self.voice(duration_ms='2000', client_message_id='v-1')
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(first.json()['id'], again.json()['id'])

    def test_files_and_images_have_an_attachment_too(self):
        file = SimpleUploadedFile('a.txt', b'salom', content_type='text/plain')
        body = self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/send/', {'file': file}, format='multipart').json()
        self.assertEqual(body['attachment']['type'], 'file')
        self.assertEqual((body['attachment']['name'], body['attachment']['mime'], body['attachment']['size']), ('a.txt', 'text/plain', 5))
        self.assertNotIn('duration_ms', body['attachment'])
        self.assertIsNone(self.send(self.student, 'matn')['attachment'])


class CapabilitiesTests(ChatV2Base):
    def caps(self, viewer, message):
        found = next(m for m in self.messages(viewer, query='?mark_read=0').json() if m['id'] == message['id'])
        return found['capabilities']

    def test_author_teacher_and_other_student(self):
        message = self.send(self.student, 'mening')
        self.assertEqual(self.caps(self.student, message), {
            'edit': True, 'delete': True, 'delete_everyone': True, 'pin': False, 'react': True, 'forward': True,
        })
        self.assertEqual(self.caps(self.teacher, message), {
            'edit': False, 'delete': True, 'delete_everyone': True, 'pin': True, 'react': True, 'forward': True,
        })
        self.assertEqual(self.caps(self.student2, message), {
            'edit': False, 'delete': True, 'delete_everyone': False, 'pin': False, 'react': True, 'forward': True,
        })

    def test_voice_cards_and_direct_chats(self):
        file = SimpleUploadedFile('o.webm', b'1234', content_type='audio/webm')
        voice = self.api(self.student).post(
            f'{self.base}/rooms/{self.room.id}/voice/', {'file': file, 'duration_ms': '2000'}, format='multipart',
        ).json()
        self.assertFalse(self.caps(self.student, voice)['edit'])  # ovozli xabar tahrirlanmaydi
        from apps.homework import services as homework

        homework.create_assignment(teacher=self.teacher, course_id=self.course.id, title='Vazifa')
        card = self.messages(self.teacher, query='?mark_read=0').json()[-1]
        caps = card['capabilities']
        self.assertEqual((caps['edit'], caps['forward'], caps['pin']), (False, False, True))
        direct = self.direct_room()
        note = self.send(self.teacher, 'salom', room=direct)
        self.assertTrue(self.api(self.student).get(f'{self.base}/rooms/{direct.id}/messages/?mark_read=0').json()[0]['capabilities']['pin'])
        self.assertEqual(note['capabilities']['edit'], True)  # send javobida ham bor

    def test_forward_and_edit_responses_carry_capabilities(self):
        message = self.send(self.student, 'x')
        edited = self.api(self.student).patch(f'{self.base}/messages/{message["id"]}/', {'text': 'y'}, format='json').json()
        self.assertTrue(edited['capabilities']['edit'])


class SocketPayloadTests(TransactionTestCase):
    """WebSocket: yangi hodisalar `{type, payload}` shaklida; xabarga ulanish egasining `capabilities`i qo'shiladi;
    "men uchun o'chirish" va `room_read` faqat shu foydalanuvchining qurilmalariga boradi."""

    def setUp(self):
        self.teacher = make('ws_t', User.Role.TEACHER)
        self.student = make('ws_s', User.Role.STUDENT)
        self.other = make('ws_o', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Socket')
        self.room = services.ensure_course_room(self.course)
        for student in (self.student, self.other):
            Enrollment.objects.create(course=self.course, student=student, status=Enrollment.Status.APPROVED)

    async def connect(self, user):
        from channels.testing import WebsocketCommunicator
        from rest_framework_simplejwt.tokens import AccessToken

        from root.asgi import application

        comm = WebsocketCommunicator(application, f'/ws/chat/{self.room.id}/?token={AccessToken.for_user(user)}')
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        return comm

    async def test_messages_carry_the_receivers_capabilities(self):
        from channels.db import database_sync_to_async

        student, teacher = await self.connect(self.student), await self.connect(self.teacher)
        await database_sync_to_async(services.send_message)(user=self.student, room_id=self.room.id, text='salom')
        for comm, expected in ((student, (True, True, False)), (teacher, (False, True, True))):
            caps = (await comm.receive_json_from(timeout=3))['message']['capabilities']
            self.assertEqual((caps['edit'], caps['delete_everyone'], caps['pin']), expected)
        await student.disconnect()
        await teacher.disconnect()

    async def test_edit_and_delete_for_me_over_the_socket(self):
        from channels.db import database_sync_to_async

        message = await database_sync_to_async(services.send_message)(user=self.student, room_id=self.room.id, text='xato')
        student, other = await self.connect(self.student), await self.connect(self.other)
        await database_sync_to_async(services.edit_message)(user=self.student, message_id=message.id, text="to'g'ri")
        frames = [await other.receive_json_from(timeout=3) for _ in range(2)]
        edited = next(f for f in frames if f['type'] == 'message_edited')
        self.assertEqual((edited['payload']['id'], edited['payload']['text']), (str(message.id), "to'g'ri"))
        await student.receive_json_from(timeout=3)
        await student.receive_json_from(timeout=3)
        # "men uchun o'chirish": faqat o'chirgan foydalanuvchining ulanishiga
        await database_sync_to_async(services.delete_messages)(user=self.student, ids=[message.id], scope='me')
        event = await student.receive_json_from(timeout=3)
        self.assertEqual((event['type'], event['payload']['scope']), ('messages_removed', 'me'))
        self.assertTrue(await other.receive_nothing(timeout=0.5))
        await student.disconnect()
        await other.disconnect()

    async def test_room_read_syncs_only_the_readers_devices(self):
        from channels.db import database_sync_to_async

        sent = await database_sync_to_async(services.send_message)(user=self.student, room_id=self.room.id, text='o\'qing')
        teacher, student = await self.connect(self.teacher), await self.connect(self.student)
        await database_sync_to_async(services.read_room)(user=self.teacher, room_id=self.room.id)
        frames = [await teacher.receive_json_from(timeout=3) for _ in range(2)]
        by_type = {f['type']: f for f in frames}
        self.assertEqual(by_type['room_read']['payload']['last_read_message_id'], str(sent.id))
        self.assertEqual(by_type['read']['last_message_id'], str(sent.id))
        only = await student.receive_json_from(timeout=3)
        self.assertEqual(only['type'], 'read')  # o'qituvchining `room_read`i talabaga bormaydi
        self.assertTrue(await student.receive_nothing(timeout=0.5))
        await teacher.disconnect()
        await student.disconnect()
