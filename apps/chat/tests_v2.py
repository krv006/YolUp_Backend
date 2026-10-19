"""Chat v2: javob, fayl/rasm/ovoz, o'qilganlik, sahifalash, qadash, suhbat holati, tahrirlash/o'chirish/uzatish,
reaksiyalar, qidiruv, a'zolar/onlayn/e'lon rejimi, vazifa kartasi, bildirishnoma `read-all`."""
import io
from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.chat import attachments, presence, services
from apps.chat.models import ChatRoom, Message, RoomRead
from apps.lessons.models import Course, Enrollment

from .tests import make, make_image


def pdf_bytes(pages=2):
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class ChatV2Base(TestCase):
    def setUp(self):
        self.teacher = make('t1', User.Role.TEACHER)
        self.student = make('s1', User.Role.STUDENT)
        self.student2 = make('s3', User.Role.STUDENT)
        self.stranger = make('s2', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Algebra')
        self.room = services.ensure_course_room(self.course)
        for student in (self.student, self.student2):
            Enrollment.objects.create(course=self.course, student=student, status=Enrollment.Status.APPROVED)
        self.client = APIClient()
        self.base = '/api/v1/chat'

    def api(self, user):
        self.client.force_authenticate(user)
        return self.client

    def send(self, user, text='salom', room=None, **extra):
        room = room or self.room
        resp = self.api(user).post(f'{self.base}/rooms/{room.id}/send/', {'text': text, **extra}, format='json')
        self.assertIn(resp.status_code, (200, 201), resp.content)
        return resp.json()

    def messages(self, user, room=None, query=''):
        room = room or self.room
        return self.api(user).get(f'{self.base}/rooms/{room.id}/messages/{query}')

    def room_info(self, user, room=None):
        room = room or self.room
        resp = self.api(user).get(f'{self.base}/rooms/{room.id}/')
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def direct_room(self):
        return ChatRoom.objects.create(
            kind=ChatRoom.Kind.DIRECT, teacher=self.teacher, student=self.student,
            direct_status=ChatRoom.DirectStatus.ACTIVE,
        )


class ReplyAndIdempotencyTests(ChatV2Base):
    def test_reply_is_a_separate_field(self):
        original = self.send(self.student, 'Savol bor')
        reply = self.send(self.teacher, 'Ha, ayting', reply_to_id=original['id'])
        self.assertEqual(reply['reply_to']['id'], original['id'])
        self.assertEqual(reply['reply_to']['text'], 'Savol bor')
        self.assertEqual(reply['text'], 'Ha, ayting')
        history = self.messages(self.student).json()
        self.assertEqual(history[-1]['reply_to']['sender_name'], 's1')

    def test_reply_to_a_message_of_another_room_is_refused(self):
        other = self.direct_room()
        foreign = self.send(self.teacher, 'boshqa', room=other)
        resp = self.api(self.student).post(
            f'{self.base}/rooms/{self.room.id}/send/', {'text': 'x', 'reply_to_id': foreign['id']}, format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_same_client_message_id_returns_the_first_message(self):
        first = self.send(self.student, 'bir', client_message_id='abc-1')
        resp = self.api(self.student).post(
            f'{self.base}/rooms/{self.room.id}/send/', {'text': 'bir', 'client_message_id': 'abc-1'}, format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['id'], first['id'])
        self.assertEqual(Message.objects.filter(room=self.room).count(), 1)
        # boshqa foydalanuvchining bir xil id si alohida xabar
        self.send(self.student2, 'ikki', client_message_id='abc-1')
        self.assertEqual(Message.objects.filter(room=self.room).count(), 2)

    def test_empty_message_is_still_refused(self):
        resp = self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/send/', {'text': '  '}, format='json')
        self.assertEqual(resp.status_code, 400)


class FileTests(ChatV2Base):
    def upload(self, user, name, content, content_type='application/octet-stream', **extra):
        file = SimpleUploadedFile(name, content, content_type=content_type)
        return self.api(user).post(
            f'{self.base}/rooms/{self.room.id}/send/', {'file': file, 'text': '', **extra}, format='multipart',
        )

    def test_pdf_has_name_type_size_and_pages(self):
        data = pdf_bytes(3)
        resp = self.upload(self.student, 'uy vazifasi.pdf', data, 'application/pdf')
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body['message_type'], 'file')
        self.assertEqual((body['file_name'], body['file_type'], body['file_size']), ('uy vazifasi.pdf', 'application/pdf', len(data)))
        self.assertEqual(body['page_count'], 3)
        self.assertTrue(body['file_url'].startswith('/api/v1/chat/files/'))

    def test_download_keeps_the_real_type_and_sends_documents_as_attachment(self):
        pdf = self.upload(self.student, 'a.pdf', pdf_bytes(1)).json()
        resp = self.api(self.teacher).get(pdf['file_url'])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp['Content-Disposition'].startswith('inline'))
        doc = self.upload(self.student, 'b.docx', b'PK\x03\x04docx').json()
        resp = self.api(self.teacher).get(doc['file_url'])
        self.assertTrue(resp['Content-Disposition'].startswith('attachment'))
        self.assertEqual(resp['X-Content-Type-Options'], 'nosniff')

    def test_image_is_detected_and_a_broken_one_is_refused(self):
        resp = self.upload(self.student, 'rasm.png', make_image().getvalue(), 'image/png')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()['message_type'], 'image')
        bad = self.upload(self.student, 'buzuq.png', b'not an image')
        self.assertEqual(bad.status_code, 400)

    def test_dangerous_types_and_huge_files_are_refused(self):
        for name in ('virus.exe', 'x.html', 'x.svg', 'x.js', 'noext'):
            self.assertEqual(self.upload(self.student, name, b'abc').status_code, 400, name)
        with mock.patch.object(attachments, 'MAX_FILE_BYTES', 10):
            self.assertEqual(self.upload(self.student, 'big.txt', b'x' * 11).status_code, 400)
        self.assertEqual(self.upload(self.student, 'empty.txt', b'').status_code, 400)

    def test_a_stranger_cannot_download_and_a_deleted_file_is_gone(self):
        body = self.upload(self.student, 'a.txt', b'secret').json()
        self.assertEqual(self.api(self.stranger).get(body['file_url']).status_code, 403)
        self.api(self.student).delete(f'{self.base}/messages/{body["id"]}/?scope=everyone')
        self.assertEqual(self.api(self.teacher).get(body['file_url']).status_code, 404)


class VoiceTests(ChatV2Base):
    def voice(self, **extra):
        file = SimpleUploadedFile('ovoz.m4a', b'0123456789' * 10, content_type='audio/mp4')
        return self.api(self.student).post(
            f'{self.base}/rooms/{self.room.id}/send/',
            {'file': file, 'message_type': 'voice', **extra}, format='multipart',
        )

    def test_voice_message_needs_a_duration_and_keeps_waveform(self):
        self.assertEqual(self.voice().status_code, 400)
        resp = self.voice(duration='24', waveform='[3, 7, 12, 300, -5]')
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual((body['message_type'], body['duration']), ('voice', 24))
        self.assertEqual(body['waveform'], [3, 7, 12, 255, 0])

    def test_bad_waveform_is_dropped_but_the_message_is_kept(self):
        body = self.voice(duration='5', waveform='nonsense').json()
        self.assertEqual(body['waveform'], [])

    def test_voice_needs_an_audio_file(self):
        file = SimpleUploadedFile('x.pdf', pdf_bytes(1), content_type='application/pdf')
        resp = self.api(self.student).post(
            f'{self.base}/rooms/{self.room.id}/send/',
            {'file': file, 'message_type': 'voice', 'duration': '5'}, format='multipart',
        )
        self.assertEqual(resp.status_code, 400)

    def test_audio_supports_range_requests(self):
        url = self.voice(duration='3').json()['file_url']
        resp = self.api(self.teacher).get(url, HTTP_RANGE='bytes=10-19')
        self.assertEqual(resp.status_code, 206)
        self.assertEqual(resp['Content-Range'], 'bytes 10-19/100')
        self.assertEqual(resp.content, b'0123456789')
        self.assertEqual(self.api(self.teacher).get(url, HTTP_RANGE='bytes=500-').status_code, 416)
        self.assertEqual(self.api(self.teacher).get(url).status_code, 200)


class ReadReceiptTests(ChatV2Base):
    def test_status_turns_read_when_the_other_side_reads(self):
        sent = self.send(self.student, 'salom')
        self.assertEqual(self.messages(self.student, query='?mark_read=0').json()[0]['status'], 'sent')
        self.assertEqual(self.messages(self.teacher, query='?mark_read=0').json()[0]['status'], 'sent')
        resp = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/read/', {'last_message_id': sent['id']}, format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.messages(self.student, query='?mark_read=0').json()[0]['status'], 'read')

    def test_read_event_is_broadcast_once(self):
        sent = self.send(self.student, 'salom')
        with mock.patch('apps.chat.realtime.broadcast_event') as broadcast, self.captureOnCommitCallbacks(execute=True):
            self.api(self.teacher).post(f'{self.base}/rooms/{self.room.id}/read/', {}, format='json')
            self.api(self.teacher).post(f'{self.base}/rooms/{self.room.id}/read/', {}, format='json')
        self.assertEqual(broadcast.call_count, 1)
        event = broadcast.call_args.args[1]
        self.assertEqual((event['type'], event['user_id'], event['last_message_id']),
                         ('read', str(self.teacher.id), sent['id']))

    def test_read_only_moves_forward_and_checks_the_message(self):
        first = self.send(self.student, 'bir')
        self.send(self.student, 'ikki')
        self.api(self.teacher).post(f'{self.base}/rooms/{self.room.id}/read/', {}, format='json')
        self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/read/', {'last_message_id': first['id']}, format='json',
        )
        self.assertEqual(self.room_info(self.teacher)['unread_count'], 0)  # orqaga qaytmadi
        other = self.direct_room()
        foreign = self.send(self.teacher, 'x', room=other)
        resp = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/read/', {'last_message_id': foreign['id']}, format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_unread_marker_points_to_the_first_unread_message(self):
        self.send(self.student, 'bir')
        self.api(self.teacher).post(f'{self.base}/rooms/{self.room.id}/read/', {}, format='json')
        second = self.send(self.student, 'ikki')
        self.send(self.student2, 'uch')
        info = self.room_info(self.teacher)
        self.assertEqual((info['unread'], info['unread_count']), (2, 2))
        self.assertEqual(info['first_unread_message_id'], second['id'])
        self.api(self.teacher).post(f'{self.base}/rooms/{self.room.id}/read/', {}, format='json')
        info = self.room_info(self.teacher)
        self.assertEqual((info['unread_count'], info['first_unread_message_id']), (0, None))

    def test_old_clients_still_mark_read_by_fetching(self):
        self.send(self.student, 'salom')
        self.messages(self.teacher)
        self.assertEqual(self.room_info(self.teacher)['unread_count'], 0)


class PaginationTests(ChatV2Base):
    def test_load_older_messages_with_before(self):
        sent = [self.send(self.student, f'm{i}') for i in range(5)]
        page = self.messages(self.teacher, query='?limit=2&mark_read=0').json()
        self.assertEqual([m['text'] for m in page['items']], ['m3', 'm4'])
        self.assertTrue(page['has_more'])
        page = self.messages(self.teacher, query=f'?before={page["items"][0]["id"]}&limit=2&mark_read=0').json()
        self.assertEqual([m['text'] for m in page['items']], ['m1', 'm2'])
        self.assertTrue(page['has_more'])
        page = self.messages(self.teacher, query=f'?before={page["items"][0]["id"]}&limit=2&mark_read=0').json()
        self.assertEqual([m['text'] for m in page['items']], ['m0'])
        self.assertFalse(page['has_more'])
        self.assertEqual(len(sent), 5)

    def test_old_shapes_are_unchanged(self):
        self.send(self.student, 'a')
        self.assertIsInstance(self.messages(self.teacher).json(), list)
        self.assertEqual(self.messages(self.teacher, query='?before=nope').status_code, 400)


class PinTests(ChatV2Base):
    def test_teacher_pins_for_everyone_in_a_group(self):
        message = self.send(self.student, 'Muhim')
        resp = self.api(self.student).post(
            f'{self.base}/rooms/{self.room.id}/pin/', {'message_id': message['id']}, format='json',
        )
        self.assertEqual(resp.status_code, 403)
        resp = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/pin/', {'message_id': message['id']}, format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        pinned = self.room_info(self.student)['pinned_message']
        self.assertEqual((pinned['id'], pinned['text']), (message['id'], 'Muhim'))
        self.assertEqual(self.api(self.student).delete(f'{self.base}/rooms/{self.room.id}/pin/').status_code, 403)
        self.assertEqual(self.api(self.teacher).delete(f'{self.base}/rooms/{self.room.id}/pin/').status_code, 200)
        self.assertIsNone(self.room_info(self.student)['pinned_message'])

    def test_either_side_pins_in_a_direct_chat(self):
        direct = self.direct_room()
        message = self.send(self.teacher, 'Eslatma', room=direct)
        resp = self.api(self.student).post(
            f'{self.base}/rooms/{direct.id}/pin/', {'message_id': message['id']}, format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_only_messages_of_this_room_can_be_pinned(self):
        other = self.direct_room()
        foreign = self.send(self.teacher, 'x', room=other)
        resp = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/pin/', {'message_id': foreign['id']}, format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_deleting_the_pinned_message_unpins_it(self):
        message = self.send(self.teacher, 'E\'lon')
        self.api(self.teacher).post(f'{self.base}/rooms/{self.room.id}/pin/', {'message_id': message['id']}, format='json')
        self.api(self.teacher).delete(f'{self.base}/messages/{message["id"]}/?scope=everyone')
        self.assertIsNone(self.room_info(self.student)['pinned_message'])


class RoomStateTests(ChatV2Base):
    def rooms(self, user):
        return {r['id']: r for r in self.api(user).get(f'{self.base}/rooms/').json()['results']}

    def test_pin_and_mute_are_personal(self):
        self.assertEqual(self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/pin-room/').status_code, 200)
        self.assertEqual(self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/mute/', {'until': None}, format='json').status_code, 200)
        mine = self.rooms(self.student)[str(self.room.id)]
        self.assertEqual((mine['is_pinned'], mine['is_muted']), (True, True))
        other = self.rooms(self.student2)[str(self.room.id)]
        self.assertEqual((other['is_pinned'], other['is_muted']), (False, False))
        self.api(self.student).delete(f'{self.base}/rooms/{self.room.id}/pin-room/')
        self.api(self.student).delete(f'{self.base}/rooms/{self.room.id}/mute/')
        mine = self.rooms(self.student)[str(self.room.id)]
        self.assertEqual((mine['is_pinned'], mine['is_muted']), (False, False))

    def test_timed_mute_expires_and_a_past_time_is_refused(self):
        past = (timezone.now() - timedelta(hours=1)).isoformat()
        resp = self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/mute/', {'until': past}, format='json')
        self.assertEqual(resp.status_code, 400)
        future = (timezone.now() + timedelta(hours=1)).isoformat()
        self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/mute/', {'until': future}, format='json')
        self.assertTrue(self.rooms(self.student)[str(self.room.id)]['is_muted'])
        RoomRead.objects.filter(user=self.student).update(muted_until=timezone.now() - timedelta(minutes=1))
        self.assertFalse(self.rooms(self.student)[str(self.room.id)]['is_muted'])

    def test_leave_hides_the_room_until_a_new_message(self):
        self.send(self.teacher, 'eski')
        self.assertEqual(self.api(self.student).delete(f'{self.base}/rooms/{self.room.id}/leave/').status_code, 204)
        self.assertNotIn(str(self.room.id), self.rooms(self.student))
        self.assertIn(str(self.room.id), self.rooms(self.student2))  # boshqalarga ta'sir qilmaydi
        self.assertEqual(Enrollment.objects.filter(student=self.student, status='approved').count(), 1)  # a'zolik joyida
        self.send(self.teacher, 'yangi')
        self.assertIn(str(self.room.id), self.rooms(self.student))

    def test_mark_unread_chat_as_read_without_opening_it(self):
        self.send(self.teacher, 'bir')
        self.assertEqual(self.rooms(self.student)[str(self.room.id)]['unread_count'], 1)
        self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/read/', {}, format='json')
        self.assertEqual(self.rooms(self.student)[str(self.room.id)]['unread_count'], 0)

    def test_a_stranger_cannot_touch_the_state(self):
        for method, path in (('post', 'pin-room'), ('post', 'mute'), ('delete', 'leave'), ('post', 'read')):
            resp = getattr(self.api(self.stranger), method)(f'{self.base}/rooms/{self.room.id}/{path}/')
            self.assertEqual(resp.status_code, 403, path)


class EditDeleteTests(ChatV2Base):
    def test_edit_is_for_the_author_only(self):
        message = self.send(self.student, 'xato')
        resp = self.api(self.student).patch(f'{self.base}/messages/{message["id"]}/', {'text': 'to\'g\'ri'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body['text'], "to'g'ri")
        self.assertIsNotNone(body['edited_at'])
        self.assertEqual(self.api(self.teacher).patch(f'{self.base}/messages/{message["id"]}/', {'text': 'x'}, format='json').status_code, 403)
        self.assertEqual(self.api(self.student).patch(f'{self.base}/messages/{message["id"]}/', {'text': ' '}, format='json').status_code, 400)

    def test_voice_cannot_be_edited(self):
        file = SimpleUploadedFile('o.m4a', b'1234', content_type='audio/mp4')
        voice = self.api(self.student).post(
            f'{self.base}/rooms/{self.room.id}/send/', {'file': file, 'message_type': 'voice', 'duration': '2'}, format='multipart',
        ).json()
        resp = self.api(self.student).patch(f'{self.base}/messages/{voice["id"]}/', {'text': 'x'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_delete_for_me_hides_only_from_me(self):
        message = self.send(self.student, 'bu')
        self.assertEqual(self.api(self.teacher).delete(f'{self.base}/messages/{message["id"]}/?scope=me').status_code, 204)
        self.assertEqual(self.messages(self.teacher).json(), [])
        self.assertEqual(len(self.messages(self.student).json()), 1)
        self.assertEqual(self.room_info(self.teacher)['unread_count'], 0)

    def test_delete_for_everyone_rules(self):
        mine = self.send(self.student, 'mening')
        theirs = self.send(self.student2, 'ularniki')
        resp = self.api(self.student).delete(f'{self.base}/messages/{theirs["id"]}/?scope=everyone')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.api(self.student).delete(f'{self.base}/messages/{mine["id"]}/?scope=everyone').status_code, 204)
        self.assertEqual(self.api(self.teacher).delete(f'{self.base}/messages/{theirs["id"]}/?scope=everyone').status_code, 204)
        self.assertEqual(self.messages(self.teacher).json(), [])
        self.assertEqual(self.api(self.teacher).delete(f'{self.base}/messages/{theirs["id"]}/').status_code, 404)

    def test_deleted_message_shows_in_replies_as_deleted_and_broadcasts(self):
        original = self.send(self.student, 'asl')
        self.send(self.student2, 'javob', reply_to_id=original['id'])
        with mock.patch('apps.chat.realtime.broadcast_event') as broadcast, self.captureOnCommitCallbacks(execute=True):
            self.api(self.student).delete(f'{self.base}/messages/{original["id"]}/?scope=everyone')
        events = {c.args[1]['type']: c.args[1] for c in broadcast.call_args_list}
        self.assertEqual(events['message_deleted']['ids'], [original['id']])  # eski nom
        self.assertEqual(
            events['messages_removed']['payload'],
            {'room_id': str(self.room.id), 'message_ids': [original['id']], 'scope': 'everyone'},
        )
        reply = self.messages(self.teacher).json()[0]
        self.assertEqual((reply['reply_to']['is_deleted'], reply['reply_to']['text']), (True, ''))

    def test_bulk_delete_is_all_or_nothing(self):
        mine = self.send(self.student, 'a')
        theirs = self.send(self.student2, 'b')
        resp = self.api(self.student).post(
            f'{self.base}/messages/bulk-delete/', {'ids': [mine['id'], theirs['id']], 'scope': 'everyone'}, format='json',
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(len(self.messages(self.teacher).json()), 2)
        resp = self.api(self.teacher).post(
            f'{self.base}/messages/bulk-delete/', {'ids': [mine['id'], theirs['id']], 'scope': 'everyone'}, format='json',
        )
        self.assertEqual((resp.status_code, resp.json()['deleted']), (200, 2))
        self.assertEqual(self.messages(self.teacher).json(), [])
        bad = self.api(self.teacher).post(f'{self.base}/messages/bulk-delete/', {'ids': [], 'scope': 'me'}, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_a_stranger_cannot_delete_or_edit(self):
        message = self.send(self.student, 'x')
        self.assertEqual(self.api(self.stranger).delete(f'{self.base}/messages/{message["id"]}/?scope=me').status_code, 403)
        self.assertEqual(self.api(self.stranger).patch(f'{self.base}/messages/{message["id"]}/', {'text': 'y'}, format='json').status_code, 403)


class ForwardTests(ChatV2Base):
    def test_forward_copies_the_message_with_its_origin(self):
        direct = self.direct_room()
        note = self.send(self.teacher, 'Ertaga imtihon', room=direct)
        resp = self.api(self.student).post(
            f'{self.base}/rooms/{self.room.id}/forward/', {'message_ids': [note['id']]}, format='json',
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        copy = resp.json()[0]
        self.assertEqual((copy['text'], copy['forwarded_from_name']), ('Ertaga imtihon', 't1'))
        self.assertEqual(copy['sender']['username'], 's1')
        again = self.api(self.student2).post(
            f'{self.base}/rooms/{direct.id}/forward/', {'message_ids': [copy['id']]}, format='json',
        )
        self.assertEqual(again.status_code, 403)  # s3 direct chatga yoza olmaydi

    def test_forward_keeps_the_original_author_through_a_chain_and_copies_files(self):
        file = SimpleUploadedFile('a.pdf', pdf_bytes(2), content_type='application/pdf')
        sent = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/send/', {'file': file}, format='multipart',
        ).json()
        direct = self.direct_room()
        first = self.api(self.student).post(
            f'{self.base}/rooms/{direct.id}/forward/', {'message_ids': [sent['id']]}, format='json',
        ).json()[0]
        self.assertEqual((first['file_name'], first['page_count'], first['message_type']), ('a.pdf', 2, 'file'))
        second = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/forward/', {'message_ids': [first['id']]}, format='json',
        ).json()[0]
        self.assertEqual(second['forwarded_from_name'], 't1')
        self.assertEqual(self.api(self.student2).get(second['file_url']).status_code, 200)

    def test_cannot_forward_from_a_chat_you_cannot_read_or_system_cards(self):
        direct = self.direct_room()
        secret = self.send(self.teacher, 'maxfiy', room=direct)
        resp = self.api(self.student2).post(
            f'{self.base}/rooms/{self.room.id}/forward/', {'message_ids': [secret['id']]}, format='json',
        )
        self.assertEqual(resp.status_code, 403)
        system = Message.objects.create(
            room=self.room, sender=self.teacher, text='tizim', kind=Message.Kind.SYSTEM, system_key='x',
        )
        resp = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/forward/', {'message_ids': [str(system.id)]}, format='json',
        )
        self.assertEqual(resp.status_code, 400)


class ReactionTests(ChatV2Base):
    def test_toggle_and_per_viewer_flag(self):
        message = self.send(self.student, 'zo\'r')
        url = f'{self.base}/messages/{message["id"]}/reactions/'
        first = self.api(self.teacher).post(url, {'emoji': '🔥'}, format='json').json()
        self.assertEqual(first['reactions'], [{'emoji': '🔥', 'count': 1, 'reacted': True}])
        self.api(self.student2).post(url, {'emoji': '🔥'}, format='json')
        seen_by_student = self.messages(self.student, query='?mark_read=0').json()[0]['reactions']
        self.assertEqual(seen_by_student, [{'emoji': '🔥', 'count': 2, 'reacted': False}])
        seen_by_teacher = self.messages(self.teacher, query='?mark_read=0').json()[0]['reactions']
        self.assertEqual(seen_by_teacher, [{'emoji': '🔥', 'count': 2, 'reacted': True}])
        off = self.api(self.teacher).post(url, {'emoji': '🔥', 'toggle': True}, format='json').json()
        self.assertEqual(off['reactions'], [{'emoji': '🔥', 'count': 1, 'reacted': False}])

    def test_bad_emoji_and_outsiders_are_refused(self):
        message = self.send(self.student, 'x')
        url = f'{self.base}/messages/{message["id"]}/reactions/'
        for bad in ('', 'abc', 'x' * 17, None):
            self.assertEqual(self.api(self.teacher).post(url, {'emoji': bad}, format='json').status_code, 400, bad)
        self.assertEqual(self.api(self.stranger).post(url, {'emoji': '👍'}, format='json').status_code, 403)

    def test_reaction_event_is_broadcast(self):
        message = self.send(self.student, 'x')
        with mock.patch('apps.chat.realtime.broadcast_event') as broadcast, self.captureOnCommitCallbacks(execute=True):
            self.api(self.teacher).post(f'{self.base}/messages/{message["id"]}/reactions/', {'emoji': '👍'}, format='json')
        events = {c.args[1]['type']: c.args[1] for c in broadcast.call_args_list}
        legacy = events['reaction']
        self.assertEqual((legacy['emoji'], legacy['added'], legacy['count']), ('👍', True, 1))
        payload = events['message_reaction']['payload']
        self.assertEqual((payload['room_id'], payload['message_id']), (str(self.room.id), message['id']))
        self.assertEqual(payload['reactions'], [{'emoji': '👍', 'count': 1, 'user_ids': [str(self.teacher.id)]}])


class SearchTests(ChatV2Base):
    def test_search_counts_and_skips_deleted_and_hidden(self):
        self.send(self.student, 'Uy vazifasi 112')
        hidden = self.send(self.student, '112 yashirin')
        gone = self.send(self.student, '112 o\'chgan')
        self.send(self.student, 'boshqa')
        self.api(self.teacher).delete(f'{self.base}/messages/{hidden["id"]}/?scope=me')
        self.api(self.student).delete(f'{self.base}/messages/{gone["id"]}/?scope=everyone')
        body = self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/messages/search/?q=112').json()
        self.assertEqual(body['total'], 1)
        self.assertEqual(body['items'][0]['text'], 'Uy vazifasi 112')
        self.assertEqual(self.api(self.student).get(f'{self.base}/rooms/{self.room.id}/messages/search/?q=112').json()['total'], 2)

    def test_empty_query_and_strangers_are_refused(self):
        self.assertEqual(self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/messages/search/?q=').status_code, 400)
        self.assertEqual(self.api(self.stranger).get(f'{self.base}/rooms/{self.room.id}/messages/search/?q=a').status_code, 403)


class GroupScreenTests(ChatV2Base):
    def test_members_with_online_state(self):
        presence.mark_online(self.student.id)
        self.addCleanup(presence.mark_offline, self.student.id)
        rows = self.api(self.student2).get(f'{self.base}/rooms/{self.room.id}/members/').json()
        self.assertEqual([r['role'] for r in rows][0], 'teacher')
        self.assertEqual({r['name'] for r in rows}, {'t1', 's1', 's3'})
        self.assertEqual({r['name']: r['is_online'] for r in rows}, {'t1': False, 's1': True, 's3': False})
        self.assertEqual(self.room_info(self.teacher)['online_count'], 1)
        self.assertEqual(self.api(self.stranger).get(f'{self.base}/rooms/{self.room.id}/members/').status_code, 403)

    def test_presence_counts_connections(self):
        presence.mark_online(self.student.id)
        presence.mark_online(self.student.id)
        presence.mark_offline(self.student.id)
        self.assertEqual(presence.online_ids([self.student.id]), {str(self.student.id)})
        presence.mark_offline(self.student.id)
        self.assertEqual(presence.online_ids([self.student.id]), set())
        presence.mark_offline(self.student.id)  # ortiqcha yopilish xato bermaydi

    def test_announcement_mode(self):
        url = f'{self.base}/rooms/{self.room.id}/'
        self.assertEqual(self.api(self.student).patch(url, {'announcement_only': True}, format='json').status_code, 403)
        resp = self.api(self.teacher).patch(url, {'announcement_only': True}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()['announcement_only'])
        denied = self.api(self.student).post(f'{url}send/', {'text': 'savol'}, format='json')
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.api(self.teacher).post(f'{url}send/', {'text': 'E\'lon'}, format='json').status_code, 201)
        self.assertEqual(len(self.messages(self.student).json()), 1)  # o'qish mumkin
        self.api(self.teacher).patch(url, {'announcement_only': False}, format='json')
        self.assertEqual(self.api(self.student).post(f'{url}send/', {'text': 'savol'}, format='json').status_code, 201)

    def test_announcement_flag_is_not_for_direct_chats(self):
        direct = self.direct_room()
        resp = self.api(self.teacher).patch(f'{self.base}/rooms/{direct.id}/', {'announcement_only': True}, format='json')
        self.assertEqual(resp.status_code, 403)


class AssignmentCardTests(ChatV2Base):
    def test_assignment_creates_a_card_with_counters(self):
        from apps.homework import services as homework

        due = timezone.now() + timedelta(days=3)
        assignment = homework.create_assignment(
            teacher=self.teacher, course_id=self.course.id, title='112–118-misollar', due_at=due.isoformat(),
        )
        card = self.messages(self.student).json()[-1]
        self.assertEqual(card['message_type'], 'assignment')
        self.assertEqual(card['assignment']['id'], assignment['id'])
        self.assertEqual((card['assignment']['title'], card['assignment']['total_count'], card['assignment']['submitted_count']),
                         ('112–118-misollar', 2, 0))
        self.assertIsNotNone(card['assignment']['due_at'])

    def test_a_failing_card_does_not_break_homework(self):
        from apps.homework import services as homework

        with mock.patch('apps.chat.services.ensure_course_room', side_effect=RuntimeError('boom')):
            result = homework.create_assignment(teacher=self.teacher, course_id=self.course.id, title='Vazifa')
        self.assertTrue(result['id'])

    def test_cards_cannot_be_forwarded_or_edited(self):
        from apps.homework import services as homework

        homework.create_assignment(teacher=self.teacher, course_id=self.course.id, title='Vazifa')
        card = self.messages(self.teacher).json()[-1]
        self.assertEqual(self.api(self.teacher).patch(f'{self.base}/messages/{card["id"]}/', {'text': 'x'}, format='json').status_code, 400)
        resp = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/forward/', {'message_ids': [card['id']]}, format='json',
        )
        self.assertEqual(resp.status_code, 400)


class NotificationBulkTests(TestCase):
    def test_read_all_and_category(self):
        from apps.notifications import services as notifications
        from apps.notifications.models import Notification

        admin = make('adm', User.Role.TEACHER)
        user = make('rcpt', User.Role.STUDENT)
        for kind, link in (('', ''), ('homework_reviewed', 'submission'), ('lesson_reminder', 'lesson'), ('', 'assignment')):
            notifications.send_notification(
                sender=admin, description='Matn', target_type=Notification.Target.USER, user_id=user.id,
                kind=kind, link_type=link,
            )
        client = APIClient()
        client.force_authenticate(user)
        inbox = client.get('/api/v1/notifications/').json()['results']
        self.assertEqual(sorted(i['notification']['category'] for i in inbox),
                         ['announcement', 'assignment', 'lesson_reminder', 'submission'])
        self.assertEqual(client.get('/api/v1/notifications/unread-count/').json()['count'], 4)
        self.assertEqual(client.post('/api/v1/notifications/read-all/').json(), {'updated': 4})
        self.assertEqual(client.get('/api/v1/notifications/unread-count/').json()['count'], 0)
        self.assertEqual(client.post('/api/v1/notifications/read-all/').json(), {'updated': 0})


class ChatEventsOverWebSocketTests(TransactionTestCase):
    """Yangi hodisalar (`read`, `message_deleted`, `pinned`, `reaction`, `room_updated`) WebSocket orqali keladi;
    ulanish onlayn belgisini qo'yadi/olib tashlaydi; WS orqali javob (`reply_to_id`) yuborish mumkin."""

    def setUp(self):
        self.teacher = make('ev_t', User.Role.TEACHER)
        self.student = make('ev_s', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Events')
        self.room = services.ensure_course_room(self.course)
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)

    async def _connect(self, user):
        from channels.testing import WebsocketCommunicator
        from rest_framework_simplejwt.tokens import AccessToken

        from root.asgi import application

        comm = WebsocketCommunicator(application, f'/ws/chat/{self.room.id}/?token={AccessToken.for_user(user)}')
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        return comm

    async def frames(self, comm, count):
        return [await comm.receive_json_from(timeout=3) for _ in range(count)]

    async def test_events_reach_the_room_and_presence_follows_the_connection(self):
        from channels.db import database_sync_to_async

        student = await self._connect(self.student)
        teacher = await self._connect(self.teacher)
        # onlayn belgisi ulanish tugallangach qo'yiladi (consumer connect'ining oxirida)
        await student.send_json_to({'type': 'typing'})
        await teacher.receive_json_from(timeout=3)
        await student.receive_json_from(timeout=3)  # o'zining `typing`i ham guruhga qaytadi
        self.assertEqual(presence.online_ids([self.student.id, self.teacher.id]), {str(self.student.id), str(self.teacher.id)})

        sent = await database_sync_to_async(services.send_message)(user=self.student, room_id=self.room.id, text='savol')
        await teacher.receive_json_from(timeout=3)
        await database_sync_to_async(services.read_room)(user=self.teacher, room_id=self.room.id)
        event = await student.receive_json_from(timeout=3)  # oldingi `message` hodisasi
        self.assertEqual(event['type'], 'message')
        event = await student.receive_json_from(timeout=3)
        self.assertEqual((event['type'], event['last_message_id']), ('read', str(sent.id)))

        await database_sync_to_async(services.pin_message)(user=self.teacher, room_id=self.room.id, message_id=sent.id)
        legacy, new = await self.frames(student, 2)  # eski nom + yangi `{type, payload}`
        self.assertEqual((legacy['type'], legacy['message']['text']), ('pinned', 'savol'))
        self.assertEqual(new['type'], 'room_pinned_changed')
        self.assertEqual([m['message_id'] for m in new['payload']['pinned_messages']], [str(sent.id)])

        await database_sync_to_async(services.toggle_reaction)(user=self.teacher, message_id=sent.id, emoji='🔥')
        legacy, new = await self.frames(student, 2)
        self.assertEqual((legacy['type'], legacy['emoji'], legacy['count']), ('reaction', '🔥', 1))
        self.assertEqual((new['type'], new['payload']['reactions'][0]['count']), ('message_reaction', 1))

        await database_sync_to_async(services.delete_messages)(user=self.teacher, ids=[sent.id], scope='everyone')
        events = await self.frames(student, 4)  # qadash olinadi (2) + o'chirish (2)
        self.assertEqual(
            {e['type'] for e in events}, {'pinned', 'room_pinned_changed', 'message_deleted', 'messages_removed'},
        )

        await student.disconnect()
        await teacher.disconnect()
        self.assertEqual(presence.online_ids([self.student.id, self.teacher.id]), set())

    async def test_reply_and_idempotency_over_the_socket(self):
        from channels.db import database_sync_to_async

        first = await database_sync_to_async(services.send_message)(user=self.teacher, room_id=self.room.id, text='asl')
        student = await self._connect(self.student)
        teacher = await self._connect(self.teacher)
        payload = {'type': 'message', 'text': 'javob', 'reply_to_id': str(first.id), 'client_message_id': 'ws-1'}
        await student.send_json_to(payload)
        event = await teacher.receive_json_from(timeout=3)
        self.assertEqual(event['message']['reply_to']['id'], str(first.id))
        self.assertEqual(event['message']['client_message_id'], 'ws-1')
        await student.send_json_to(payload)  # qayta yuborish — dublikat yaratmaydi
        await student.send_json_to({'type': 'typing'})
        self.assertEqual((await teacher.receive_json_from(timeout=3))['type'], 'typing')
        count = await database_sync_to_async(lambda: Message.objects.filter(room=self.room, text='javob').count())()
        self.assertEqual(count, 1)
        await student.disconnect()
        await teacher.disconnect()
