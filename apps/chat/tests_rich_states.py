"""Chatdagi boy holatlar (BACKEND_CHAT_RICH_STATES.md): vazifa xabari, e'lon rejimi, a'zolar va oxirgi faollik, Fayllar/Media,
bir nechta biriktirma, qidiruv (`limit`/`cursor`/`around`), xona `capabilities`."""
import io
from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.chat import presence, services
from apps.chat.models import Message, MessageAttachment
from apps.lessons.models import Course, Enrollment, Lesson

from .tests import make
from .tests_v2 import ChatV2Base, pdf_bytes


def body_of(response) -> bytes:
    """FileResponse oqimidan to'liq tana."""
    return b''.join(response.streaming_content)


def png(color='blue', size=(20, 20)):
    buffer = io.BytesIO()
    Image.new('RGB', size, color).save(buffer, format='PNG')
    return buffer.getvalue()


class HomeworkMessageTests(ChatV2Base):
    def assignment(self, **extra):
        from apps.homework import services as homework

        lesson = Lesson.objects.create(course=self.course, title='Kasrlar', starts_at=timezone.now(), status=Lesson.Status.FINISHED)
        return homework.create_assignment(
            teacher=self.teacher, course_id=self.course.id, title='112–118-misollar', description='Daftarga yeching',
            due_at=(timezone.now() + timedelta(days=2)).isoformat(), lesson_id=lesson.id, **extra,
        )

    def card(self, user):
        return next(m for m in self.messages(user, query='?mark_read=0').json() if m['type'] == 'homework')

    def test_auto_card_has_type_homework_and_full_assignment_data(self):
        created = self.assignment()
        card = self.card(self.student)
        self.assertEqual((card['type'], card['message_type']), ('homework', 'assignment'))
        data = card['assignment']
        self.assertEqual(
            (data['id'], data['title'], data['description'], data['files_count'], data['lesson_title'], data['total_count']),
            (created['id'], '112–118-misollar', 'Daftarga yeching', 0, 'Kasrlar', 2),
        )
        self.assertTrue(data['lesson_id'] and data['due_at'])
        self.assertIsNone(card['my_submission'])

    def test_my_submission_flips_for_the_student_who_submitted(self):
        from apps.homework.models import Assignment, Submission

        created = self.assignment()
        Submission.objects.create(
            assignment=Assignment.objects.get(pk=created['id']), student=self.student,
            file=SimpleUploadedFile('a.pdf', b'x'), original_name='a.pdf',
        )
        mine = self.card(self.student)['my_submission']
        self.assertEqual(mine['status'], 'checking')
        self.assertTrue(mine['id'] and mine['created_at'])
        self.assertIsNone(self.card(self.student2)['my_submission'])  # boshqa o'quvchi topshirmagan
        self.assertIsNone(self.card(self.teacher)['my_submission'])  # o'qituvchida bu maydon yo'q
        self.assertEqual(self.card(self.teacher)['assignment']['submitted_count'], 1)

    def test_teacher_can_post_an_existing_assignment_by_hand(self):
        created = self.assignment()
        url = f'{self.base}/rooms/{self.room.id}/messages/'
        resp = self.api(self.teacher).post(url, {'type': 'homework', 'assignment_id': created['id']}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual((resp.json()['type'], resp.json()['assignment']['id']), ('homework', created['id']))
        self.assertEqual(len([m for m in self.messages(self.student).json() if m['type'] == 'homework']), 2)
        self.assertEqual(self.api(self.student).post(url, {'type': 'homework', 'assignment_id': created['id']}, format='json').status_code, 403)
        bad = self.api(self.teacher).post(url, {'type': 'homework', 'assignment_id': 'nope'}, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_assignment_of_another_course_is_refused(self):
        from apps.homework import services as homework

        other_course = Course.objects.create(teacher=self.teacher, title='Boshqa kurs')
        foreign = homework.create_assignment(teacher=self.teacher, course_id=other_course.id, title='Boshqa')
        resp = self.api(self.teacher).post(
            f'{self.base}/rooms/{self.room.id}/messages/', {'type': 'homework', 'assignment_id': foreign['id']}, format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_to_messages_is_the_same_as_send(self):
        resp = self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/messages/', {'text': 'salom'}, format='json')
        self.assertEqual((resp.status_code, resp.json()['type'], resp.json()['text']), (201, 'text', 'salom'))


class AnnouncementModeTests(ChatV2Base):
    def patch(self, user, **data):
        return self.api(user).patch(f'{self.base}/rooms/{self.room.id}/', data, format='json')

    def test_new_name_alias_can_write_and_system_notice(self):
        self.assertTrue(self.room_info(self.student)['can_write'])
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.patch(self.teacher, announcement_mode=True)
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body['announcement_mode'], body['announcement_only'], body['can_write']), (True, True, True))
        student = self.room_info(self.student)
        self.assertEqual((student['announcement_mode'], student['can_write']), (True, False))
        notice = self.messages(self.student).json()[-1]
        self.assertEqual((notice['type'], notice['kind'], notice['system_key']), ('system', 'system', 'announcement_mode_on'))
        self.assertEqual(self.patch(self.student, announcement_mode=False).status_code, 403)
        self.assertEqual(self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/send/', {'text': 'x'}, format='json').status_code, 403)

    def test_notice_only_when_the_value_changes_and_old_name_still_works(self):
        self.patch(self.teacher, announcement_only=True)
        self.patch(self.teacher, announcement_mode=True)  # o'zgarmadi — yangi tizim xabari yo'q
        self.assertEqual([m['system_key'] for m in self.messages(self.teacher).json()], ['announcement_mode_on'])
        self.patch(self.teacher, announcement_mode=False)
        self.assertEqual(
            [m['system_key'] for m in self.messages(self.teacher).json()], ['announcement_mode_on', 'announcement_mode_off'],
        )
        self.assertTrue(self.room_info(self.student)['can_write'])
        self.assertEqual(self.patch(self.teacher).status_code, 400)

    def test_event_has_payload_and_old_fields(self):
        with mock.patch('apps.chat.realtime.broadcast_event') as broadcast, self.captureOnCommitCallbacks(execute=True):
            self.patch(self.teacher, announcement_mode=True)
        event = broadcast.call_args.args[1]
        self.assertEqual(event['type'], 'room_updated')
        self.assertEqual(event['payload'], {'room_id': str(self.room.id), 'announcement_mode': True, 'announcement_only': True})
        self.assertEqual((event['room'], event['announcement_only']), (str(self.room.id), True))

    def test_room_capabilities(self):
        self.assertEqual(self.room_info(self.teacher)['capabilities'], {'write': True, 'pin': True, 'announcement': True, 'delete': True})
        self.assertEqual(self.room_info(self.student)['capabilities'], {'write': True, 'pin': False, 'announcement': False, 'delete': False})
        self.patch(self.teacher, announcement_mode=True)
        self.assertFalse(self.room_info(self.student)['capabilities']['write'])
        direct = self.direct_room()
        self.assertEqual(self.room_info(self.student, direct)['capabilities'], {'write': True, 'pin': True, 'announcement': False, 'delete': False})


class MembersLastSeenTests(ChatV2Base):
    def members(self, user):
        return {m['username']: m for m in self.api(user).get(f'{self.base}/rooms/{self.room.id}/members/').json()}

    def test_member_rows_have_username_avatar_role_and_last_seen(self):
        rows = self.members(self.teacher)
        self.assertEqual(set(rows['s1']), {'id', 'name', 'username', 'role', 'is_online', 'avatar_url', 'avatar', 'last_seen_at'})
        self.assertEqual((rows['t1']['role'], rows['s1']['role']), ('teacher', 'student'))
        self.assertIsNone(rows['s1']['avatar'])

    def test_authenticated_requests_update_last_seen_with_a_throttle(self):
        self.assertIsNone(User.objects.get(username='s1').last_seen_at)
        self.client.force_authenticate(self.student)  # force_authenticate JWT'dan o'tmaydi — haqiqiy token bilan
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework.test import APIClient

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(self.student)}')
        self.assertEqual(client.get('/api/v1/auth/me/').status_code, 200)
        first = User.objects.get(username='s1').last_seen_at
        self.assertIsNotNone(first)
        client.get('/api/v1/auth/me/')  # 2 daqiqa ichida qayta yozilmaydi
        self.assertEqual(User.objects.get(username='s1').last_seen_at, first)
        self.assertIsNotNone(self.members(self.teacher)['s1']['last_seen_at'])

    def test_closing_the_connection_forces_a_last_seen_update(self):
        presence.touch_last_seen(self.student.id)
        before = User.objects.get(username='s1').last_seen_at
        presence.touch_last_seen(self.student.id, force=True)
        self.assertGreater(User.objects.get(username='s1').last_seen_at, before)


class MultipleAttachmentsTests(ChatV2Base):
    def upload(self, user, files, **extra):
        data = {'text': extra.pop('text', ''), 'files': [SimpleUploadedFile(n, c) for n, c in files], **extra}
        return self.api(user).post(f'{self.base}/rooms/{self.room.id}/messages/', data, format='multipart')

    def test_several_files_in_one_message(self):
        resp = self.upload(self.student, [('uy.pdf', pdf_bytes(3)), ('rasm.png', png()), ('jadval.xlsx', b'PK\x03\x04xlsx')], text='Mana')
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual((body['type'], body['text']), ('file', 'Mana'))  # aralash: fayl xabari
        items = body['attachments']
        self.assertEqual([i['name'] for i in items], ['uy.pdf', 'rasm.png', 'jadval.xlsx'])
        self.assertEqual([i['type'] for i in items], ['file', 'image', 'file'])
        self.assertEqual((items[0]['mime_type'], items[0]['page_count']), ('application/pdf', 3))
        self.assertEqual(items[1]['thumbnail_url'], items[1]['url'] + '?thumb=1')
        self.assertIsNone(items[0]['thumbnail_url'])
        self.assertEqual((body['file_name'], body['attachment']['name']), ('uy.pdf', 'uy.pdf'))  # eski maydonlar = birinchi fayl
        self.assertEqual(MessageAttachment.objects.filter(message_id=body['id']).count(), 3)

    def test_every_attachment_can_be_downloaded_by_members_only(self):
        body = self.upload(self.student, [('a.txt', b'birinchi'), ('b.txt', b'ikkinchi')]).json()
        contents = [body_of(self.api(self.teacher).get(i['url'])) for i in body['attachments']]
        self.assertEqual(contents, [b'birinchi', b'ikkinchi'])
        self.assertEqual(self.api(self.stranger).get(body['attachments'][1]['url']).status_code, 403)
        self.assertEqual(body_of(self.api(self.teacher).get(f"{self.base}/files/{body['id']}/")), b'birinchi')
        self.api(self.student).delete(f"{self.base}/messages/{body['id']}/?scope=everyone")
        self.assertEqual(self.api(self.teacher).get(body['attachments'][1]['url']).status_code, 404)

    def test_all_images_make_an_image_message_and_thumbnails_work(self):
        body = self.upload(self.student, [('a.png', png('red', (800, 600))), ('b.png', png('green'))]).json()
        self.assertEqual(body['type'], 'image')
        thumb = self.api(self.teacher).get(body['attachments'][0]['thumbnail_url'])
        self.assertEqual((thumb.status_code, thumb['Content-Type']), (200, 'image/jpeg'))
        small = Image.open(io.BytesIO(thumb.content))
        self.assertLessEqual(max(small.size), 320)
        full = self.api(self.teacher).get(body['attachments'][0]['url'])
        self.assertEqual(full['Content-Type'], 'image/png')

    def test_limits_and_validation(self):
        eleven = [(f'f{i}.txt', b'x') for i in range(11)]
        self.assertEqual(self.upload(self.student, eleven).status_code, 400)
        self.assertEqual(self.upload(self.student, [('ok.txt', b'x'), ('virus.exe', b'x')]).status_code, 400)
        self.assertEqual(Message.objects.filter(room=self.room).count(), 0)  # hech narsa yaratilmadi
        self.assertEqual(self.upload(self.student, [('a.txt', b'x'), ('b.png', b'bad')]).status_code, 400)

    def test_single_file_via_send_still_has_one_attachment_and_old_messages_are_listed(self):
        file = SimpleUploadedFile('eski.txt', b'salom')
        body = self.api(self.student).post(f'{self.base}/rooms/{self.room.id}/send/', {'file': file}, format='multipart').json()
        self.assertEqual([i['name'] for i in body['attachments']], ['eski.txt'])
        # qatorsiz (eski) xabar ham `attachments` da ko'rinadi
        legacy = Message.objects.create(room=self.room, sender=self.student, text='', file='chat_files/old.pdf', file_name='old.pdf', file_type='application/pdf', file_size=7)
        found = next(m for m in self.messages(self.teacher).json() if m['id'] == str(legacy.id))
        self.assertEqual((found['attachments'][0]['name'], found['attachments'][0]['url']), ('old.pdf', f'/api/v1/chat/files/{legacy.id}/'))

    def test_forward_keeps_all_attachments(self):
        body = self.upload(self.student, [('a.txt', b'bir'), ('b.txt', b'ikki')]).json()
        direct = self.direct_room()
        copy = self.api(self.teacher).post(
            f'{self.base}/messages/forward/', {'message_ids': [body['id']], 'target_room_ids': [str(direct.id)]}, format='json',
        ).json()[0]
        self.assertEqual([i['name'] for i in copy['attachments']], ['a.txt', 'b.txt'])
        self.assertEqual(body_of(self.api(self.student).get(copy['attachments'][1]['url'])), b'ikki')

    def test_voice_stays_single_and_is_not_listed_in_files(self):
        file = SimpleUploadedFile('v.webm', b'1234')
        voice = self.api(self.student).post(
            f'{self.base}/rooms/{self.room.id}/voice/', {'file': file, 'duration_ms': '2000'}, format='multipart',
        ).json()
        self.assertEqual((voice['type'], voice['attachments'][0]['type'], voice['attachments'][0]['duration_ms']), ('voice', 'voice', 2000))
        self.assertEqual(self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/attachments/?kind=file').json()['results'], [])
        two = self.api(self.student).post(
            f'{self.base}/rooms/{self.room.id}/send/',
            {'files': [SimpleUploadedFile('a.webm', b'1'), SimpleUploadedFile('b.webm', b'2')], 'message_type': 'voice', 'duration': '2'},
            format='multipart',
        )
        self.assertEqual(two.status_code, 400)


class FilesAndMediaTabsTests(ChatV2Base):
    def setUp(self):
        super().setUp()
        self.send_files(self.student, [('uy.pdf', pdf_bytes(2))])
        self.send_files(self.student2, [('rasm1.png', png()), ('rasm2.png', png('red'))])
        self.send_files(self.teacher, [('jadval.xlsx', b'PK\x03\x04x'), ('foto.jpg', b'bad')][:1])

    def send_files(self, user, files):
        resp = self.api(user).post(
            f'{self.base}/rooms/{self.room.id}/send/',
            {'files': [SimpleUploadedFile(n, c) for n, c in files]}, format='multipart',
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def tab(self, user, kind, query=''):
        resp = self.api(user).get(f'{self.base}/rooms/{self.room.id}/attachments/?kind={kind}{query}')
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def test_files_and_media_tabs(self):
        files = self.tab(self.teacher, 'file')
        self.assertEqual([f['name'] for f in files['results']], ['jadval.xlsx', 'uy.pdf'])  # yangilari birinchi
        self.assertEqual(files['count'], 2)
        media = self.tab(self.teacher, 'media')
        self.assertEqual([m['name'] for m in media['results']], ['rasm1.png', 'rasm2.png'])
        first = media['results'][0]
        self.assertEqual(
            set(first), {'id', 'message_id', 'name', 'mime_type', 'mime', 'size', 'url', 'thumbnail_url', 'page_count', 'created_at', 'sender'},
        )
        self.assertEqual((first['mime_type'], first['sender']['name']), ('image/png', 's3'))
        self.assertTrue(first['thumbnail_url'].endswith('?thumb=1'))
        self.assertIsNone(files['results'][0]['thumbnail_url'])

    def test_pagination_default_kind_and_errors(self):
        page = self.tab(self.teacher, 'media', '&page_size=1')
        self.assertEqual(len(page['results']), 1)
        default = self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/attachments/').json()
        self.assertEqual(default['count'], 2)  # standart: file
        self.assertEqual(self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/attachments/?kind=video').status_code, 400)
        self.assertEqual(self.api(self.stranger).get(f'{self.base}/rooms/{self.room.id}/attachments/?kind=file').status_code, 404)  # a'zo emas: xona ko'rinmaydi

    def test_deleted_and_hidden_messages_do_not_show_up(self):
        message = Message.objects.filter(file_name='uy.pdf').get()
        self.api(self.teacher).delete(f'{self.base}/messages/{message.id}/?scope=me')
        self.assertEqual([f['name'] for f in self.tab(self.teacher, 'file')['results']], ['jadval.xlsx'])
        self.assertEqual(self.tab(self.student, 'file')['count'], 2)  # boshqalarga ta'sir qilmaydi
        self.api(self.student).delete(f'{self.base}/messages/{message.id}/?scope=everyone')
        self.assertEqual(self.tab(self.student, 'file')['count'], 1)


class SearchCursorTests(ChatV2Base):
    def setUp(self):
        super().setUp()
        self.sent = [self.send(self.student, f'xabar 112 №{i}') for i in range(5)]
        self.send(self.student, 'boshqa')

    def search(self, query):
        resp = self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/messages/search/?q=112{query}')
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def test_limit_cursor_and_total(self):
        first = self.search('&limit=2')
        self.assertEqual(first['total'], 5)
        self.assertEqual([i['text'] for i in first['items']], ['xabar 112 №4', 'xabar 112 №3'])
        item = first['items'][0]
        self.assertEqual((item['message_id'], item['id'], item['cursor'], item['sender_name']), (self.sent[4]['id'],) * 3 + ('s1',))
        second = self.search(f'&limit=2&cursor={first["next_cursor"]}')
        self.assertEqual([i['text'] for i in second['items']], ['xabar 112 №2', 'xabar 112 №1'])
        last = self.search(f'&limit=2&cursor={second["next_cursor"]}')
        self.assertEqual(([i['text'] for i in last['items']], last['next_cursor']), (['xabar 112 №0'], None))
        self.assertEqual(self.search('')['total'], 5)  # eski chaqiruv o'zgarmagan
        bad = self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/messages/search/?q=112&cursor=nope')
        self.assertEqual(bad.status_code, 400)

    def test_around_returns_the_neighbourhood(self):
        target = self.sent[2]
        resp = self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/messages/?around={target["id"]}&limit=4&mark_read=1')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual([m['text'] for m in body['items']], ['xabar 112 №0', 'xabar 112 №1', 'xabar 112 №2', 'xabar 112 №3', 'xabar 112 №4'])
        self.assertEqual((body['has_more_before'], body['has_more_after']), (False, True))
        # `around` xonani o'qilgan deb belgilamaydi (qidiruvdan sakrash o'qilmaganlarni yo'qotmasin)
        self.assertEqual(self.room_info(self.teacher)['unread_count'], 6)

    def test_around_edges_and_errors(self):
        newest = self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/messages/?around={self.sent[0]["id"]}&limit=2').json()
        self.assertEqual((newest['items'][0]['text'], newest['has_more_before'], newest['has_more_after']), ('xabar 112 №0', False, True))
        self.assertEqual(self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/messages/?around=nope').status_code, 400)
        self.api(self.student).delete(f'{self.base}/messages/{self.sent[1]["id"]}/?scope=everyone')
        deleted = self.api(self.teacher).get(f'{self.base}/rooms/{self.room.id}/messages/?around={self.sent[1]["id"]}')
        self.assertEqual(deleted.status_code, 400)
        self.assertEqual(self.api(self.stranger).get(f'{self.base}/rooms/{self.room.id}/messages/?around={self.sent[0]["id"]}').status_code, 404)


class RoomUpdatedSocketTests(TransactionTestCase):
    async def test_socket_receives_room_updated_with_payload_and_the_system_notice(self):
        from channels.db import database_sync_to_async
        from channels.testing import WebsocketCommunicator
        from rest_framework_simplejwt.tokens import AccessToken

        from root.asgi import application

        teacher = await database_sync_to_async(make)('rs_t', User.Role.TEACHER)
        student = await database_sync_to_async(make)('rs_s', User.Role.STUDENT)
        course = await database_sync_to_async(Course.objects.create)(teacher=teacher, title='RS')
        room = await database_sync_to_async(services.ensure_course_room)(course)
        await database_sync_to_async(Enrollment.objects.create)(course=course, student=student, status='approved')
        comm = WebsocketCommunicator(application, f'/ws/chat/{room.id}/?token={AccessToken.for_user(student)}')
        connected, _ = await comm.connect()
        self.assertTrue(connected)
        await database_sync_to_async(services.set_announcement_only)(teacher=teacher, room_id=room.id, value=True)
        frames = [await comm.receive_json_from(timeout=3) for _ in range(2)]
        by_type = {f['type']: f for f in frames}
        self.assertEqual(by_type['room_updated']['payload']['announcement_mode'], True)
        self.assertEqual(by_type['message']['message']['type'], 'system')
        await comm.disconnect()
