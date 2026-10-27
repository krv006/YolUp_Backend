"""Ikki serverli joylashtirish: sayt serverida fayl yo'q, yozuv serverida bor."""
import shutil
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.lessons import services
from apps.lessons.models import Course, Lesson, LessonRecording
from apps.notifications.models import NotificationRecipient


class TwoServerBase(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        override = override_settings(RECORDINGS_DIR=self.root)
        override.enable()
        self.addCleanup(override.disable)
        self.teacher = User.objects.create_user(username='ts_t', password='x', role=User.Role.TEACHER, is_approved=True)
        self.course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        self.lesson = Lesson.objects.create(course=self.course, title='D', starts_at=timezone.now(), status=Lesson.Status.FINISHED)


class EnsureFinalizedTests(TwoServerBase):
    def make(self):
        return LessonRecording.objects.create(
            lesson=self.lesson, status=LessonRecording.Status.RECORDING, video_file_name='v.webm', audio_file_name='a.webm',
        )

    @override_settings(RECORDINGS_LOCAL=False)
    def test_core_server_only_marks_parts_ready_and_never_merges(self):
        recording = self.make()
        with mock.patch('apps.live.services.maybe_start_merge') as merge, \
                mock.patch('apps.live.services.finalize_single_side') as single:
            services._ensure_recording_finalized(self.lesson)
        merge.assert_not_called()
        single.assert_not_called()
        recording.refresh_from_db()
        self.assertIsNotNone(recording.video_ready_at)
        self.assertIsNotNone(recording.audio_finalized_at)
        self.assertEqual(recording.status, LessonRecording.Status.RECORDING)

    @override_settings(RECORDINGS_LOCAL=True)
    def test_single_server_still_merges(self):
        self.make()
        with mock.patch('apps.live.services.maybe_start_merge') as merge, \
                mock.patch('apps.live.services.finalize_single_side'):
            services._ensure_recording_finalized(self.lesson)
        merge.assert_called_once()


class RecoverPicksStaleRecordingTests(TwoServerBase):
    def test_idle_recording_state_is_recovered_on_media_server(self):
        from apps.live import services as live

        (self.root / 'v.webm').write_bytes(b'x' * 10)
        (self.root / 'a.webm').write_bytes(b'x' * 10)
        recording = LessonRecording.objects.create(
            lesson=self.lesson, status=LessonRecording.Status.RECORDING, video_file_name='v.webm', audio_file_name='a.webm',
        )
        LessonRecording.objects.filter(pk=recording.pk).update(updated_at=timezone.now() - timedelta(hours=1))
        import os
        old = (timezone.now() - timedelta(hours=1)).timestamp()
        for name in ('v.webm', 'a.webm'):
            os.utime(self.root / name, (old, old))
        with mock.patch.object(live, '_merge_recording') as merge:
            report = live.recover_recordings()
        merge.assert_called_once_with(recording.pk)
        self.assertEqual(report['merged'], 1)


class PruneOrphansTests(TwoServerBase):
    def run_command(self, *args):
        out = StringIO()
        call_command('prune_orphan_recordings', *args, stdout=out)
        return out.getvalue()

    def age(self, name, hours):
        import os
        stamp = (timezone.now() - timedelta(hours=hours)).timestamp()
        os.utime(self.root / name, (stamp, stamp))

    def test_removes_only_old_files_without_a_row(self):
        for name in ('keep.webm', 'orphan.webm', 'fresh_orphan.webm'):
            (self.root / name).write_bytes(b'x')
        LessonRecording.objects.create(lesson=self.lesson, status=LessonRecording.Status.COMPLETED, file_name='keep.webm')
        for name in ('keep.webm', 'orphan.webm'):
            self.age(name, 100)
        self.run_command('--apply')
        self.assertEqual({p.name for p in self.root.iterdir()}, {'keep.webm', 'fresh_orphan.webm'})

    def test_report_only_by_default(self):
        LessonRecording.objects.create(lesson=self.lesson, status=LessonRecording.Status.COMPLETED, file_name='keep.webm')
        (self.root / 'orphan.webm').write_bytes(b'x')
        self.age('orphan.webm', 100)
        self.assertIn('1 ta', self.run_command())
        self.assertTrue((self.root / 'orphan.webm').exists())

    def test_refuses_when_database_has_no_recordings(self):
        (self.root / 'orphan.webm').write_bytes(b'x')
        self.age('orphan.webm', 100)
        self.run_command('--apply')
        self.assertTrue((self.root / 'orphan.webm').exists())

    @override_settings(RECORDINGS_LOCAL=False)
    def test_skips_on_core_server(self):
        LessonRecording.objects.create(lesson=self.lesson, status=LessonRecording.Status.COMPLETED, file_name='keep.webm')
        (self.root / 'orphan.webm').write_bytes(b'x')
        self.age('orphan.webm', 100)
        self.run_command('--apply')
        self.assertTrue((self.root / 'orphan.webm').exists())

    def test_max_delete_limit(self):
        LessonRecording.objects.create(lesson=self.lesson, status=LessonRecording.Status.COMPLETED, file_name='keep.webm')
        for i in range(5):
            (self.root / f'o{i}.webm').write_bytes(b'x')
            self.age(f'o{i}.webm', 100)
        self.run_command('--apply', '--max-delete', '2')
        self.assertEqual(len(list(self.root.iterdir())), 3)


class CheckDiskTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(username='disk_admin', password='x', role=User.Role.ADMIN)

    def run_command(self, percent, *args):
        with mock.patch('apps.monitoring.services.disk_percent', return_value=percent):
            call_command('check_disk', *args, stdout=StringIO())

    def test_below_threshold_is_silent(self):
        self.run_command(50.0)
        self.assertFalse(NotificationRecipient.objects.exists())

    def test_alert_is_sent_once_per_level(self):
        self.run_command(85.0)
        self.run_command(85.0)
        self.assertEqual(NotificationRecipient.objects.filter(user=self.admin).count(), 1)

    def test_critical_is_a_separate_alert(self):
        self.run_command(85.0)
        self.run_command(95.0)
        self.assertEqual(NotificationRecipient.objects.filter(user=self.admin).count(), 2)
