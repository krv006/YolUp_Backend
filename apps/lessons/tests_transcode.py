"""Dars yozuvini iOS ochadigan MP4 ga o'girish: navbat, band qilish, xatolar, stream tanlovi, haqiqiy ffmpeg bilan."""
import io
import shutil
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User

from . import services, transcode
from .models import Course, Enrollment, Lesson, LessonRecording

HAS_FFMPEG = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))


class RecordingBase(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        override = override_settings(RECORDINGS_DIR=self.tmp)
        override.enable()
        self.addCleanup(override.disable)
        self.teacher = User.objects.create_user(username='tr_t', password='x', role=User.Role.TEACHER)
        self.student = User.objects.create_user(username='tr_s', password='x', role=User.Role.STUDENT)
        self.course = Course.objects.create(teacher=self.teacher, title='TR')
        Enrollment.objects.create(course=self.course, student=self.student, status=Enrollment.Status.APPROVED)

    def recording(self, name='lesson-final.webm', *, status=LessonRecording.Status.COMPLETED, content=b'webm-bytes', **extra):
        lesson = Lesson.objects.create(course=self.course, starts_at=timezone.now(), duration_min=45,
                                       status=Lesson.Status.FINISHED)
        if name:
            (self.tmp / name).write_bytes(content)
        return LessonRecording.objects.create(lesson=lesson, file_name=name, status=status, **extra)

    @staticmethod
    def fake_ffmpeg(*, video=True, fail=False):
        """`subprocess.run` o'rniga: ffprobe 'video' deydi yoki yo'q; ffmpeg chiqish faylini yaratadi."""
        calls = []

        def run(cmd, **kwargs):
            calls.append(cmd)
            result = subprocess.CompletedProcess(cmd, 0, stdout='', stderr='')
            if 'ffprobe' in cmd[0]:
                result.stdout = 'video\n' if video else ''
            elif fail:
                result.returncode, result.stderr = 1, 'Invalid data found when processing input'
            else:
                Path(cmd[-1]).write_bytes(b'mp4-bytes')
            return result

        run.calls = calls
        return run


class ConvertTests(RecordingBase):
    def test_a_video_recording_becomes_an_h264_aac_faststart_mp4(self):
        recording = self.recording()
        fake = self.fake_ffmpeg()
        with patch('apps.lessons.transcode.subprocess.run', side_effect=fake):
            self.assertEqual(transcode.convert(recording.pk), 'done')
        recording.refresh_from_db()
        self.assertEqual((recording.mp4_file_name, recording.mp4_error), ('lesson-final.mp4', ''))
        self.assertEqual((self.tmp / 'lesson-final.mp4').read_bytes(), b'mp4-bytes')
        self.assertTrue((self.tmp / 'lesson-final.webm').exists())  # asl nusxa saqlanadi
        self.assertFalse(list(self.tmp.glob('*.part*')))  # vaqtinchalik fayl qolmaydi
        command = next(c for c in fake.calls if 'ffmpeg' in c[0] or 'ffmpeg' in c)
        flat = ' '.join(command)
        for expected in ('libx264', 'aac', '+faststart', 'yuv420p', '-g 30'):
            self.assertIn(expected, flat)

    def test_an_audio_only_recording_becomes_m4a_without_video_encoding(self):
        recording = self.recording()
        fake = self.fake_ffmpeg(video=False)
        with patch('apps.lessons.transcode.subprocess.run', side_effect=fake):
            self.assertEqual(transcode.convert(recording.pk), 'done')
        recording.refresh_from_db()
        self.assertEqual(recording.mp4_file_name, 'lesson-final.m4a')
        flat = ' '.join(next(c for c in fake.calls if 'ffprobe' not in ' '.join(c)))
        self.assertIn('-vn', flat)
        self.assertNotIn('libx264', flat)

    def test_a_failed_conversion_keeps_the_webm_and_records_the_reason(self):
        recording = self.recording()
        with patch('apps.lessons.transcode.subprocess.run', side_effect=self.fake_ffmpeg(fail=True)):
            self.assertEqual(transcode.convert(recording.pk), 'failed')
        recording.refresh_from_db()
        self.assertEqual(recording.mp4_file_name, '')
        self.assertIn('Invalid data', recording.mp4_error)
        self.assertTrue((self.tmp / 'lesson-final.webm').exists())
        self.assertFalse(list(self.tmp.glob('*.part*')))
        self.assertEqual(transcode.next_pending(), [])  # xatoli yozuv har siklda qayta urinilmaydi

    def test_a_missing_source_file_fails_cleanly(self):
        recording = self.recording(name='gone.webm')
        (self.tmp / 'gone.webm').unlink()
        self.assertEqual(transcode.convert(recording.pk), 'failed')
        recording.refresh_from_db()
        self.assertIn('topilmadi', recording.mp4_error)

    def test_only_one_process_can_claim_a_recording(self):
        recording = self.recording(mp4_error=transcode.CONVERTING)
        self.assertEqual(transcode.convert(recording.pk), 'skipped')

    def test_existing_mp4_and_unfinished_recordings_are_not_converted(self):
        old_mp4 = self.recording('egress.mp4')
        unfinished = self.recording('x.webm', status=LessonRecording.Status.RECORDING)
        done = self.recording('y.webm', mp4_file_name='y.mp4')
        self.assertEqual(transcode.next_pending(limit=10), [])
        self.assertEqual({old_mp4.pk, unfinished.pk, done.pk} & {r.pk for r in transcode.next_pending(limit=10)}, set())

    def test_the_oldest_recording_goes_first(self):
        first = self.recording('a.webm')
        second = self.recording('b.webm')
        LessonRecording.objects.filter(pk=first.pk).update(created_at=timezone.now() - timedelta(days=30))
        self.assertEqual([r.pk for r in transcode.next_pending(limit=2)], [first.pk, second.pk])

    def test_stale_claims_are_released_and_failed_ones_can_be_retried(self):
        stuck = self.recording('s.webm', mp4_error=transcode.CONVERTING)
        LessonRecording.objects.filter(pk=stuck.pk).update(updated_at=timezone.now() - timedelta(hours=7))
        self.assertEqual(transcode.release_stale(), 1)
        self.assertEqual([r.pk for r in transcode.next_pending()], [stuck.pk])
        failed = self.recording('f.webm', mp4_error='xato')
        self.assertNotIn(failed.pk, [r.pk for r in transcode.next_pending(limit=10)])
        self.assertIn(failed.pk, [r.pk for r in transcode.next_pending(retry_failed=True, limit=10)])
        with patch('apps.lessons.transcode.subprocess.run', side_effect=self.fake_ffmpeg()):
            self.assertEqual(transcode.convert(failed.pk), 'done')


class CommandLineTests(RecordingBase):
    def test_the_heavy_work_runs_at_low_priority_when_nice_exists(self):
        with patch('apps.lessons.transcode.shutil.which', return_value='/usr/bin/nice'):
            command = transcode._command('a.webm', 'a.mp4', video=True)
        self.assertEqual(command[:3], ['nice', '-n', '15'])
        self.assertEqual(command[3], 'ffmpeg')

    def test_without_nice_ffmpeg_runs_directly(self):
        with patch('apps.lessons.transcode.shutil.which', return_value=None):
            self.assertEqual(transcode._command('a.webm', 'a.mp4', video=True)[0], 'ffmpeg')


class CommandTests(RecordingBase):
    def test_the_command_converts_one_recording_per_call_oldest_first(self):
        first = self.recording('a.webm')
        second = self.recording('b.webm')
        LessonRecording.objects.filter(pk=first.pk).update(created_at=timezone.now() - timedelta(days=2))
        out = io.StringIO()
        with patch('apps.lessons.transcode.subprocess.run', side_effect=self.fake_ffmpeg()):
            call_command('convert_recordings', stdout=out)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.mp4_file_name, second.mp4_file_name), ('a.mp4', ''))
        self.assertIn('done', out.getvalue())

    def test_the_command_does_nothing_when_the_queue_is_empty(self):
        out = io.StringIO()
        call_command('convert_recordings', stdout=out)
        self.assertEqual(out.getvalue(), '')


class StreamTests(RecordingBase):
    def stream(self, recording, **headers):
        info = self.api().get(f'/api/v1/lessons/{recording.lesson_id}/recording/')
        self.assertEqual(info.status_code, 200, info.content)
        return APIClient().get(info.data['stream_url'], **headers)

    def api(self):
        client = APIClient()
        client.force_authenticate(self.student)
        return client

    def test_the_webm_is_served_until_the_mp4_is_ready(self):
        recording = self.recording(content=b'W' * 500)
        response = self.stream(recording)
        self.assertEqual((response.status_code, response['Content-Type']), (200, 'video/webm'))

    def test_the_mp4_is_served_once_it_is_ready_with_ranges(self):
        recording = self.recording(content=b'W' * 500)
        (self.tmp / 'lesson-final.mp4').write_bytes(b'M' * 300)
        LessonRecording.objects.filter(pk=recording.pk).update(mp4_file_name='lesson-final.mp4')
        response = self.stream(recording)
        self.assertEqual((response.status_code, response['Content-Type']), (200, 'video/mp4'))
        self.assertEqual(response['Accept-Ranges'], 'bytes')
        ranged = self.stream(recording, HTTP_RANGE='bytes=10-19')
        self.assertEqual((ranged.status_code, ranged['Content-Length'], ranged['Content-Range']),
                         (206, '10', 'bytes 10-19/300'))

    def test_an_open_ended_range_is_capped_so_the_server_never_buffers_the_rest_of_the_file(self):
        recording = self.recording(content=b'W' * 500)
        (self.tmp / 'lesson-final.mp4').write_bytes(bytes(range(256)) + b'M' * 244)
        LessonRecording.objects.filter(pk=recording.pk).update(mp4_file_name='lesson-final.mp4')
        with patch('apps.lessons.views.MAX_VIDEO_CHUNK', 100):
            open_ended = self.stream(recording, HTTP_RANGE='bytes=10-')
            too_long = self.stream(recording, HTTP_RANGE='bytes=10-499')
            tail = self.stream(recording, HTTP_RANGE='bytes=450-')
        self.assertEqual((open_ended.status_code, open_ended['Content-Length'], open_ended['Content-Range']),
                         (206, '100', 'bytes 10-109/500'))
        self.assertEqual(b''.join(open_ended.streaming_content), bytes(range(10, 110)))
        self.assertEqual((too_long['Content-Length'], too_long['Content-Range']), ('100', 'bytes 10-109/500'))
        self.assertEqual((tail['Content-Length'], tail['Content-Range']), ('50', 'bytes 450-499/500'))

    def test_an_audio_only_copy_is_served_as_audio_mp4(self):
        recording = self.recording(content=b'W' * 500)
        (self.tmp / 'lesson-final.m4a').write_bytes(b'A' * 100)
        LessonRecording.objects.filter(pk=recording.pk).update(mp4_file_name='lesson-final.m4a')
        self.assertEqual(self.stream(recording)['Content-Type'], 'audio/mp4')

    def test_a_missing_mp4_file_falls_back_to_the_webm(self):
        recording = self.recording(content=b'W' * 500, mp4_file_name='ghost.mp4')
        response = self.stream(recording)
        self.assertEqual((response.status_code, response['Content-Type']), (200, 'video/webm'))

    def test_deleting_a_recording_removes_the_mp4_too(self):
        recording = self.recording()
        (self.tmp / 'lesson-final.mp4').write_bytes(b'M')
        LessonRecording.objects.filter(pk=recording.pk).update(mp4_file_name='lesson-final.mp4')
        services.delete_recording(teacher=self.teacher, lesson=recording.lesson)
        self.assertEqual(list(self.tmp.iterdir()), [])


@skipUnless(HAS_FFMPEG, 'ffmpeg/ffprobe o\'rnatilmagan')
class RealFfmpegTests(RecordingBase):
    """Haqiqiy ffmpeg: brauzer kabi VP8+Opus WebM yaratib, iOS ochadigan H.264+AAC ga o'giramiz."""

    def setUp(self):
        super().setUp()
        # `nice` serverda (Linux) bor; Windows'da Git'ning `nice.exe` si argumentlarni buzadi — ffmpeg'ning o'zini sinaymiz
        patcher = patch('apps.lessons.transcode.shutil.which', return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_webm(self, name, *, video=True):
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2']
        if video:
            cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=size=800x450:rate=30:duration=2',
                   '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-c:v', 'libvpx', '-b:v', '300k',
                   '-c:a', 'libopus']
        else:
            cmd += ['-c:a', 'libopus']
        subprocess.run(cmd + [str(self.tmp / name)], check=True, capture_output=True)

    @staticmethod
    def probe(path):
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,codec_type,pix_fmt', '-of', 'csv=p=0', str(path)],
            capture_output=True, text=True, check=True).stdout
        return sorted(line for line in out.splitlines() if line)

    def test_a_vp8_opus_webm_becomes_h264_aac_mp4_with_the_index_up_front(self):
        self.make_webm('real.webm')
        recording = self.recording('real.webm', content=(self.tmp / 'real.webm').read_bytes())
        self.assertEqual(transcode.convert(recording.pk), 'done', LessonRecording.objects.get(pk=recording.pk).mp4_error)
        recording.refresh_from_db()
        mp4 = self.tmp / recording.mp4_file_name
        streams = self.probe(mp4)
        self.assertTrue(any(line.startswith('aac,audio') for line in streams), streams)
        self.assertTrue(any(line.startswith('h264,video') and 'yuv420p' in line for line in streams), streams)
        data = mp4.read_bytes()
        self.assertLess(data.find(b'moov'), data.find(b'mdat'))  # faststart: pleyer butun faylni kutmaydi

    def test_a_static_screen_still_gets_a_keyframe_every_two_seconds(self):
        # Tinch ekran (sahna o'zgarishi yo'q) — standart sozlamada kalit kadr ~17 soniyada bir marta chiqar edi
        subprocess.run(
            ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=c=white:s=640x360:r=30:d=9',
             '-f', 'lavfi', '-i', 'sine=frequency=440:duration=9', '-c:v', 'libvpx', '-g', '1000', '-b:v', '200k',
             '-c:a', 'libopus', str(self.tmp / 'static.webm')], check=True, capture_output=True)
        recording = self.recording('static.webm', content=(self.tmp / 'static.webm').read_bytes())
        self.assertEqual(transcode.convert(recording.pk), 'done')
        recording.refresh_from_db()
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'packet=pts_time,flags', '-of', 'csv=p=0',
             str(self.tmp / recording.mp4_file_name)], capture_output=True, text=True, check=True).stdout
        keyframes = [float(line.split(',')[0]) for line in out.splitlines() if ',K' in line]
        self.assertGreaterEqual(len(keyframes), 4, keyframes)  # 0, 2, 4, 6, 8
        gaps = [b - a for a, b in zip(keyframes, keyframes[1:])]
        self.assertLessEqual(max(gaps), 2.1, keyframes)

    def test_an_audio_only_webm_becomes_aac_m4a(self):
        self.make_webm('voice.webm', video=False)
        recording = self.recording('voice.webm', content=(self.tmp / 'voice.webm').read_bytes())
        self.assertEqual(transcode.convert(recording.pk), 'done')
        recording.refresh_from_db()
        self.assertEqual(recording.mp4_file_name, 'voice.m4a')
        self.assertEqual(self.probe(self.tmp / 'voice.m4a'), ['aac,audio'])

    def test_a_corrupt_file_fails_without_touching_anything(self):
        recording = self.recording('bad.webm', content=b'this is not a video')
        self.assertEqual(transcode.convert(recording.pk), 'failed')
        recording.refresh_from_db()
        self.assertEqual(recording.mp4_file_name, '')
        self.assertTrue(recording.mp4_error)
        self.assertEqual([p.name for p in self.tmp.iterdir()], ['bad.webm'])
