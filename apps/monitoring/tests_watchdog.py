"""watchdog: yiqilish/tiklanish xabarlari faqat holat o'zgarganda va ketma-ket N marta muvaffaqiyatsizlikdan keyin yuboriladi."""
import os
import tempfile
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from apps.monitoring.management.commands import watchdog


class WatchdogTests(SimpleTestCase):
    def setUp(self):
        self.state_file = os.path.join(tempfile.mkdtemp(), 'state.json')
        patcher = mock.patch.dict(os.environ, {'WATCHDOG_STATE_FILE': self.state_file, 'WATCHDOG_FAIL_AFTER': '2'})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.targets = [('MEDIA: LiveKit', 'https://x/', {})]

    def run_once(self, ok):
        with mock.patch.object(watchdog, 'targets', return_value=self.targets), \
                mock.patch.object(watchdog, 'check_url', return_value=(ok, 'HTTP 200' if ok else 'URLError')), \
                mock.patch.object(watchdog, 'send_alert') as alert:
            call_command('watchdog', stdout=StringIO())
        return alert

    def test_no_alert_while_everything_is_up(self):
        self.assertFalse(self.run_once(True).called)

    def test_alerts_only_after_consecutive_failures_and_only_once(self):
        self.assertFalse(self.run_once(False).called)         # 1st failure: wait
        second = self.run_once(False)
        self.assertEqual(second.call_count, 1)                # 2nd: down alert
        self.assertIn('YIQILDI', second.call_args[0][0])
        self.assertFalse(self.run_once(False).called)         # still down: no repeat spam

    def test_recovery_alert_then_silence(self):
        self.run_once(False)
        self.run_once(False)
        recovered = self.run_once(True)
        self.assertEqual(recovered.call_count, 1)
        self.assertIn('TIKLANDI', recovered.call_args[0][0])
        self.assertFalse(self.run_once(True).called)

    def test_single_blip_does_not_alert(self):
        self.run_once(False)
        self.assertFalse(self.run_once(True).called)

    @override_settings(SERVER_ROLE='media', ALLOWED_HOSTS=['backend.example'])
    def test_media_checks_the_app_health_endpoint(self):
        with mock.patch.dict(os.environ, {'DOMAIN': 'backend.example'}):
            self.assertEqual(watchdog.targets()[0][1], 'https://backend.example/api/health/')

    @override_settings(SERVER_ROLE='', LIVEKIT_URL='wss://lk.example', ALLOWED_HOSTS=['backend.example'])
    def test_app_checks_livekit_and_the_recording_service(self):
        with mock.patch.dict(os.environ, {'REC_UPSTREAM': '10.10.0.2:8000'}):
            urls = [t[1] for t in watchdog.targets()]
        self.assertEqual(urls, ['https://lk.example', 'http://10.10.0.2:8000/api/health/'])

    def test_send_alert_without_configuration_is_a_noop(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            for key in ('ALERT_TELEGRAM_BOT_TOKEN', 'ALERT_TELEGRAM_CHAT_ID', 'ALERT_WEBHOOK_URL'):
                os.environ.pop(key, None)
            with mock.patch.object(watchdog, '_post') as post:
                self.assertFalse(watchdog.send_alert('x'))
                post.assert_not_called()

    def test_send_alert_uses_telegram_when_configured(self):
        with mock.patch.dict(os.environ, {'ALERT_TELEGRAM_BOT_TOKEN': 'T', 'ALERT_TELEGRAM_CHAT_ID': '42'}), \
                mock.patch.object(watchdog, '_post', return_value=True) as post:
            self.assertTrue(watchdog.send_alert('hello'))
            self.assertIn('api.telegram.org/botT/sendMessage', post.call_args[0][0])
