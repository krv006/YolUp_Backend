"""Savollar guruhi: umumiy matn parchasi (Reading/SAT) va audio (Listening)."""
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from .models import Question, QuestionGroup
from .tests_question_types import QuizTestBase

SINGLE = {'type': 'single', 'points': 2, 'options': [
    {'text': "to'g'ri", 'is_correct': True}, {'text': 'xato', 'is_correct': False}]}


def q(text, group=None):
    data = {**SINGLE, 'text': text}
    if group is not None:
        data['group'] = group
    return data


class GroupTestBase(QuizTestBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)

    def create_grouped(self, **extra):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/', {
            'course': self.course_id, 'topic': 'Reading', 'title': 'R1',
            'groups': [
                {'title': 'Passage 1', 'passage': "Birinchi matn parchasi."},
                {'title': 'Passage 2', 'passage': 'Ikkinchi parcha.'},
            ],
            'questions': [q('Q1', 0), q('Q2', 0), q('Q3', 1), q('Q4')],
            **extra,
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()

    def audio(self, name='listening.mp3', size=2048):
        return SimpleUploadedFile(name, b'\x00' * size, content_type='audio/mpeg')

    def upload(self, quiz_id, group_id, upload=None, token=None):
        self.auth(token or self.teacher_token)
        return self.client.post(
            f'/api/v1/quizzes/{quiz_id}/groups/{group_id}/audio/',
            {'file': upload or self.audio()}, format='multipart',
        )


class GroupCreateTests(GroupTestBase):
    def test_questions_are_linked_to_groups(self):
        body = self.create_grouped()
        self.assertEqual([g['title'] for g in body['groups']], ['Passage 1', 'Passage 2'])
        self.assertEqual(body['groups'][0]['passage'], 'Birinchi matn parchasi.')
        self.assertIsNone(body['groups'][0]['audio_url'])
        by_text = {x['text']: x['group'] for x in body['questions']}
        g1, g2 = body['groups'][0]['id'], body['groups'][1]['id']
        self.assertEqual(by_text, {'Q1': g1, 'Q2': g1, 'Q3': g2, 'Q4': None})

    def test_student_sees_passages_but_no_answer_key(self):
        body = self.create_grouped()
        take = self.take(body['id'])
        self.assertEqual(take['groups'][0]['passage'], 'Birinchi matn parchasi.')
        self.assertEqual(take['questions'][0]['group'], body['groups'][0]['id'])
        text = str(take)
        self.assertNotIn('is_correct', text)

    def test_quiz_without_groups_still_works(self):
        resp = self.make_quiz([q('Faqat savol')])
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['groups'], [])
        self.assertIsNone(resp.json()['questions'][0]['group'])

    def test_question_pointing_to_missing_group_is_rejected(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/quizzes/', {
            'course': self.course_id, 'topic': 'T', 'questions': [q('Q', 3)],
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(QuestionGroup.objects.count(), 0)


class GroupAudioTests(GroupTestBase):
    def test_upload_returns_absolute_url_and_stores_file(self):
        body = self.create_grouped()
        group_id = body['groups'][0]['id']
        resp = self.upload(body['id'], group_id)
        self.assertEqual(resp.status_code, 200, resp.content)
        url = resp.json()['audio_url']
        self.assertTrue(url.startswith('http'), url)
        self.assertIn('/media/quiz_audio/', url)
        self.assertTrue(url.endswith('.mp3'))
        stored = list((Path(self.media) / 'quiz_audio').glob('*.mp3'))
        self.assertEqual(len(stored), 1)
        # o'quvchi ham audio manzilini ko'radi
        self.assertEqual(self.take(body['id'])['groups'][0]['audio_url'], url)

    def test_replace_removes_previous_file(self):
        body = self.create_grouped()
        group_id = body['groups'][0]['id']
        self.upload(body['id'], group_id)
        self.upload(body['id'], group_id, self.audio('new.wav'))
        files = list((Path(self.media) / 'quiz_audio').iterdir())
        self.assertEqual([f.suffix for f in files], ['.wav'])

    def test_rejects_bad_extension_and_oversize(self):
        body = self.create_grouped()
        group_id = body['groups'][0]['id']
        self.assertEqual(self.upload(body['id'], group_id, self.audio('x.exe')).status_code, 400)
        with patch('apps.quizzes.services.MAX_AUDIO_MB', 0):
            self.assertEqual(self.upload(body['id'], group_id).status_code, 400)
        self.assertFalse(QuestionGroup.objects.get(pk=group_id).audio)

    def test_only_the_owner_can_upload(self):
        body = self.create_grouped()
        group_id = body['groups'][0]['id']
        self.assertEqual(self.upload(body['id'], group_id, token=self.child_token).status_code, 403)
        self.assertEqual(self.upload(body['id'], group_id, token=self.parent_token).status_code, 403)

    def test_delete_audio(self):
        body = self.create_grouped()
        group_id = body['groups'][0]['id']
        self.upload(body['id'], group_id)
        self.auth(self.teacher_token)
        resp = self.client.delete(f'/api/v1/quizzes/{body["id"]}/groups/{group_id}/audio/')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(QuestionGroup.objects.get(pk=group_id).audio)
        self.assertEqual(list((Path(self.media) / 'quiz_audio').iterdir()), [])

    def test_deleting_the_quiz_removes_audio_files(self):
        body = self.create_grouped()
        self.upload(body['id'], body['groups'][0]['id'])
        self.auth(self.teacher_token)
        self.assertEqual(self.client.delete(f'/api/v1/quizzes/{body["id"]}/').status_code, 204)
        self.assertEqual(list((Path(self.media) / 'quiz_audio').iterdir()), [])


class GroupEditTests(GroupTestBase):
    def patch(self, quiz_id, payload):
        self.auth(self.teacher_token)
        return self.client.patch(f'/api/v1/quizzes/{quiz_id}/', payload, format='json')

    def test_replacing_questions_keeps_groups_and_audio_when_id_is_sent(self):
        body = self.create_grouped()
        g1 = body['groups'][0]
        self.upload(body['id'], g1['id'])
        resp = self.patch(body['id'], {
            'groups': [{'id': g1['id'], 'title': 'Passage 1 (yangi)', 'passage': 'Yangilangan matn'}],
            'questions': [q('Yangi Q1', 0), q('Yangi Q2', 0)],
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(len(data['groups']), 1)
        self.assertEqual(data['groups'][0]['id'], g1['id'])
        self.assertEqual(data['groups'][0]['passage'], 'Yangilangan matn')
        self.assertTrue(data['groups'][0]['audio_url'])
        self.assertEqual({x['group'] for x in data['questions']}, {g1['id']})
        # ikkinchi guruh o'chirildi
        self.assertEqual(QuestionGroup.objects.count(), 1)

    def test_replacing_questions_without_groups_keeps_existing_groups_by_position(self):
        body = self.create_grouped()
        g1 = body['groups'][0]
        self.upload(body['id'], g1['id'])
        resp = self.patch(body['id'], {'questions': [q('A', 1), q('B', 0)]})
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual([g['id'] for g in data['groups']], [g['id'] for g in body['groups']])
        self.assertTrue(data['groups'][0]['audio_url'])
        by_text = {x['text']: x['group'] for x in data['questions']}
        self.assertEqual(by_text, {'A': body['groups'][1]['id'], 'B': body['groups'][0]['id']})

    def test_groups_only_update_edits_passage_without_touching_questions(self):
        body = self.create_grouped()
        g1, g2 = body['groups']
        resp = self.patch(body['id'], {'groups': [{'id': g1['id'], 'passage': 'Faqat matn o\'zgardi'}]})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(Question.objects.filter(quiz_id=body['id']).count(), 4)
        # olib tashlangan guruhning savollari guruhsiz qoldi
        orphaned = Question.objects.get(quiz_id=body['id'], text='Q3')
        self.assertIsNone(orphaned.group_id)
        self.assertEqual(QuestionGroup.objects.get(pk=g1['id']).passage, "Faqat matn o'zgardi")
        self.assertFalse(QuestionGroup.objects.filter(pk=g2['id']).exists())

    def test_removing_a_group_deletes_its_audio(self):
        body = self.create_grouped()
        g2 = body['groups'][1]
        self.upload(body['id'], g2['id'])
        self.patch(body['id'], {'groups': [{'id': body['groups'][0]['id']}]})
        self.assertEqual(list((Path(self.media) / 'quiz_audio').iterdir()), [])

    def test_group_ids_must_belong_to_this_quiz(self):
        body = self.create_grouped()
        other = self.create_grouped()
        resp = self.patch(body['id'], {'groups': [{'id': other['groups'][0]['id'], 'title': 'x'}]})
        self.assertEqual(resp.status_code, 200)
        # begona id e'tiborsiz qoldiriladi — yangi guruh yaratiladi, boshqa testniki o'zgarmaydi
        self.assertNotEqual(resp.json()['groups'][0]['id'], other['groups'][0]['id'])
        self.assertEqual(QuestionGroup.objects.get(pk=other['groups'][0]['id']).title, 'Passage 1')


class ExamGroupsTests(GroupTestBase):
    def test_exam_current_includes_groups_and_audio(self):
        from apps.exams.models import Exam

        body = self.create_grouped()
        self.upload(body['id'], body['groups'][0]['id'])
        self.auth(self.teacher_token)
        starts = (timezone.now() + timedelta(hours=2)).isoformat()
        resp = self.client.post('/api/v1/exams/', {
            'course': self.course_id, 'template': 'milliy', 'title': 'Reading mock', 'starts_at': starts,
            'sections': [{'key': 'main', 'quiz': body['id']}],
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        Exam.objects.update(
            starts_at=timezone.now() - timedelta(minutes=1),
            ends_at=timezone.now() + timedelta(minutes=149),
        )
        self.auth(self.child_token)
        item = self.client.get(f'/api/v1/exams/{resp.json()["id"]}/current/').json()['item']
        self.assertEqual([g['title'] for g in item['groups']], ['Passage 1', 'Passage 2'])
        self.assertTrue(item['groups'][0]['audio_url'].startswith('http'))
        self.assertIn(item['groups'][0]['id'], {x['group'] for x in item['questions']})
