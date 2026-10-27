"""Yozuv fayllarini tozalash: kurs o'chganda hamma fayl ketadi; prune_recordings xavfsiz qoidalar bilan ishlaydi."""
import shutil
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.lessons import services
from apps.lessons.models import Course, Lesson, LessonRecording
from apps.notifications.models import Notification, NotificationRecipient


class PruneBase(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        override = override_settings(RECORDINGS_DIR=self.root)
        override.enable()
        self.addCleanup(override.disable)
        self.teacher = User.objects.create_user(username='prune_t', password='x', role=User.Role.TEACHER, is_approved=True)
        self.course = Course.objects.create(teacher=self.teacher, title='K', subject='math')
        self.lesson = Lesson.objects.create(course=self.course, title='D', starts_at=timezone.now(), status=Lesson.Status.FINISHED)

    def make_recording(self, *, old=True, mp4=True):
        for name in ('final.webm', 'final.mp4', 'v.webm', 'a.webm'):
            (self.root / name).write_bytes(b'x' * 100)
        recording = LessonRecording.objects.create(
            lesson=self.lesson, status=LessonRecording.Status.COMPLETED, file_name='final.webm',
            mp4_file_name='final.mp4' if mp4 else '', video_file_name='v.webm', audio_file_name='a.webm',
        )
        if old:
            LessonRecording.objects.filter(pk=recording.pk).update(updated_at=timezone.now() - timedelta(days=30))
        return recording


class CourseDeleteFilesTests(PruneBase):
    def test_delete_course_removes_every_recording_file(self):
        self.make_recording()
        services.delete_course(teacher=self.teacher, course=self.course, request=None)
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertFalse(LessonRecording.objects.exists())


class PruneRecordingsTests(PruneBase):
    def run_command(self, *args):
        out = StringIO()
        with mock.patch('apps.lessons.management.commands.prune_recordings._readable', return_value=True):
            call_command('prune_recordings', *args, stdout=out)
        return out.getvalue()

    def test_report_only_deletes_nothing(self):
        self.make_recording()
        text = self.run_command()
        self.assertIn('2 ta', text)
        self.assertEqual(len(list(self.root.iterdir())), 4)

    def test_apply_removes_only_raw_parts(self):
        self.make_recording()
        self.run_command('--apply')
        self.assertEqual({p.name for p in self.root.iterdir()}, {'final.webm', 'final.mp4'})

    def test_drop_webm_keeps_mp4_and_serves_it(self):
        recording = self.make_recording()
        self.run_command('--apply', '--drop-webm')
        self.assertEqual({p.name for p in self.root.iterdir()}, {'final.mp4'})
        self.assertEqual(services._recording_path(recording).name, 'final.mp4')

    def test_drop_webm_needs_mp4(self):
        self.make_recording(mp4=False)
        self.run_command('--apply', '--drop-webm')
        self.assertTrue((self.root / 'final.webm').exists())

    def test_recent_recordings_untouched(self):
        self.make_recording(old=False)
        self.run_command('--apply', '--drop-webm')
        self.assertEqual(len(list(self.root.iterdir())), 4)

    def test_no_final_file_keeps_raw_parts(self):
        self.make_recording()
        (self.root / 'final.webm').unlink()
        self.run_command('--apply')
        self.assertTrue((self.root / 'v.webm').exists())


class PruneNotificationsTests(TestCase):
    def test_apply_deletes_only_old(self):
        admin = User.objects.create_user(username='n_admin', password='x', role=User.Role.ADMIN)
        student = User.objects.create_user(username='n_student', password='x', role=User.Role.STUDENT)
        old = Notification.objects.create(sender=admin, description='eski', target_type='all')
        new = Notification.objects.create(sender=admin, description='yangi', target_type='all')
        for item in (old, new):
            NotificationRecipient.objects.create(notification=item, user=student)
        Notification.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=400))
        out = StringIO()
        call_command('prune_notifications', stdout=out)
        self.assertEqual(Notification.objects.count(), 2)  # hisobot — o'chirmaydi
        call_command('prune_notifications', '--apply', stdout=out)
        self.assertEqual(list(Notification.objects.values_list('pk', flat=True)), [new.pk])
        self.assertEqual(NotificationRecipient.objects.count(), 1)
