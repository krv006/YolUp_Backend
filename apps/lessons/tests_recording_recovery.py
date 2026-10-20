"""Yozuv chidamliligi: bo'lak tartib raqami (takror yuborishdan himoya) va qotib qolgan/xato yozuvlarni avtomatik tiklash."""
import os
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.live import services as live_services

from .models import Course, Enrollment, Lesson, LessonRecording


def make(username, role):
    user = User(username=username, role=role)
    user.set_password('x')
    user.save()
    return user


class RecordingBase(APITestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        override = override_settings(RECORDINGS_DIR=self.tmp)
        override.enable()
        self.addCleanup(override.disable)
        self.teacher = make('rr_t', User.Role.TEACHER)
        self.student = make('rr_s', User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='Yozuv')
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)
        self.lesson = Lesson.objects.create(
            course=self.course, starts_at=timezone.now(), duration_min=45, status=Lesson.Status.LIVE,
        )

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def send(self, kind, data: bytes, user=None, **extra):
        chunk = SimpleUploadedFile('c.webm', data, content_type='video/webm')
        return self.api(user or self.teacher).post(
            f'/api/v1/lessons/{self.lesson.id}/recording/{kind}/', {'chunk': chunk, **extra}, format='multipart',
        )

    def raw(self, kind) -> bytes:
        recording = LessonRecording.objects.get(lesson=self.lesson)
        return (self.tmp / getattr(recording, f'{kind}_file_name')).read_bytes()


class ChunkSequenceTests(RecordingBase):
    def test_a_resent_chunk_is_not_written_twice(self):
        for kind in ('audio', 'video'):
            for index, data in ((0, b'AAAA'), (1, b'BBBB'), (1, b'BBBB'), (2, b'CCCC'), (0, b'AAAA')):
                resp = self.send(kind, data, session='s-1', index=index)
                self.assertEqual(resp.status_code, 204, resp.content)
            self.assertEqual(self.raw(kind), b'AAAABBBBCCCC')
        recording = LessonRecording.objects.get(lesson=self.lesson)
        self.assertEqual((recording.audio_next_index, recording.video_next_index), (3, 3))

    def test_a_new_session_starts_counting_again(self):
        self.send('video', b'AAAA', session='first', index=0)
        self.send('video', b'BBBB', session='first', index=1)
        self.send('video', b'CCCC', session='second', index=0)  # sahifa qayta ochildi: indeks 0 dan, bu takror emas
        self.send('video', b'CCCC', session='second', index=0)  # shu sessiyadagi takror
        self.send('video', b'DDDD', session='second', index=1)
        self.assertEqual(self.raw('video'), b'AAAABBBBCCCCDDDD')
        self.assertEqual(LessonRecording.objects.get(lesson=self.lesson).video_session, 'second')

    def test_old_clients_without_a_sequence_still_append_everything(self):
        for data in (b'AA', b'AA', b'BB'):
            self.assertEqual(self.send('audio', data).status_code, 204)
        self.assertEqual(self.raw('audio'), b'AAAABB')

    def test_a_gap_is_accepted_and_the_counter_follows(self):
        self.send('audio', b'AA', session='s', index=0)
        self.send('audio', b'CC', session='s', index=2)  # 1-bo'lak yo'q: baribir yoziladi (eng yaxshi urinish)
        self.send('audio', b'DD', session='s', index=2)  # endi takror
        self.assertEqual(self.raw('audio'), b'AACC')
        self.assertEqual(LessonRecording.objects.get(lesson=self.lesson).audio_next_index, 3)

    def test_bad_values_and_permissions(self):
        self.assertEqual(self.send('audio', b'A', session='s', index='x').status_code, 400)
        self.assertEqual(self.send('audio', b'A', session='s', index='-1').status_code, 400)
        self.assertEqual(self.send('audio', b'A', user=self.student, session='s', index=0).status_code, 403)
        self.assertFalse(LessonRecording.objects.exists())

    def test_naive_started_at_is_accepted(self):
        resp = self.send('audio', b'A', started_at='2026-08-27T10:00:00')
        self.assertEqual(resp.status_code, 204, resp.content)
        self.assertEqual(LessonRecording.objects.get().audio_started_at.isoformat(), '2026-08-27T10:00:00+00:00')


def make_video(path):
    subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=64x64:d=1', '-c:v', 'libvpx', '-t', '1', str(path)],
                   capture_output=True, check=True)


def make_audio(path):
    subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', '-c:a', 'libopus', str(path)],
                   capture_output=True, check=True)


class RecoveryTests(RecordingBase):
    def setUp(self):
        super().setUp()
        Lesson.objects.filter(pk=self.lesson.pk).update(status=Lesson.Status.FINISHED)
        self.lesson.refresh_from_db()
        self.old = timezone.now() - timedelta(hours=1)

    def recording(self, status, video=True, audio=True, **extra):
        if video:
            make_video(self.tmp / 'v.webm')
        if audio:
            make_audio(self.tmp / 'a.webm')
        recording = LessonRecording.objects.create(
            lesson=self.lesson, status=status, video_file_name='v.webm' if video else '',
            audio_file_name='a.webm' if audio else '', video_started_at=timezone.now(), audio_started_at=timezone.now(), **extra,
        )
        for name in ('v.webm', 'a.webm'):
            path = self.tmp / name
            if path.exists():
                os.utime(path, (self.old.timestamp(), self.old.timestamp()))
        LessonRecording.objects.filter(pk=recording.pk).update(updated_at=self.old)
        recording.refresh_from_db()
        return recording

    def test_failed_recording_with_both_files_is_merged_for_real(self):
        recording = self.recording(LessonRecording.Status.FAILED, error='Yozuv fayli yaratilmadi')
        with mock.patch('apps.live.services._announce_recording_ready'):
            report = live_services.recover_recordings()
        recording.refresh_from_db()
        self.assertEqual(report['merged'], 1)
        self.assertEqual((recording.status, recording.error, recording.merge_attempts), ('completed', '', 1))
        self.assertTrue((self.tmp / recording.file_name).stat().st_size > 0)
        self.assertIsNotNone(recording.video_ready_at)  # "tugadi" belgisi yo'q edi — qo'yildi

    def test_merge_killed_mid_way_is_recovered_only_after_the_stuck_window(self):
        recording = self.recording(LessonRecording.Status.MERGING)
        LessonRecording.objects.filter(pk=recording.pk).update(updated_at=timezone.now() - timedelta(minutes=5))
        with mock.patch('apps.live.services._merge_recording') as merge:
            self.assertEqual(live_services.recover_recordings()['merged'], 0)  # hali "qotmagan" — jarayon ishlayotgan bo'lishi mumkin
            merge.assert_not_called()
            LessonRecording.objects.filter(pk=recording.pk).update(updated_at=timezone.now() - timedelta(minutes=30))
            self.assertEqual(live_services.recover_recordings()['merged'], 1)
            merge.assert_called_once_with(recording.pk)

    def test_attempts_are_capped(self):
        recording = self.recording(LessonRecording.Status.FAILED, merge_attempts=live_services.MERGE_MAX_ATTEMPTS)
        with mock.patch('apps.live.services._merge_recording') as merge:
            self.assertEqual(live_services.recover_recordings(), {'merged': 0, 'single': 0, 'repaired': 0, 'skipped': 0})
            merge.assert_not_called()
        self.assertEqual(LessonRecording.objects.get(pk=recording.pk).merge_attempts, live_services.MERGE_MAX_ATTEMPTS)

    def test_a_failing_merge_is_retried_at_most_three_times(self):
        self.recording(LessonRecording.Status.FAILED)

        def fail(pk):
            LessonRecording.objects.filter(pk=pk).update(status=LessonRecording.Status.FAILED, error='boom')

        with mock.patch('apps.live.services._merge_recording', side_effect=fail) as merge:
            for _ in range(6):
                live_services.recover_recordings()
        self.assertEqual(merge.call_count, live_services.MERGE_MAX_ATTEMPTS)

    def test_files_still_being_written_active_lessons_and_missing_files_are_left_alone(self):
        fresh = self.recording(LessonRecording.Status.FAILED)
        now = timezone.now().timestamp()
        os.utime(self.tmp / 'v.webm', (now, now))  # hozirgina yozilgan
        with mock.patch('apps.live.services._merge_recording') as merge:
            self.assertEqual(live_services.recover_recordings()['skipped'], 1)
            merge.assert_not_called()
        LessonRecording.objects.filter(pk=fresh.pk).delete()
        Lesson.objects.filter(pk=self.lesson.pk).update(status=Lesson.Status.LIVE)
        self.recording(LessonRecording.Status.FAILED)
        with mock.patch('apps.live.services._merge_recording') as merge:
            self.assertEqual(live_services.recover_recordings()['merged'], 0)  # dars hali jonli
            merge.assert_not_called()
        LessonRecording.objects.all().delete()
        Lesson.objects.filter(pk=self.lesson.pk).update(status=Lesson.Status.FINISHED)
        LessonRecording.objects.create(
            lesson=self.lesson, status=LessonRecording.Status.FAILED, video_file_name='yoq.webm', audio_file_name='yoq2.webm',
        )
        with mock.patch('apps.live.services._merge_recording') as merge:
            self.assertEqual(live_services.recover_recordings()['skipped'], 1)  # fayllar diskda yo'q
            merge.assert_not_called()

    def test_single_side_recording_is_finalized_with_what_exists(self):
        recording = self.recording(LessonRecording.Status.FAILED, audio=False)
        with mock.patch('apps.live.services._announce_recording_ready'):
            report = live_services.recover_recordings()
        recording.refresh_from_db()
        self.assertEqual(report['single'], 1)
        self.assertEqual((recording.status, recording.file_name), ('completed', 'v.webm'))

    def test_one_missing_file_with_both_names_does_not_break_it(self):
        recording = self.recording(LessonRecording.Status.FAILED)
        (self.tmp / 'a.webm').unlink()
        with mock.patch('apps.live.services._announce_recording_ready'):
            report = live_services.recover_recordings()
        recording.refresh_from_db()
        self.assertEqual((report['single'], recording.status, recording.audio_file_name), (1, 'completed', ''))

    def test_completed_file_with_a_wrong_status_is_just_repaired(self):
        recording = self.recording(LessonRecording.Status.FAILED, audio=False, file_name='final.webm')
        make_video(self.tmp / 'final.webm')
        with mock.patch('apps.live.services._merge_recording') as merge:
            report = live_services.recover_recordings()
            merge.assert_not_called()
        self.assertEqual(report['repaired'], 1)
        self.assertEqual(LessonRecording.objects.get(pk=recording.pk).status, 'completed')

    def test_limit_and_the_management_command(self):
        for index in range(3):
            lesson = Lesson.objects.create(course=self.course, starts_at=timezone.now(), status=Lesson.Status.FINISHED)
            v, a = f'v{index}.webm', f'a{index}.webm'
            make_video(self.tmp / v)
            make_audio(self.tmp / a)
            for name in (v, a):
                os.utime(self.tmp / name, (self.old.timestamp(), self.old.timestamp()))
            LessonRecording.objects.create(lesson=lesson, status='failed', video_file_name=v, audio_file_name=a)
        with mock.patch('apps.live.services._merge_recording') as merge:
            self.assertEqual(live_services.recover_recordings(limit=2)['merged'], 2)
            self.assertEqual(merge.call_count, 2)
        with mock.patch('apps.live.services._merge_recording'):
            from io import StringIO

            out = StringIO()
            call_command('recover_recordings', '--limit', '5', stdout=out)
        self.assertIn('Birlashtirildi: 1', out.getvalue())  # qolgan bittasi
