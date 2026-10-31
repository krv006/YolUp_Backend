from unittest import mock

from django.core.management import get_commands
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.core.management.commands import run_scheduler


class SchedulerTests(SimpleTestCase):
    def test_every_job_is_a_real_command(self):
        commands = get_commands()
        for name, command, _args, period in run_scheduler.JOBS + run_scheduler.OPTIONAL_JOBS:
            self.assertIn(command, commands, name)
            self.assertGreaterEqual(period, 30)

    def test_failure_is_contained(self):
        with mock.patch.object(run_scheduler, 'call_command', side_effect=RuntimeError('boom')), \
                mock.patch.object(run_scheduler, 'close_old_connections') as close:
            self.assertFalse(run_scheduler.run_job('sync_ai_quizzes'))
            close.assert_called_once()

    def test_success_passes_arguments(self):
        with mock.patch.object(run_scheduler, 'call_command') as call, \
                mock.patch.object(run_scheduler, 'close_old_connections'):
            self.assertTrue(run_scheduler.run_job('prune_orphan_recordings', ('--apply',)))
            call.assert_called_once_with('prune_orphan_recordings', '--apply', verbosity=0)

    def test_default_selection_has_no_file_deleting_job(self):
        names = [job[0] for job in run_scheduler.select_jobs()]
        self.assertIn('recover_recordings', names)
        self.assertNotIn('prune_orphan_recordings', names)
        self.assertNotIn('prune_recordings', names)

    def test_retention_job_is_optional_and_uses_the_safe_command_arguments(self):
        (job,) = [j for j in run_scheduler.OPTIONAL_JOBS if j[0] == 'prune_recordings']
        self.assertEqual(job[2], ('--apply', '--drop-webm', '--older-than-days', '7'))
        with mock.patch.object(run_scheduler, 'call_command') as call, \
                mock.patch.object(run_scheduler, 'close_old_connections'):
            self.assertTrue(run_scheduler.run_job(job[1], job[2]))
            call.assert_called_once_with('prune_recordings', '--apply', '--drop-webm', '--older-than-days', '7', verbosity=0)

    def test_skip_removes_job(self):
        names = [job[0] for job in run_scheduler.select_jobs(skip=['recover_recordings'])]
        self.assertNotIn('recover_recordings', names)
        self.assertIn('send_lesson_reminders', names)

    def test_only_selects_exactly_those_including_optional(self):
        names = [job[0] for job in run_scheduler.select_jobs(only=['recover_recordings', 'prune_orphan_recordings'])]
        self.assertEqual(names, ['recover_recordings', 'prune_orphan_recordings'])

    def test_unknown_job_is_rejected(self):
        with self.assertRaises(CommandError):
            run_scheduler.select_jobs(only=['nope'])
