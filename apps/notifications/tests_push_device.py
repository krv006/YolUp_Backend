"""Mobil push (FCM) — qurilma ro'yxati va yuborish. PUSH-BACKEND.md."""
from unittest.mock import MagicMock, patch

from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.tests import login, register

from .models import PushDevice
from .services import strip_html
from .tests import make_admin


class PushDeviceApiTests(APITestCase):
    def setUp(self):
        register(self.client, 'pd1', 'teacher')
        self.teacher_token = login(self.client, 'pd1')
        self.teacher = User.objects.get(username='pd1')
        register(self.client, 'pd2', 'student')
        self.student_token = login(self.client, 'pd2')
        self.student = User.objects.get(username='pd2')

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def register_device(self, auth_token, **overrides):
        self.auth(auth_token)
        body = {
            'token': 'fcm-token-abc', 'platform': 'android', 'device_id': 'device-1', 'app_version': '1.0.0',
        }
        body.update(overrides)
        return self.client.post('/api/v1/notifications/push/device/', body, format='json')

    def test_requires_auth(self):
        resp = self.client.post('/api/v1/notifications/push/device/', {
            'token': 't', 'platform': 'android', 'device_id': 'd',
        }, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_register_creates_device(self):
        resp = self.register_device(self.teacher_token)
        self.assertEqual(resp.status_code, 201, resp.content)
        device = PushDevice.objects.get(user=self.teacher, device_id='device-1')
        self.assertEqual(device.token, 'fcm-token-abc')
        self.assertEqual(device.platform, 'android')
        self.assertEqual(device.app_version, '1.0.0')

    def test_invalid_platform_rejected(self):
        resp = self.register_device(self.teacher_token, platform='windows_phone')
        self.assertEqual(resp.status_code, 400)

    def test_reregistering_same_device_updates_token_not_duplicates(self):
        self.register_device(self.teacher_token, token='old-token')
        self.register_device(self.teacher_token, token='new-token')
        self.assertEqual(PushDevice.objects.filter(user=self.teacher, device_id='device-1').count(), 1)
        self.assertEqual(
            PushDevice.objects.get(user=self.teacher, device_id='device-1').token, 'new-token',
        )

    def test_same_device_id_different_users_creates_two_rows(self):
        """Hisoblar orasida almashish — bitta telefonda ikki hisob ulanishi mumkin."""
        self.register_device(self.teacher_token, device_id='shared-phone')
        self.register_device(self.student_token, device_id='shared-phone')
        self.assertEqual(PushDevice.objects.filter(device_id='shared-phone').count(), 2)

    def test_delete_removes_only_own_device(self):
        self.register_device(self.teacher_token, device_id='to-remove')
        self.auth(self.teacher_token)
        resp = self.client.delete(
            '/api/v1/notifications/push/device/', {'device_id': 'to-remove'}, format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['removed'])
        self.assertFalse(PushDevice.objects.filter(device_id='to-remove').exists())

    def test_delete_nonexistent_device_returns_false_not_error(self):
        self.auth(self.teacher_token)
        resp = self.client.delete(
            '/api/v1/notifications/push/device/', {'device_id': 'nope'}, format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()['removed'])

    def test_cannot_delete_another_users_device(self):
        self.register_device(self.teacher_token, device_id='teacher-device')
        self.auth(self.student_token)
        resp = self.client.delete(
            '/api/v1/notifications/push/device/', {'device_id': 'teacher-device'}, format='json',
        )
        self.assertFalse(resp.json()['removed'])
        self.assertTrue(PushDevice.objects.filter(device_id='teacher-device').exists())

    def test_logout_with_device_id_removes_device(self):
        self.register_device(self.teacher_token, device_id='logout-device')
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/auth/logout/', {
            'refresh': 'irrelevant-invalid-token', 'device_id': 'logout-device',
        }, format='json')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(PushDevice.objects.filter(device_id='logout-device').exists())

    def test_push_test_endpoint_notifies_self(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/notifications/push/test/')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()['kind'], 'push_test')


class StripHtmlTests(APITestCase):
    def test_strips_tags_keeps_text(self):
        self.assertEqual(strip_html('<p>Salom <b>dunyo</b></p>'), 'Salom dunyo')

    def test_empty_input(self):
        self.assertEqual(strip_html(''), '')
        self.assertEqual(strip_html(None), '')


class SendMobilePushTests(APITestCase):
    """`send_mobile_push` — FCM yuborish, best-effort, eskirgan token tozalash."""

    def setUp(self):
        self.admin = make_admin(self.client)
        self.admin_token = login(self.client, self.admin.username)
        register(self.client, 'mp1', 'teacher')
        self.teacher_token = login(self.client, 'mp1')
        self.teacher = User.objects.get(username='mp1')

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def send_as_admin(self, description='<p>Salom <b>dunyo</b></p>'):
        self.auth(self.admin_token)
        return self.client.post('/api/v1/notifications/send/', {
            'description': description, 'target_type': 'user', 'user_id': str(self.teacher.id),
        }, format='json')

    def test_no_devices_means_no_messaging_call(self):
        with patch('apps.notifications.services._firebase_messaging') as mock_get:
            with self.captureOnCommitCallbacks(execute=True):
                self.send_as_admin()
            mock_get.assert_not_called()

    def test_sends_plain_text_body_to_registered_device(self):
        from .services import register_push_device

        register_push_device(user=self.teacher, token='tok-1', platform='android', device_id='d1')
        fake_messaging = MagicMock()
        fake_messaging.UnregisteredError = type('UnregisteredError', (Exception,), {})
        fake_messaging.SenderIdMismatchError = type('SenderIdMismatchError', (Exception,), {})

        with patch('apps.notifications.services._firebase_messaging', return_value=fake_messaging):
            with self.captureOnCommitCallbacks(execute=True):
                self.send_as_admin('<p>Salom <b>dunyo</b></p>')

        self.assertEqual(fake_messaging.send.call_count, 1)
        sent_message = fake_messaging.Message.call_args.kwargs
        self.assertEqual(sent_message['token'], 'tok-1')
        notif_kwargs = fake_messaging.Notification.call_args.kwargs
        self.assertEqual(notif_kwargs['body'], 'Salom dunyo')
        self.assertNotIn('<', notif_kwargs['body'])

    def test_unregistered_device_is_deleted(self):
        from .services import register_push_device

        register_push_device(user=self.teacher, token='dead-tok', platform='ios', device_id='d2')
        fake_messaging = MagicMock()

        class UnregisteredError(Exception):
            pass

        class SenderIdMismatchError(Exception):
            pass

        fake_messaging.UnregisteredError = UnregisteredError
        fake_messaging.SenderIdMismatchError = SenderIdMismatchError
        fake_messaging.send.side_effect = UnregisteredError('gone')

        with patch('apps.notifications.services._firebase_messaging', return_value=fake_messaging):
            with self.captureOnCommitCallbacks(execute=True):
                self.send_as_admin()

        self.assertFalse(PushDevice.objects.filter(device_id='d2').exists())

    def test_firebase_not_configured_is_a_silent_noop(self):
        """`GOOGLE_APPLICATION_CREDENTIALS` sozlanmagan — xato bermasdan chiqadi."""
        from .services import register_push_device

        register_push_device(user=self.teacher, token='tok', platform='android', device_id='d3')
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.send_as_admin()
        self.assertEqual(resp.status_code, 201)
