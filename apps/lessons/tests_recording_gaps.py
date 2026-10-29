"""Yozuvdagi tanaffuslar: ekran ulashish o'chirib-yoqilganda yoki video/ovozdan biri erta to'xtaganda video va ovoz siljimasligi.

Sabab (2026-10-29, lokal tajriba): har yangi yozuv sessiyasi xom faylga ulanadi, `mkvmerge --append` esa oradagi real vaqt
tanaffusini olib tashlaydi, ovoz esa uzluksiz yozilib ketadi => 10 soniyalik tanaffus 10 soniya siljish va oxiri kesilishi.
Haqiqiy `ffmpeg`/`mkvmerge` bilan; fayllar brauzer (MediaRecorder) kabi davomiylik sarlavhasiz (`-live 1`).
"""
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.live.services import _media_duration, _merge_recording, _normalize_webm

from .models import Course, Lesson, LessonRecording

T0 = datetime(2026, 10, 29, 10, 0, 0, tzinfo=dt_timezone.utc)


def make_video(path, color, seconds):
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'color=c={color}:s=64x64:r=10:d={seconds}',
        '-c:v', 'libvpx', '-g', '10', '-f', 'webm', '-live', '1', str(path),
    ], check=True, capture_output=True)


def make_audio(path, seconds, frequency=440):
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'sine=frequency={frequency}:duration={seconds}',
        '-c:a', 'libopus', '-f', 'webm', '-live', '1', str(path),
    ], check=True, capture_output=True)


def picture_at(path, second):
    from PIL import Image

    frame = Path(path).with_suffix('.frame.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(second), '-i', str(path), '-frames:v', '1', str(frame)],
                   check=True, capture_output=True)
    return Image.open(frame).convert('RGB').resize((1, 1)).getpixel((0, 0))


def is_red(pixel):
    return pixel[0] > 150 and pixel[2] < 100


def is_blue(pixel):
    return pixel[2] > 150 and pixel[0] < 100


class RecordingGapTests(APITestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        override = override_settings(RECORDINGS_DIR=self.tmp)
        override.enable()
        self.addCleanup(override.disable)
        teacher = User(username='gap_t', role=User.Role.TEACHER)
        teacher.set_password('x')
        teacher.save()
        self.teacher = teacher
        course = Course.objects.create(teacher=teacher, title='Gap')
        self.lesson = Lesson.objects.create(course=course, starts_at=timezone.now(), duration_min=45,
                                            status=Lesson.Status.FINISHED)

    def two_video_sessions(self, gap_seconds, first=2, second=2):
        """Qizil (1-sessiya) + ko'k (2-sessiya) xom ulangan fayl va ularning sessiya yozuvlari."""
        a, b = self.tmp / 'a.webm', self.tmp / 'b.webm'
        make_video(a, 'red', first)
        make_video(b, 'blue', second)
        raw = self.tmp / 'video.webm'
        raw.write_bytes(a.read_bytes() + b.read_bytes())
        sessions = [
            {'session': 's1', 'offset': 0, 'started_at': T0.isoformat()},
            {'session': 's2', 'offset': a.stat().st_size,
             'started_at': (T0 + timedelta(seconds=first + gap_seconds)).isoformat()},
        ]
        return raw, sessions

    # ── bo'laklarni yuklash: sessiya chegarasi saqlanadi ──
    def test_each_new_recording_session_is_remembered_with_its_byte_offset_and_clock_time(self):
        api = self.client
        api.force_authenticate(self.teacher)
        url = f'/api/v1/lessons/{self.lesson.id}/recording/video/'

        def send(session, index, body, started_at=None):
            data = {'chunk': SimpleUploadedFile('c.webm', body, content_type='video/webm'), 'session': session, 'index': index}
            if started_at:
                data['started_at'] = started_at
            self.assertEqual(api.post(url, data, format='multipart').status_code, 204)

        send('s1', 0, b'AAAA', T0.isoformat())
        send('s1', 1, b'BB')
        send('s1', 1, b'BB')  # takror — yozilmaydi va sessiya qayta qo'shilmaydi
        send('s2', 0, b'CCC', (T0 + timedelta(seconds=30)).isoformat())
        recording = LessonRecording.objects.get(lesson=self.lesson)
        self.assertEqual((self.tmp / recording.video_file_name).read_bytes(), b'AAAABBCCC')
        self.assertEqual(recording.video_sessions, [
            {'session': 's1', 'offset': 0, 'started_at': T0.isoformat()},
            {'session': 's2', 'offset': 6, 'started_at': (T0 + timedelta(seconds=30)).isoformat()},
        ])

    def test_old_clients_without_session_ids_leave_no_session_records(self):
        self.client.force_authenticate(self.teacher)
        chunk = SimpleUploadedFile('c.webm', b'AAAA', content_type='video/webm')
        self.client.post(f'/api/v1/lessons/{self.lesson.id}/recording/video/', {'chunk': chunk}, format='multipart')
        self.assertEqual(LessonRecording.objects.get(lesson=self.lesson).video_sessions, [])

    # ── normalizatsiya: tanaffus to'ldiriladi ──
    def test_video_gap_between_sessions_is_filled_so_the_timeline_matches_the_lesson(self):
        raw, sessions = self.two_video_sessions(gap_seconds=3)
        result = _normalize_webm(raw, sessions, 'video')
        self.assertNotEqual(result, raw)
        self.assertAlmostEqual(_media_duration(result), 7.0, delta=0.7)  # 2 + 3 (tanaffus) + 2
        self.assertTrue(is_red(picture_at(result, 0.5)))
        self.assertTrue(is_red(picture_at(result, 3.5)), 'tanaffusda oxirgi kadr qotib turishi kerak')
        self.assertTrue(is_blue(picture_at(result, 6.0)))

    def test_without_session_info_segments_are_just_joined_as_before(self):
        raw, _sessions = self.two_video_sessions(gap_seconds=3)
        result = _normalize_webm(raw)
        self.assertAlmostEqual(_media_duration(result), 4.0, delta=0.6)

    def test_a_gap_shorter_than_half_a_second_is_ignored(self):
        raw, sessions = self.two_video_sessions(gap_seconds=0.2)
        self.assertAlmostEqual(_media_duration(_normalize_webm(raw, sessions, 'video')), 4.0, delta=0.6)

    def test_audio_gap_is_filled_with_silence(self):
        a, b = self.tmp / 'a1.webm', self.tmp / 'a2.webm'
        make_audio(a, 2)
        make_audio(b, 2)
        raw = self.tmp / 'audio.webm'
        raw.write_bytes(a.read_bytes() + b.read_bytes())
        sessions = [{'session': 's1', 'offset': 0, 'started_at': T0.isoformat()},
                    {'session': 's2', 'offset': a.stat().st_size, 'started_at': (T0 + timedelta(seconds=6)).isoformat()}]
        result = _normalize_webm(raw, sessions, 'audio')
        self.assertAlmostEqual(_media_duration(result), 8.0, delta=0.7)  # 2 + 4 (jimlik) + 2

    def test_session_offsets_are_trusted_over_a_byte_scan_and_wrong_ones_fall_back_to_the_scan(self):
        raw, sessions = self.two_video_sessions(gap_seconds=3)
        sessions[1]['offset'] += 7  # EBML sarlavhasiga to'g'ri kelmaydi
        result = _normalize_webm(raw, sessions, 'video')
        self.assertAlmostEqual(_media_duration(result), 4.0, delta=0.6)  # skanerlash: tanaffussiz, lekin ikkala segment bor

    def test_normalizing_does_not_load_the_whole_recording_into_memory(self):
        raw, sessions = self.two_video_sessions(gap_seconds=1)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('butun fayl xotiraga o\'qildi')):
            result = _normalize_webm(raw, sessions, 'video')
        self.assertTrue(result.exists())

    # ── to'liq birlashtirish ──
    def test_merge_keeps_picture_and_sound_in_step_after_the_screen_share_was_off_for_a_while(self):
        raw, vsessions = self.two_video_sessions(gap_seconds=3)
        audio = self.tmp / 'audio.webm'
        make_audio(audio, 7)  # ovoz uzluksiz, butun dars (7 s)
        recording = LessonRecording.objects.create(
            lesson=self.lesson, status=LessonRecording.Status.MERGING,
            video_file_name='video.webm', video_started_at=T0, video_sessions=vsessions,
            audio_file_name='audio.webm', audio_started_at=T0,
            video_ready_at=T0, audio_finalized_at=T0,
        )
        _merge_recording(recording.pk)
        recording.refresh_from_db()
        self.assertEqual(recording.status, LessonRecording.Status.COMPLETED, recording.error)
        final = self.tmp / recording.file_name
        self.assertAlmostEqual(_media_duration(final), 7.0, delta=0.8)  # eskisi: 4 s (oxiri kesilardi)
        self.assertTrue(is_blue(picture_at(final, 6.0)), '6-soniyada rasm 2-sessiyaniki (ko\'k) bo\'lishi kerak')
        self.assertTrue(is_red(picture_at(final, 3.5)))
        self.assertEqual(list(self.tmp.glob('*-normalized*')) + list(self.tmp.glob('*-padded*')), [])

    def test_when_the_video_stops_early_the_rest_of_the_audio_is_kept_over_the_last_frame(self):
        video = self.tmp / 'video.webm'
        audio = self.tmp / 'audio.webm'
        make_video(video, 'red', 2)  # o'qituvchi ulashishni 2-soniyada to'xtatgan
        make_audio(audio, 6)         # dars esa 6 soniya davom etgan
        recording = LessonRecording.objects.create(
            lesson=self.lesson, status=LessonRecording.Status.MERGING,
            video_file_name='video.webm', video_started_at=T0,
            audio_file_name='audio.webm', audio_started_at=T0,
            video_ready_at=T0, audio_finalized_at=T0,
        )
        _merge_recording(recording.pk)
        recording.refresh_from_db()
        self.assertEqual(recording.status, LessonRecording.Status.COMPLETED, recording.error)
        final = self.tmp / recording.file_name
        self.assertAlmostEqual(_media_duration(final), 6.0, delta=0.8)  # eskisi: 2 s (ovoz kesilardi)
        self.assertTrue(is_red(picture_at(final, 5.0)))
        self.assertEqual(list(self.tmp.glob('*-padded*')), [])

    def test_a_shorter_audio_is_padded_with_silence_instead_of_cutting_the_video(self):
        video = self.tmp / 'video.webm'
        audio = self.tmp / 'audio.webm'
        make_video(video, 'red', 5)
        make_audio(audio, 2)
        recording = LessonRecording.objects.create(
            lesson=self.lesson, status=LessonRecording.Status.MERGING,
            video_file_name='video.webm', video_started_at=T0,
            audio_file_name='audio.webm', audio_started_at=T0,
            video_ready_at=T0, audio_finalized_at=T0,
        )
        _merge_recording(recording.pk)
        recording.refresh_from_db()
        self.assertEqual(recording.status, LessonRecording.Status.COMPLETED, recording.error)
        self.assertAlmostEqual(_media_duration(self.tmp / recording.file_name), 5.0, delta=0.8)

    def test_normal_recording_without_gaps_is_unchanged(self):
        video = self.tmp / 'video.webm'
        audio = self.tmp / 'audio.webm'
        make_video(video, 'red', 3)
        make_audio(audio, 3)
        recording = LessonRecording.objects.create(
            lesson=self.lesson, status=LessonRecording.Status.MERGING,
            video_file_name='video.webm', video_started_at=T0, video_sessions=[{'session': 's', 'offset': 0, 'started_at': T0.isoformat()}],
            audio_file_name='audio.webm', audio_started_at=T0, audio_sessions=[{'session': 's', 'offset': 0, 'started_at': T0.isoformat()}],
            video_ready_at=T0, audio_finalized_at=T0,
        )
        with patch('apps.live.services._make_filler') as filler:
            _merge_recording(recording.pk)
        filler.assert_not_called()
        recording.refresh_from_db()
        self.assertEqual(recording.status, LessonRecording.Status.COMPLETED, recording.error)
        self.assertAlmostEqual(_media_duration(self.tmp / recording.file_name), 3.0, delta=0.6)

    def test_if_the_gap_filler_cannot_be_appended_the_plain_join_is_used_instead(self):
        """To'ldiruvchi bilan ulanmasa (haqiqiy Chrome faylida kodek parametrlari farq qilsa) yozuv yo'qolmaydi."""
        from apps.live import services as live

        real = live._mkv_append

        def refuse_fillers(parts, output):
            if any(Path(part).name.startswith('gap-') for part in parts):
                return False
            return real(parts, output)

        raw, sessions = self.two_video_sessions(gap_seconds=3)
        with patch.object(live, '_mkv_append', side_effect=refuse_fillers):
            result = live._normalize_webm(raw, sessions, 'video')
        self.assertNotEqual(result, raw)
        self.assertAlmostEqual(_media_duration(result), 4.0, delta=0.6)  # tanaffussiz, lekin ikkala segment bor


class CheckFailedRecordingsTests(APITestCase):
    """Qayta urinishlar tugagan FAILED yozuvlar adminga bir marta xabar qiladi (M3)."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.admin = User.objects.create_user(username='fr_admin', password='x', role=User.Role.ADMIN)
        teacher = User.objects.create_user(username='fr_t', password='x', role=User.Role.TEACHER)
        course = Course.objects.create(teacher=teacher, title='Fail')
        self.lesson = Lesson.objects.create(course=course, starts_at=timezone.now(), duration_min=45,
                                            status=Lesson.Status.FINISHED)

    def run_command(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('check_failed_recordings', stdout=StringIO())

    def count(self):
        from apps.notifications.models import NotificationRecipient

        return NotificationRecipient.objects.filter(user=self.admin).count()

    def test_exhausted_failed_recording_notifies_admins_once(self):
        LessonRecording.objects.create(lesson=self.lesson, status=LessonRecording.Status.FAILED, merge_attempts=3, error='boom')
        self.run_command()
        self.run_command()
        self.assertEqual(self.count(), 1)

    def test_recordings_that_can_still_be_retried_or_are_fine_are_ignored(self):
        LessonRecording.objects.create(lesson=self.lesson, status=LessonRecording.Status.FAILED, merge_attempts=1)
        self.run_command()
        self.assertEqual(self.count(), 0)
