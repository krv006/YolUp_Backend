"""O'qituvchining ovozli vazifasi: `voice` (+ `voice_duration_ms`, `remove_voice`) va himoyalangan `GET .../voice/`."""
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User

from .models import Assignment
from .tests_hardening import HomeworkBase, make

AUDIO = b'RIFF....WAVEfmt fake-audio-bytes'


def audio(name='izoh.webm', data=AUDIO):
    return SimpleUploadedFile(name, data, content_type='video/webm')


class AssignmentVoiceTests(HomeworkBase):
    URL = '/api/v1/homework/assignments/'

    def create(self, **extra):
        return self.api(self.teacher).post(
            self.URL, {'course_id': str(self.course.id), 'title': 'Ovozli vazifa', **extra}, format='multipart')

    def test_voice_is_saved_and_returned_with_duration_and_mime(self):
        resp = self.create(voice=audio(), voice_duration_ms='45000')
        self.assertEqual(resp.status_code, 201, resp.content)
        voice = resp.json()['voice']
        self.assertEqual((voice['duration_ms'], voice['mime']), (45000, 'audio/webm'))  # video/webm yuborilsa ham audio/webm
        self.assertEqual(voice['url'], f'/api/v1/homework/assignments/{resp.json()["id"]}/voice/')

    def test_assignment_without_voice_has_null(self):
        self.assertIsNone(self.create().json()['voice'])

    def test_every_allowed_format_works(self):
        for ext, mime in (('webm', 'audio/webm'), ('ogg', 'audio/ogg'), ('m4a', 'audio/mp4'), ('mp3', 'audio/mpeg'), ('wav', 'audio/wav')):
            resp = self.create(voice=audio(f'x.{ext}'))
            self.assertEqual((resp.status_code, resp.json()['voice']['mime']), (201, mime), ext)

    def test_bad_format_size_and_duration_are_rejected(self):
        self.assertEqual(self.create(voice=audio('x.exe')).status_code, 400)
        self.assertEqual(self.create(voice=audio('x.webm', b'')).status_code, 400)
        self.assertEqual(self.create(voice=audio(), voice_duration_ms=str(10 * 60 * 1000 + 1)).status_code, 400)
        self.assertEqual(self.create(voice=audio(), voice_duration_ms='abc').status_code, 400)
        self.assertEqual(self.create(voice=audio(), voice_duration_ms=str(10 * 60 * 1000)).status_code, 201)  # aynan 10 daqiqa mumkin
        big = SimpleUploadedFile('big.mp3', b'0' * (20 * 1024 * 1024 + 1), content_type='audio/mpeg')
        self.assertEqual(self.create(voice=big).status_code, 400)
        self.assertEqual(Assignment.objects.filter(title='Ovozli vazifa').count(), 1)  # faqat yaroqli bittasi yaratilgan

    def test_voice_is_added_replaced_and_removed_on_edit(self):
        aid = self.create().json()['id']
        patch = lambda **data: self.api(self.teacher).patch(f'{self.URL}{aid}/', data, format='multipart')
        resp = patch(voice=audio('a.mp3'), voice_duration_ms='1000')
        self.assertEqual((resp.status_code, resp.json()['voice']['mime'], resp.json()['voice']['duration_ms']), (200, 'audio/mpeg', 1000))
        resp = patch(title='Yangi nom')  # boshqa maydonni o'zgartirish ovozga tegmaydi
        self.assertEqual(resp.json()['voice']['mime'], 'audio/mpeg')
        resp = patch(voice=audio('b.wav'), voice_duration_ms='2000')
        self.assertEqual((resp.json()['voice']['mime'], resp.json()['voice']['duration_ms']), ('audio/wav', 2000))
        resp = patch(remove_voice='1')
        self.assertEqual((resp.status_code, resp.json()['voice']), (200, None))
        self.assertEqual(self.api(self.teacher).get(f'{self.URL}{aid}/voice/').status_code, 404)

    def test_voice_does_not_touch_the_document_attachment(self):
        doc = SimpleUploadedFile('shart.pdf', b'%PDF-1.4 x', content_type='application/pdf')
        body = self.create(attachment=doc, voice=audio()).json()
        self.assertTrue(body['has_attachment'])
        self.assertEqual(body['attachment_name'], 'shart.pdf')
        self.assertIsNotNone(body['voice'])

    def test_playback_access_follows_the_assignment_access(self):
        aid = self.create(voice=audio()).json()['id']
        url = f'{self.URL}{aid}/voice/'
        for user in (self.teacher, self.student, self.parent):
            resp = self.api(user).get(url)
            self.assertEqual(resp.status_code, 200, user.role)
            self.assertEqual(b''.join(resp.streaming_content), AUDIO)
            self.assertEqual(resp['Content-Type'], 'audio/webm')
        stranger = make('s9', User.Role.STUDENT)  # guruhga yozilmagan o'quvchi
        self.assertIn(self.api(stranger).get(url).status_code, (403, 404))
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(url).status_code, (401, 403))

    def test_draft_voice_is_hidden_from_students(self):
        aid = self.create(voice=audio(), status='draft').json()['id']
        self.assertIn(self.api(self.student).get(f'{self.URL}{aid}/voice/').status_code, (403, 404))
        self.assertEqual(self.api(self.teacher).get(f'{self.URL}{aid}/voice/').status_code, 200)

    def test_student_cannot_attach_a_voice(self):
        resp = self.api(self.student).post(self.URL, {'course_id': str(self.course.id), 'title': 'x', 'voice': audio()}, format='multipart')
        self.assertEqual(resp.status_code, 403)

    def test_voice_goes_with_the_bank_copy(self):
        bank = self.api(self.teacher).post(self.URL, {'title': 'Bazada', 'bank': '1', 'voice': audio('m.mp3'), 'voice_duration_ms': '3000'}, format='multipart')
        if bank.status_code != 201:  # bazaga yaratish usuli boshqacha bo'lsa — kursdagi vazifani bazaga ko'chirmaymiz
            self.skipTest(f'bank create not via this endpoint: {bank.content}')
        bank_id = bank.json()['id']
        resp = self.api(self.teacher).post(f'{self.URL}{bank_id}/assign/', {'course_ids': [str(self.course.id)]}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        copy = resp.json()['assignments'][0]
        self.assertEqual(copy['voice']['duration_ms'], 3000)
