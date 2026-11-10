"""Yozuvni guruhga yuborish ixtiyoriy (20) va MP4 tayyor bo'lguncha yozuv yopiq (21) — 2026-11-10."""
from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.chat.models import Message
from apps.live import services as live_services

from . import services, transcode
from .models import LessonRecording
from .tests_transcode import RecordingBase


class GateBase(RecordingBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def info(self, user, recording):
        self.client.force_authenticate(user)
        return self.client.get(f'/api/v1/lessons/{recording.lesson_id}/recording/')

    def announcements(self):
        return Message.objects.filter(system_key='recording_ready').count()

    def ready(self, recording):
        """Yozuv fayli tayyor bo'ldi (merge/finalize oxiri) — e'lon qilish yoki konvertatsiyani kutish qarori."""
        recording.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True):
            live_services.recording_became_ready(recording)

    def convert(self, recording, **fake_kwargs):
        with self.captureOnCommitCallbacks(execute=True), patch(
            'apps.lessons.transcode.subprocess.run', side_effect=self.fake_ffmpeg(**fake_kwargs),
        ):
            return transcode.convert(recording.pk)


class PostRecordingFlagTests(GateBase):
    def test_finish_stores_the_choice_and_defaults_to_posting(self):
        for value, expected in ((None, True), ('true', True), (False, False), ('false', False), ('0', False)):
            recording = self.recording(name='')
            lesson = recording.lesson
            lesson.status = 'live'
            lesson.save(update_fields=['status'])
            self.client.force_authenticate(self.teacher)
            body = {} if value is None else {'post_recording': value}
            resp = self.client.post(f'/api/v1/lessons/{lesson.id}/finish/', body, format='json')
            self.assertEqual(resp.status_code, 200, resp.content)
            recording.refresh_from_db()
            self.assertEqual(recording.post_to_chat, expected, value)

    def test_nothing_is_announced_when_the_teacher_said_no_but_manual_share_still_works(self):
        recording = self.recording('done.mp4', post_to_chat=False)
        self.ready(recording)
        self.assertEqual(self.announcements(), 0)
        self.assertEqual(LessonRecording.objects.get(pk=recording.pk).announced_at, None)
        message = services.share_recording(teacher=self.teacher, lesson=recording.lesson)  # keyin qo'lda yuborish
        self.assertEqual(message.system_key, 'recording_ready')

    def test_info_exposes_the_flag(self):
        recording = self.recording(post_to_chat=False)
        self.assertEqual(self.info(self.teacher, recording).json()['post_to_chat'], False)


class ConversionGateTests(GateBase):
    def test_a_new_webm_recording_stays_closed_and_unannounced_until_the_mp4_is_ready(self):
        recording = self.recording()
        self.ready(recording)
        recording.refresh_from_db()
        self.assertTrue(recording.convert_required)
        self.assertEqual(self.announcements(), 0)
        for user in (self.student, self.teacher):  # o'qituvchiga ham yopiq
            body = self.info(user, recording).json()
            self.assertEqual((body['status'], body['ready'], body['stream_url']), ('converting', False, None))
        with self.assertRaises(Exception):
            services.recording_stream_path(lesson=recording.lesson, token='x')
        self.assertEqual(self.client.post(f'/api/v1/lessons/{recording.lesson_id}/recording/share/').status_code, 400)

    def test_conversion_opens_the_recording_and_announces_it_exactly_once(self):
        recording = self.recording()
        self.ready(recording)
        self.assertEqual(self.convert(recording), 'done')
        self.assertEqual(self.announcements(), 1)
        body = self.info(self.student, recording).json()
        self.assertEqual((body['status'], body['ready']), ('completed', True))
        self.assertIn('/recording/stream/?t=', body['stream_url'])
        recording.refresh_from_db()
        self.assertIsNotNone(recording.announced_at)
        with self.captureOnCommitCallbacks(execute=True):
            live_services._announce_recording_ready(recording)  # qayta chaqirish ikkinchi xabar yaratmaydi
        self.assertEqual(self.announcements(), 1)

    def test_a_failed_conversion_falls_back_to_the_original_webm_and_still_announces(self):
        recording = self.recording()
        self.ready(recording)
        self.assertEqual(self.convert(recording, fail=True), 'failed')
        body = self.info(self.student, recording).json()
        self.assertEqual((body['status'], body['ready']), ('completed', True))
        self.assertEqual(self.announcements(), 1)

    def test_an_mp4_recording_is_announced_at_once_and_never_gated(self):
        recording = self.recording('direct.mp4')
        self.ready(recording)
        recording.refresh_from_db()
        self.assertFalse(recording.convert_required)
        self.assertEqual(self.announcements(), 1)
        self.assertTrue(self.info(self.student, recording).json()['ready'])

    def test_old_recordings_keep_opening_as_webm_and_are_not_announced_again_after_conversion(self):
        recording = self.recording()  # convert_required=False: bu o'zgarishdan oldingi yozuv
        body = self.info(self.student, recording).json()
        self.assertEqual((body['status'], body['ready']), ('completed', True))
        self.assertEqual(self.convert(recording), 'done')
        self.assertEqual(self.announcements(), 0)

    def test_a_recording_hidden_for_too_long_opens_with_the_webm(self):
        recording = self.recording(convert_required=True, ended_at=timezone.now() - transcode.HIDE_MAX - timedelta(minutes=1))
        self.assertFalse(transcode.is_converting(recording))
        self.assertTrue(self.info(self.student, recording).json()['ready'])
        fresh = self.recording(convert_required=True, ended_at=timezone.now())
        self.assertTrue(transcode.is_converting(fresh))

    def test_students_do_not_see_a_converting_recording_in_the_materials_folder(self):
        recording = self.recording()
        self.ready(recording)
        self.client.force_authenticate(self.student)
        folder = self.client.get(f'/api/v1/materials/lessons/{recording.lesson_id}/').json()
        self.assertIsNone(folder['recording'])
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.get(f'/api/v1/materials/lessons/{recording.lesson_id}/').json()['recording']['status'], 'converting')
        self.convert(recording)
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get(f'/api/v1/materials/lessons/{recording.lesson_id}/').json()['recording']['status'], 'completed')


class LoadGuardTests(GateBase):
    def test_a_busy_server_postpones_conversion_until_the_max_wait_passes(self):
        fresh = self.recording(convert_required=True, ended_at=timezone.now())
        old = self.recording(convert_required=True, ended_at=timezone.now() - transcode.MAX_WAIT - timedelta(minutes=1))
        with patch('apps.lessons.transcode.system_busy', return_value=True):
            self.assertTrue(transcode.should_wait(fresh))
            self.assertFalse(transcode.should_wait(old))  # juda uzoq kutdi — baribir boshlanadi
        with patch('apps.lessons.transcode.system_busy', return_value=False):
            self.assertFalse(transcode.should_wait(fresh))

    def test_the_command_skips_a_waiting_recording_while_the_server_is_busy(self):
        recording = self.recording(convert_required=True, ended_at=timezone.now())
        with patch('apps.lessons.transcode.system_busy', return_value=True), patch('apps.lessons.transcode.convert') as convert:
            call_command('convert_recordings', verbosity=0)
        convert.assert_not_called()
        with patch('apps.lessons.transcode.system_busy', return_value=False), patch(
            'apps.lessons.transcode.convert', return_value='done',
        ) as convert:
            call_command('convert_recordings', verbosity=0)
        convert.assert_called_once_with(recording.pk)

    def test_load_average_is_compared_with_the_core_count(self):
        with patch('apps.lessons.transcode.os.getloadavg', return_value=(100.0, 0, 0)):
            self.assertTrue(transcode.system_busy())
        with patch('apps.lessons.transcode.os.getloadavg', return_value=(0.0, 0, 0)):
            self.assertFalse(transcode.system_busy())
