"""Email/telefonni kod bilan tasdiqlash, seanslarda shahar, email bildirishnomalari va fon ishlari."""
import re
from types import SimpleNamespace
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient, APITestCase

from apps.accounts import sessions
from apps.accounts.models import User
from apps.core import background, mailer, sms
from apps.notifications import services as notification_services
from apps.notifications.models import Notification

PASSWORD = 'StrongPass123!'


def make(username, role=User.Role.STUDENT, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def mailed_code():
    return re.search(r'\b(\d{5})\b', mail.outbox[-1].body).group(1)


@override_settings(SMS_BACKEND='console')
class VerificationTests(APITestCase):
    def setUp(self):
        cache.clear()
        sms.sent.clear()
        mail.outbox.clear()
        self.user = make('u1', email='u1@example.com', phone='+998901234567')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def post(self, path, data=None):
        return self.client.post(f'/api/v1/auth/{path}/', data or {}, format='json')

    def test_email_code_flow(self):
        resp = self.post('email/send-code')
        self.assertEqual((resp.status_code, resp.json()['sent']), (200, True))
        self.assertEqual(mail.outbox[-1].to, ['u1@example.com'])
        self.assertEqual(self.post('email/verify', {'code': '00000x'}).status_code, 400)
        resp = self.post('email/verify', {'code': mailed_code()})
        self.assertEqual((resp.status_code, resp.json()), (200, {'verified': True}))
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        self.assertTrue(self.client.get('/api/v1/auth/me/').json()['email_verified'])
        self.assertEqual(self.post('email/send-code').status_code, 400)  # allaqachon tasdiqlangan

    def test_phone_code_flow(self):
        self.assertEqual(self.post('phone/send-code').status_code, 200)
        code = re.search(r'\b(\d{5})\b', sms.sent[-1][1]).group(1)
        self.assertEqual(self.post('phone/verify', {'code': code}).json(), {'verified': True})
        self.user.refresh_from_db()
        self.assertTrue(self.user.phone_verified)

    def test_codes_are_single_use_and_limited_to_five_tries(self):
        self.post('email/send-code')
        code = mailed_code()
        wrong = '11111' if code != '11111' else '22222'
        for _ in range(5):
            self.assertEqual(self.post('email/verify', {'code': wrong}).status_code, 400)
        self.assertEqual(self.post('email/verify', {'code': code}).status_code, 400)  # 5 xatodan keyin kod bekor

    def test_missing_address_is_a_clear_error(self):
        User.objects.filter(pk=self.user.pk).update(email='', phone='')
        self.user.refresh_from_db()
        self.client.force_authenticate(self.user)
        self.assertEqual(self.post('email/send-code').status_code, 400)
        self.assertEqual(self.post('phone/send-code').status_code, 400)

    def test_resend_is_throttled_and_requires_login(self):
        self.assertEqual(self.post('email/send-code').status_code, 200)
        self.assertEqual(self.post('email/send-code').status_code, 429)
        self.assertEqual(APIClient().post('/api/v1/auth/email/send-code/').status_code, 401)

    def test_changing_the_address_resets_verification_and_old_code_is_useless(self):
        self.post('email/send-code')
        old_code = mailed_code()
        self.post('email/verify', {'code': old_code})
        self.client.patch('/api/v1/auth/me/', {'email': 'new@example.com', 'phone': '+998909999999'}, format='json')
        self.user.refresh_from_db()
        self.assertEqual((self.user.email_verified, self.user.phone_verified), (False, False))
        self.client.patch('/api/v1/auth/me/', {'email': 'new@example.com'}, format='json')  # o'zgarmadi
        self.assertEqual(self.post('email/verify', {'code': old_code}).status_code, 400)

    def test_without_email_service_nothing_is_pretended_and_cooldown_is_not_burnt(self):
        with override_settings(EMAIL_HOST='', EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'):
            for _ in range(2):
                resp = self.post('email/send-code')
                self.assertEqual(resp.status_code, 503)  # ikkinchisida ham 503 (429 emas)
        self.assertEqual(mail.outbox, [])


class SessionCityTests(SimpleTestCase):
    def tearDown(self):
        sessions._geoip_reader, sessions._geoip_failed = None, False

    def test_empty_when_not_configured(self):
        with override_settings(GEOIP_CITY_DB=''):
            self.assertEqual(sessions.city_for_ip('8.8.8.8'), '')
        self.assertEqual(sessions.city_for_ip(None), '')

    def test_city_from_reader_and_failures_are_swallowed(self):
        reader = mock.Mock()
        reader.city.return_value = SimpleNamespace(city=SimpleNamespace(name='Toshkent'))
        sessions._geoip_reader = reader
        with override_settings(GEOIP_CITY_DB='/x/city.mmdb'):
            self.assertEqual(sessions.city_for_ip('1.2.3.4'), 'Toshkent')
            reader.city.side_effect = LookupError('topilmadi')
            self.assertEqual(sessions.city_for_ip('10.0.0.1'), '')

    def test_missing_database_file_is_remembered(self):
        with override_settings(GEOIP_CITY_DB='/yo-q/city.mmdb'):
            self.assertEqual(sessions.city_for_ip('1.2.3.4'), '')
            self.assertTrue(sessions._geoip_failed)


class EmailNotificationTests(APITestCase):
    def setUp(self):
        mail.outbox.clear()
        self.wants = make('wants', email='a@example.com', notify_email=True)
        self.declines = make('declines', email='b@example.com', notify_email=False)
        self.no_address = make('noaddr', email='', notify_email=True)
        self.note = Notification(description='<p>Ertaga <b>test</b> bor</p>', kind='x')

    def send(self):
        notification_services.send_email_notification(self.note, [self.wants, self.declines, self.no_address])

    def test_only_opted_in_users_with_an_address_get_an_email(self):
        self.send()
        self.assertEqual([m.to for m in mail.outbox], [['a@example.com']])
        self.assertIn('Ertaga test bor', mail.outbox[0].body)
        self.assertNotIn('<b>', mail.outbox[0].body)

    def test_silent_when_email_is_not_configured(self):
        with override_settings(EMAIL_HOST='', EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'):
            self.send()  # xato ko'tarilmaydi
        self.assertEqual(mail.outbox, [])

    def test_one_bad_address_does_not_stop_the_rest(self):
        self.declines.notify_email = True
        real = mailer.send_email

        def flaky(to, subject, body):
            if to == 'a@example.com':
                raise mailer.EmailFailed()
            real(to, subject, body)

        with mock.patch('apps.core.mailer.send_email', side_effect=flaky):
            self.send()
        self.assertEqual([m.to for m in mail.outbox], [['b@example.com']])


class BackgroundTests(SimpleTestCase):
    def test_runs_inline_when_async_is_off_and_swallows_errors(self):
        calls = []
        with override_settings(BACKGROUND_ASYNC=False):
            background.run(calls.append, 1)
            background.run(lambda: 1 / 0)  # ko'tarilmaydi
        self.assertEqual(calls, [1])

    def test_submits_to_the_pool_when_async_is_on(self):
        with override_settings(BACKGROUND_ASYNC=True), mock.patch.object(background, '_pool') as pool:
            background.run(print, 'x')
        pool.return_value.submit.assert_called_once()
