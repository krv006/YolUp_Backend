from unittest import mock

from django.core.management import get_commands
from django.test import SimpleTestCase

from apps.core.management.commands import run_scheduler


class SchedulerTests(SimpleTestCase):
    def test_every_job_is_a_real_command(self):
        commands = get_commands()
        for name, period in run_scheduler.JOBS:
            self.assertIn(name, commands)
            self.assertGreaterEqual(period, 30)

    def test_failure_is_contained(self):
        with mock.patch.object(run_scheduler, 'call_command', side_effect=RuntimeError('boom')), \
                mock.patch.object(run_scheduler, 'close_old_connections') as close:
            self.assertFalse(run_scheduler.run_job('sync_ai_quizzes'))
            close.assert_called_once()

    def test_success_returns_true(self):
        with mock.patch.object(run_scheduler, 'call_command') as call, \
                mock.patch.object(run_scheduler, 'close_old_connections'):
            self.assertTrue(run_scheduler.run_job('send_lesson_reminders'))
            call.assert_called_once_with('send_lesson_reminders', verbosity=0)
