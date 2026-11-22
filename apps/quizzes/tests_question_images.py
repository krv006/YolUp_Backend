"""Savol rasmi (`POST /quizzes/question-images/`), rasmdan keyingi matn va matndan import (`/quizzes/import-text/`)."""
import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from apps.accounts.tests import login, register
from apps.quizzes.models import Question, QuestionImage
from apps.quizzes.tests_question_types import QuizTestBase

_MEDIA = tempfile.mkdtemp(prefix='quiz-img-tests-')


def tearDownModule():
    shutil.rmtree(_MEDIA, ignore_errors=True)


def image_file(fmt='PNG', name='rasm.png', size=(40, 30)):
    buffer = BytesIO()
    Image.new('RGB', size, (69, 103, 245)).save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f'image/{fmt.lower()}')


SINGLE = {'type': 'single', 'text': 'Rasmdagi shakl nima?', 'options': [
    {'text': 'Doira', 'is_correct': True}, {'text': 'Kvadrat', 'is_correct': False}]}


@override_settings(MEDIA_ROOT=_MEDIA)
class QuestionImageTests(QuizTestBase):
    def upload(self, upload=None, token=None):
        self.auth(token or self.teacher_token)
        return self.client.post(
            '/api/v1/quizzes/question-images/', {'file': upload or image_file()}, format='multipart',
        )

    def test_teacher_uploads_png_and_gets_id_and_url(self):
        resp = self.upload()
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertTrue(body['url'].endswith('.png'))
        self.assertIn('/media/quiz_images/', body['url'])
        self.assertEqual(QuestionImage.objects.count(), 1)

    def test_other_formats_are_accepted_and_named_by_real_format(self):
        for fmt, ext in (('JPEG', '.jpg'), ('GIF', '.gif'), ('WEBP', '.webp')):
            resp = self.upload(image_file(fmt, 'x.png'))  # kengaytma yolg'on — format Pillow bo'yicha aniqlanadi
            self.assertEqual(resp.status_code, 201, (fmt, resp.content))
            self.assertTrue(resp.json()['url'].endswith(ext), resp.json()['url'])

    def test_non_image_is_rejected(self):
        fake = SimpleUploadedFile('virus.png', b'<?php echo 1; ?>', content_type='image/png')
        resp = self.upload(fake)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('file', resp.json()['error']['details'])
        self.assertEqual(QuestionImage.objects.count(), 0)

    def test_unsupported_image_format_is_rejected(self):
        resp = self.upload(image_file('BMP', 'x.bmp'))
        self.assertEqual(resp.status_code, 400)

    def test_too_large_file_is_rejected(self):
        big = SimpleUploadedFile('big.png', b'0' * (5 * 1024 * 1024 + 1), content_type='image/png')
        resp = self.upload(big)
        self.assertEqual(resp.status_code, 400)

    def test_missing_file_is_rejected(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/question-images/', {}, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_student_cannot_upload(self):
        resp = self.upload(token=self.child_token)
        self.assertEqual(resp.status_code, 403)

    def test_question_keeps_image_and_text_after_for_teacher_and_student(self):
        image_id = self.upload().json()['id']
        question = {**SINGLE, 'text': 'Rasmga qarang.', 'image': image_id, 'text_after': 'Bu qanday shakl?'}
        created = self.make_quiz([question])
        self.assertEqual(created.status_code, 201, created.content)
        quiz_id = created.json()['id']

        self.auth(self.teacher_token)
        detail = self.client.get(f'/api/v1/quizzes/{quiz_id}/').json()['questions'][0]
        self.assertEqual(detail['text'], 'Rasmga qarang.')
        self.assertEqual(detail['text_after'], 'Bu qanday shakl?')
        self.assertEqual(detail['image']['id'], image_id)
        self.assertIn('/media/quiz_images/', detail['image']['url'])

        taken = self.take(quiz_id)['questions'][0]
        self.assertEqual(taken['text_after'], 'Bu qanday shakl?')
        self.assertIn('/media/quiz_images/', taken['image'])
        self.assertNotIn('is_correct', str(taken))

    def test_question_without_image_has_null_image_and_empty_text_after(self):
        quiz_id = self.make_quiz([SINGLE]).json()['id']
        self.auth(self.teacher_token)
        detail = self.client.get(f'/api/v1/quizzes/{quiz_id}/').json()['questions'][0]
        self.assertIsNone(detail['image'])
        self.assertEqual(detail['text_after'], '')
        self.assertIsNone(self.take(quiz_id)['questions'][0]['image'])

    def test_cannot_attach_someone_elses_image(self):
        image_id = self.upload().json()['id']
        register(self.client, 't2', 'teacher')
        other = login(self.client, 't2')
        self.auth(other)
        resp = self.client.post('/api/v1/quizzes/', {
            'topic': 'Boshqa', 'title': 'T', 'questions': [{**SINGLE, 'image': image_id}],
        }, format='json')
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(Question.objects.filter(image_id=image_id).count(), 0)

    def test_unknown_image_id_is_rejected(self):
        resp = self.make_quiz([{**SINGLE, 'image': '00000000-0000-0000-0000-000000000000'}])
        self.assertEqual(resp.status_code, 400)

    def test_editing_questions_keeps_image_when_id_is_sent_again(self):
        image_id = self.upload().json()['id']
        quiz_id = self.make_quiz([{**SINGLE, 'image': image_id, 'text_after': 'pastda'}], ).json()['id']
        self.auth(self.teacher_token)
        patched = self.client.patch(f'/api/v1/quizzes/{quiz_id}/', {
            'questions': [{**SINGLE, 'text': 'Yangi matn', 'image': image_id, 'text_after': 'yangi pastki matn'}],
        }, format='json')
        self.assertEqual(patched.status_code, 200, patched.content)
        question = patched.json()['questions'][0]
        self.assertEqual(question['image']['id'], image_id)
        self.assertEqual(question['text_after'], 'yangi pastki matn')
        self.assertEqual(QuestionImage.objects.filter(pk=image_id).count(), 1)

    def test_replacing_questions_without_image_detaches_but_keeps_file_row(self):
        image_id = self.upload().json()['id']
        quiz_id = self.make_quiz([{**SINGLE, 'image': image_id}]).json()['id']
        self.auth(self.teacher_token)
        patched = self.client.patch(f'/api/v1/quizzes/{quiz_id}/', {'questions': [SINGLE]}, format='json')
        self.assertEqual(patched.status_code, 200, patched.content)
        self.assertIsNone(patched.json()['questions'][0]['image'])
        self.assertEqual(QuestionImage.objects.filter(pk=image_id).count(), 1)

    def test_null_image_is_allowed(self):
        resp = self.make_quiz([{**SINGLE, 'image': None}])
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_deleting_image_row_removes_file(self):
        image = QuestionImage.objects.get(pk=self.upload().json()['id'])
        path = image.file.path
        image.delete()
        import os
        self.assertFalse(os.path.exists(path))


TEXT = (
    "Ingliz tili nazorati\n\n"
    "1. She ___ in London since 2019.\n"
    "A) lives\n"
    "B) has lived\n"
    "To'g'ri javob: B\n\n"
    "2. Qaysi biri to'g'ri?\n"
    "A) Bir\n"
    "B) Ikki\n"
    "C) Uch\n"
)


class TextImportTests(QuizTestBase):
    def test_preview_from_pasted_text(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/import-text/', {'text': TEXT}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(len(body['questions']), 2)
        self.assertTrue(body['questions'][0]['options'][1]['is_correct'])
        self.assertEqual(len(body['warnings']), 1)  # 2-savolda javob qatori yo'q

    def test_text_with_topic_saves_draft_quiz(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/import-text/', {'text': TEXT, 'topic': 'Joylangan'}, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body['status'], 'draft')
        self.assertEqual(len(body['questions']), 2)

    def test_empty_text_is_rejected(self):
        self.auth(self.teacher_token)
        for text in ('', '   \n  '):
            resp = self.client.post('/api/v1/quizzes/import-text/', {'text': text}, format='json')
            self.assertEqual(resp.status_code, 400, text)

    def test_text_without_questions_is_rejected(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/import-text/', {'text': 'Shunchaki gap, savol yo\'q.'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('text', resp.json()['error']['details'])

    def test_too_long_text_is_rejected(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/import-text/', {'text': 'x' * 100_001}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_student_cannot_import(self):
        self.auth(self.child_token)
        resp = self.client.post('/api/v1/quizzes/import-text/', {'text': TEXT}, format='json')
        self.assertEqual(resp.status_code, 403)
