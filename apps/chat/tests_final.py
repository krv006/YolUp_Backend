"""Chat: video xabar, "yetib bordi" belgisi (1:1) va chat push qoidalari."""
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.chat import presence, push, services
from apps.chat.models import Message, RoomRead

from .tests_v2 import ChatV2Base


class VideoMessageTests(ChatV2Base):
    def send_video(self, user, name='dars.mp4', data=b'0123456789', room=None):
        room = room or self.room
        file = SimpleUploadedFile(name, data, content_type='video/mp4')
        return self.api(user).post(f'{self.base}/rooms/{room.id}/send/', {'file': file}, format='multipart')

    def test_mp4_becomes_a_video_message_with_attachment(self):
        resp = self.send_video(self.student)
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual((body['message_type'], body['type']), ('video', 'video'))
        self.assertEqual((body['attachment']['type'], body['attachment']['mime']), ('video', 'video/mp4'))
        item = body['attachments'][0]
        self.assertEqual((item['type'], item['thumbnail_url']), ('video', None))
        self.assertTrue(body['capabilities']['edit'])

    def test_video_is_listed_under_media_and_streams_in_ranges(self):
        body = self.send_video(self.student).json()
        media = self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/attachments/?kind=media').json()
        files = self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/attachments/?kind=file').json()
        self.assertEqual([r['name'] for r in media['results']], ['dars.mp4'])
        self.assertEqual(files['results'], [])
        resp = self.api(self.teacher).get(body['attachment']['url'], HTTP_RANGE='bytes=2-5')
        self.assertEqual((resp.status_code, resp.content), (206, b'2345'))
        self.assertIn('inline', resp['Content-Disposition'])  # brauzerda o'ynaydi

    def test_range_response_is_capped(self):
        body = self.send_video(self.student).json()
        with mock.patch('apps.chat.views.MAX_RANGE_BYTES', 4):
            resp = self.api(self.teacher).get(body['attachment']['url'], HTTP_RANGE='bytes=0-')
        self.assertEqual((resp.status_code, resp.content, resp['Content-Range']), (206, b'0123', 'bytes 0-3/10'))

    def test_video_size_limit_and_mixed_batch(self):
        with mock.patch('apps.chat.attachments.MAX_VIDEO_BYTES', 5):
            self.assertEqual(self.send_video(self.student).status_code, 400)
        two = [SimpleUploadedFile('a.mp4', b'1234'), SimpleUploadedFile('b.mov', b'1234')]
        resp = self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/send/', {'files': two}, format='multipart')
        self.assertEqual((resp.status_code, resp.json()['message_type']), (201, 'video'))
        mixed = [SimpleUploadedFile('a.mp4', b'1234'), SimpleUploadedFile('b.txt', b'1234')]
        resp = self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/send/', {'files': mixed}, format='multipart')
        self.assertEqual(resp.json()['message_type'], 'file')


class DeliveredStatusTests(ChatV2Base):
    def setUp(self):
        super().setUp()
        self.direct = self.direct_room()

    def status_of(self, viewer, message):
        rows = self.messages(viewer, room=self.direct, query='?mark_read=0').json()
        return next(m for m in rows if m['id'] == message['id'])['status']

    def test_sent_then_delivered_then_read(self):
        message = self.send(self.teacher, 'Salom', room=self.direct)
        self.assertEqual(self.status_of(self.teacher, message), 'sent')
        with mock.patch('apps.chat.realtime.broadcast_event') as events:
            event = services.deliver_message(user=self.student, message_id=message['id'])
        self.assertEqual((event['type'], event['user_id'], event['last_message_id']), ('delivered', str(self.student.id), message['id']))
        self.assertEqual(events.call_args.args[1]['type'], 'delivered')
        self.assertEqual(self.status_of(self.teacher, message), 'delivered')
        self.api(self.student).post(f'{self.base}/rooms/{self.direct.id}/read/', {}, format='json')
        self.assertEqual(self.status_of(self.teacher, message), 'read')

    def test_repeat_sender_and_group_are_ignored(self):
        message = self.send(self.teacher, 'Salom', room=self.direct)
        self.assertIsNone(services.deliver_message(user=self.teacher, message_id=message['id']))  # o'z xabari
        self.assertIsNotNone(services.deliver_message(user=self.student, message_id=message['id']))
        self.assertIsNone(services.deliver_message(user=self.student, message_id=message['id']))  # qayta — o'zgarish yo'q
        group = self.send(self.teacher, 'Hammaga')
        self.assertIsNone(services.deliver_message(user=self.student, message_id=group['id']))  # guruhda belgi yo'q
        self.assertEqual(self.messages(self.teacher, query='?mark_read=0').json()[-1]['status'], 'sent')
        self.assertIsNone(services.deliver_message(user=self.stranger, message_id=message['id']))  # a'zo emas
        self.assertIsNone(services.deliver_message(user=self.student, message_id='not-an-id'))

    def test_connecting_delivers_the_offline_backlog(self):
        first = self.send(self.teacher, 'bir', room=self.direct)
        last = self.send(self.teacher, 'ikki', room=self.direct)
        with mock.patch('apps.chat.realtime.broadcast_event') as events:
            event = services.deliver_room(user=self.student, room_id=self.direct.id)
            self.assertIsNone(services.deliver_room(user=self.student, room_id=self.direct.id))
        self.assertEqual(event['last_message_id'], last['id'])
        self.assertEqual(events.call_count, 1)
        self.assertEqual((self.status_of(self.teacher, first), self.status_of(self.teacher, last)), ('delivered', 'delivered'))


class ChatPushTests(ChatV2Base):
    def setUp(self):
        super().setUp()
        cache.clear()

    def message(self, sender=None, room=None, **fields):
        fields.setdefault('text', 'Ertaga test')
        return Message.objects.create(room=room or self.room, sender=sender or self.teacher, **fields)

    def ids(self, message):
        return {u.username for u in push.recipients_for(message)}

    def test_offline_members_get_it_but_not_the_sender(self):
        self.assertEqual(self.ids(self.message()), {'s1', 's3'})
        self.assertEqual(self.ids(self.message(sender=self.student)), {'t1', 's3'})

    def test_online_muted_and_disabled_members_are_skipped(self):
        message = self.message()
        presence.mark_online(self.student.id)
        self.assertEqual(self.ids(message), {'s3'})
        presence.mark_offline(self.student.id)
        RoomRead.objects.create(room=self.room, user=self.student2, last_read_at=timezone.now(), muted=True)
        self.assertEqual(self.ids(message), {'s1'})
        RoomRead.objects.filter(user=self.student2).update(muted_until=timezone.now() - timedelta(hours=1))  # muddat o'tgan
        self.assertEqual(self.ids(message), {'s1', 's3'})
        User = type(self.student)
        User.objects.filter(pk=self.student.pk).update(notify_messages=False)
        self.assertEqual(self.ids(message), {'s3'})

    def test_mentioned_user_is_left_to_the_mention_notification(self):
        message = self.message()
        message.mentions.set([self.student])
        self.assertEqual(self.ids(message), {'s3'})

    def test_push_content_for_group_and_direct_and_throttle(self):
        message = self.message()
        with mock.patch('apps.notifications.services.send_web_push') as web, \
                mock.patch('apps.notifications.services.send_mobile_push') as mobile:
            push._send(message.id)
            note, users = web.call_args.args
            self.assertEqual({u.username for u in users}, {'s1', 's3'})
            self.assertEqual((web.call_args.kwargs['title'], note.description), ('Algebra', 't1: Ertaga test'))
            self.assertEqual((note.kind, note.link_type, note.link_id), ('chat_message', 'chat_room', str(self.room.id)))
            self.assertEqual(mobile.call_args.kwargs['title'], 'Algebra')
            push._send(message.id)  # 30 soniya ichida takror — hech kimga
            self.assertEqual(web.call_count, 1)
            direct = self.direct_room()
            voice = self.message(room=direct, message_type=Message.Type.VOICE, text='')
            push._send(voice.id)
        note = web.call_args.args[0]
        self.assertEqual((web.call_args.kwargs['title'], note.description), ('t1', '🎤 Ovozli xabar'))
        self.assertEqual({u.username for u in web.call_args.args[1]}, {'s1'})

    def test_no_notification_rows_and_deleted_or_system_messages_are_skipped(self):
        from apps.notifications.models import Notification

        message = self.message()
        with mock.patch('apps.notifications.services.send_web_push') as web, \
                mock.patch('apps.notifications.services.send_mobile_push'):
            push._send(message.id)
            self.assertEqual(Notification.objects.count(), 0)
            Message.objects.filter(pk=message.pk).update(deleted_at=timezone.now())
            cache.clear()
            push._send(message.id)
            system = self.message(kind=Message.Kind.SYSTEM)
            push._send(system.id)
        self.assertEqual(web.call_count, 1)

    def test_sending_a_message_schedules_the_push(self):
        with mock.patch('apps.chat.push.schedule') as scheduled, self.captureOnCommitCallbacks(execute=True):
            self.send(self.teacher, 'Salom')
        self.assertEqual(scheduled.call_count, 1)
