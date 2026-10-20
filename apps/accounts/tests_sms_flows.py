"""Parolni tiklash (telefon + SMS kod), ikki bosqichli tasdiqlash (2FA) va tizim sozlamalari."""
import re
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from apps.accounts import otp
from apps.accounts.models import User, UserSession
from apps.core import sms

PASSWORD = 'StrongPass123!'
NEW_PASSWORD = 'BrandNewPass456!'
PHONE = '+998901234567'


def make(username, role=User.Role.STUDENT, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def last_code():
    return re.search(r'\b(\d{5})\b', sms.sent[-1][1]).group(1)


@override_settings(SMS_BACKEND='console')
class SmsTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        sms.sent.clear()


class SmsModuleTests(SmsTestCase):
    def test_phone_helpers(self):
        self.assertEqual(sms.normalize_phone('+998 90 123-45-67'), '998901234567')
        self.assertEqual(sms.normalize_phone('901234567'), '998901234567')
        self.assertEqual(sms.normalize_phone('abc'), '')
        self.assertIn('+998901234567', sms.phone_variants('90 123 45 67'))
        self.assertEqual(sms.mask_phone(PHONE), '+998*****4567')

    def test_without_a_provider_nothing_is_pretended(self):
        with override_settings(SMS_BACKEND='', ESKIZ_EMAIL='', ESKIZ_PASSWORD=''):
            self.assertFalse(sms.configured())
            with self.assertRaises(sms.SmsNotConfigured):
                sms.send_sms(PHONE, 'x')
        with override_settings(SMS_BACKEND='', ESKIZ_EMAIL='a@b.uz', ESKIZ_PASSWORD='x'):
            self.assertEqual(sms.backend_name(), 'eskiz')

    def test_eskiz_login_and_send(self):
        calls = []

        def fake_post(url, data=None, headers=None, timeout=None):
            calls.append((url, data, headers))
            response = mock.Mock(status_code=200)
            response.json.return_value = {'data': {'token': 'TKN'}}
            response.raise_for_status.return_value = None
            return response

        with override_settings(SMS_BACKEND='eskiz', ESKIZ_EMAIL='a@b.uz', ESKIZ_PASSWORD='x'), \
                mock.patch('apps.core.sms.requests.post', side_effect=fake_post):
            sms.send_sms(PHONE, 'salom')
        self.assertTrue(calls[0][0].endswith('/auth/login'))
        self.assertEqual(calls[1][1]['mobile_phone'], '998901234567')
        self.assertEqual(calls[1][2]['Authorization'], 'Bearer TKN')

    def test_provider_failure_becomes_502(self):
        with override_settings(SMS_BACKEND='eskiz', ESKIZ_EMAIL='a@b.uz', ESKIZ_PASSWORD='x'), \
                mock.patch('apps.core.sms.requests.post', side_effect=RuntimeError('boom')):
            with self.assertRaises(sms.SmsFailed):
                sms.send_sms(PHONE, 'x')


class PasswordResetTests(SmsTestCase):
    def setUp(self):
        super().setUp()
        self.user = make('u1', phone=PHONE)
        self.client = APIClient()

    def post(self, step, data):
        return self.client.post(f'/api/v1/auth/password/reset/{step}/', data, format='json')

    def start(self):
        resp = self.post('request', {'phone': PHONE})
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def test_full_flow_changes_the_password_and_closes_sessions(self):
        client = APIClient()
        login = client.post('/api/v1/auth/login/', {'username': 'u1', 'password': PASSWORD}).json()
        body = self.start()
        self.assertEqual(body, {'sent': True, 'expires_in': 120, 'retry_after': 45})
        self.assertEqual(sms.sent[-1][0], '998901234567')
        verified = self.post('verify', {'phone': PHONE, 'code': last_code()})
        self.assertEqual(verified.status_code, 200, verified.content)
        token = verified.json()['reset_token']
        self.assertEqual(verified.json()['expires_in'], 600)
        done = self.post('confirm', {'reset_token': token, 'password': NEW_PASSWORD})
        self.assertEqual((done.status_code, done.json()), (200, {'ok': True}))
        fresh = APIClient()
        self.assertEqual(fresh.post('/api/v1/auth/login/', {'username': 'u1', 'password': NEW_PASSWORD}).status_code, 200)
        self.assertEqual(fresh.post('/api/v1/auth/login/', {'username': 'u1', 'password': PASSWORD}).status_code, 401)
        self.assertIsNotNone(User.objects.get(username='u1').password_changed_at)
        refresh = APIClient().post('/api/v1/auth/token/refresh/', {'refresh': login['refresh']}, format='json')
        self.assertEqual(refresh.status_code, 401)  # eski seanslar yopildi
        self.assertTrue(UserSession.objects.filter(user=self.user, revoked_at__isnull=False).exists())

    def test_phone_can_be_typed_in_any_format_and_unknown_phone_is_404(self):
        self.assertEqual(self.post('request', {'phone': '90 123 45 67'}).status_code, 200)
        self.assertEqual(self.post('request', {'phone': '+998909999999'}).status_code, 404)
        self.assertEqual(len(sms.sent), 1)

    def test_resend_cooldown_and_daily_cap(self):
        self.start()
        again = self.post('request', {'phone': PHONE})
        self.assertEqual(again.status_code, 429)
        self.assertTrue(again.json()['error']['details']['detail'])
        self.assertEqual(len(sms.sent), 1)  # ikkinchi SMS ketmadi
        with mock.patch.object(otp, 'RETRY_AFTER', 0):
            for _ in range(otp.DAILY_LIMIT - 1):
                self.assertEqual(self.post('request', {'phone': PHONE}).status_code, 200)
            self.assertEqual(self.post('request', {'phone': PHONE}).status_code, 429)

    def test_wrong_code_attempts_and_expiry(self):
        self.start()
        code = last_code()
        wrong = '00000' if code != '00000' else '11111'
        for _ in range(otp.MAX_ATTEMPTS):
            self.assertEqual(self.post('verify', {'phone': PHONE, 'code': wrong}).status_code, 400)
        # urinishlar tugadi: to'g'ri kod ham endi o'tmaydi
        self.assertEqual(self.post('verify', {'phone': PHONE, 'code': code}).status_code, 400)
        cache.clear()
        self.assertEqual(self.post('verify', {'phone': PHONE, 'code': code}).status_code, 400)  # muddati o'tgan

    def test_code_and_token_are_single_use(self):
        self.start()
        code = last_code()
        token = self.post('verify', {'phone': PHONE, 'code': code}).json()['reset_token']
        self.assertEqual(self.post('verify', {'phone': PHONE, 'code': code}).status_code, 400)
        self.assertEqual(self.post('confirm', {'reset_token': token, 'password': NEW_PASSWORD}).status_code, 200)
        self.assertEqual(self.post('confirm', {'reset_token': token, 'password': 'AnotherPass789!'}).status_code, 400)
        self.assertEqual(self.post('confirm', {'reset_token': 'garbage', 'password': NEW_PASSWORD}).status_code, 400)

    def test_weak_password_is_refused_and_the_token_stays_usable(self):
        self.start()
        token = self.post('verify', {'phone': PHONE, 'code': last_code()}).json()['reset_token']
        weak = self.post('confirm', {'reset_token': token, 'password': '123'})
        self.assertEqual(weak.status_code, 400)
        self.assertEqual(self.post('confirm', {'reset_token': token, 'password': NEW_PASSWORD}).status_code, 200)

    def test_every_account_of_the_same_phone_is_reset(self):
        parent = make('p1', User.Role.PARENT, phone='998901234567')
        self.start()
        token = self.post('verify', {'phone': PHONE, 'code': last_code()}).json()['reset_token']
        self.post('confirm', {'reset_token': token, 'password': NEW_PASSWORD})
        self.assertTrue(User.objects.get(pk=parent.pk).check_password(NEW_PASSWORD))
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password(NEW_PASSWORD))

    def test_inactive_accounts_are_ignored_and_no_provider_gives_503(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.post('request', {'phone': PHONE}).status_code, 404)
        User.objects.filter(pk=self.user.pk).update(is_active=True)
        with override_settings(SMS_BACKEND='', ESKIZ_EMAIL='', ESKIZ_PASSWORD=''):
            resp = self.post('request', {'phone': PHONE})
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()['error']['code'], 'sms_not_configured')
        self.assertEqual(self.post('request', {'phone': PHONE}).status_code, 200)  # 503 sovitishni kuydirmadi


class TwoFactorTests(SmsTestCase):
    def setUp(self):
        super().setUp()
        self.user = make('u1', phone=PHONE)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def enable(self):
        self.assertEqual(self.client.post('/api/v1/auth/2fa/enable/', {'password': PASSWORD}, format='json').status_code, 200)
        resp = self.client.post('/api/v1/auth/2fa/confirm/', {'code': last_code()}, format='json')
        self.assertEqual((resp.status_code, resp.json()), (200, {'enabled': True}))

    def test_enable_confirm_disable(self):
        self.assertEqual(self.client.get('/api/v1/auth/2fa/').json(), {'enabled': False})
        self.enable()
        self.assertEqual(self.client.get('/api/v1/auth/2fa/').json(), {'enabled': True})
        self.assertTrue(self.client.get('/api/v1/auth/me/').json()['two_factor_enabled'])
        wrong = self.client.post('/api/v1/auth/2fa/disable/', {'password': 'bad'}, format='json')
        self.assertEqual(wrong.status_code, 400)
        off = self.client.post('/api/v1/auth/2fa/disable/', {'password': PASSWORD}, format='json')
        self.assertEqual(off.json(), {'enabled': False})
        self.assertFalse(User.objects.get(pk=self.user.pk).two_factor_enabled)

    def test_enable_needs_password_phone_and_a_provider(self):
        bad = self.client.post('/api/v1/auth/2fa/enable/', {'password': 'bad'}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(len(sms.sent), 0)
        User.objects.filter(pk=self.user.pk).update(phone=None)
        self.user.refresh_from_db()
        self.client.force_authenticate(self.user)
        nophone = self.client.post('/api/v1/auth/2fa/enable/', {'password': PASSWORD}, format='json')
        self.assertEqual(nophone.status_code, 400)
        User.objects.filter(pk=self.user.pk).update(phone=PHONE)
        self.user.refresh_from_db()
        self.client.force_authenticate(self.user)
        with override_settings(SMS_BACKEND='', ESKIZ_EMAIL='', ESKIZ_PASSWORD=''):
            self.assertEqual(self.client.post('/api/v1/auth/2fa/enable/', {'password': PASSWORD}, format='json').status_code, 503)
        self.assertFalse(User.objects.get(pk=self.user.pk).two_factor_enabled)  # provayder yo'q — yoqilmaydi

    def test_wrong_code_does_not_enable_it(self):
        self.client.post('/api/v1/auth/2fa/enable/', {'password': PASSWORD}, format='json')
        code = last_code()
        wrong = '00000' if code != '00000' else '11111'
        self.assertEqual(self.client.post('/api/v1/auth/2fa/confirm/', {'code': wrong}, format='json').status_code, 400)
        self.assertFalse(User.objects.get(pk=self.user.pk).two_factor_enabled)

    def test_login_asks_for_the_code_and_only_then_gives_tokens(self):
        self.enable()
        sms.sent.clear()
        anon = APIClient()
        first = anon.post('/api/v1/auth/login/', {'username': 'u1', 'password': PASSWORD})
        self.assertEqual(first.status_code, 200)
        body = first.json()
        self.assertEqual((body['two_factor_required'], body['expires_in'], body['phone_hint']), (True, 120, '+998*****4567'))
        self.assertNotIn('access', body)
        self.assertEqual(len(sms.sent), 1)
        self.assertEqual(UserSession.objects.count(), 0)  # hali seans ochilmadi
        wrong = anon.post('/api/v1/auth/2fa/login/', {'challenge_token': body['challenge_token'], 'code': '00000'}, format='json')
        self.assertEqual(wrong.status_code, 400)
        ok = anon.post('/api/v1/auth/2fa/login/', {'challenge_token': body['challenge_token'], 'code': last_code()}, format='json')
        self.assertEqual(ok.status_code, 200, ok.content)
        tokens = ok.json()
        authed = APIClient()
        authed.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        self.assertEqual(authed.get('/api/v1/auth/me/').status_code, 200)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)
        replay = anon.post('/api/v1/auth/2fa/login/', {'challenge_token': body['challenge_token'], 'code': last_code()}, format='json')
        self.assertEqual(replay.status_code, 400)  # bir martalik

    def test_login_without_2fa_is_unchanged_and_bad_password_still_401(self):
        make('plain', phone='+998900000009')
        anon = APIClient()
        resp = anon.post('/api/v1/auth/login/', {'username': 'plain', 'password': PASSWORD})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.json())
        self.enable()
        self.assertEqual(anon.post('/api/v1/auth/login/', {'username': 'u1', 'password': 'bad'}).status_code, 401)
        self.assertEqual(anon.post('/api/v1/auth/2fa/login/', {'challenge_token': 'x', 'code': '1'}, format='json').status_code, 400)


class NotifyPreferencesTests(APITestCase):
    def test_flags_are_editable_through_me(self):
        user = make('u1')
        self.client.force_authenticate(user)
        me = self.client.get('/api/v1/auth/me/').json()
        self.assertEqual((me['notify_messages'], me['notify_email']), (True, False))
        resp = self.client.patch('/api/v1/auth/me/', {'notify_messages': False, 'notify_email': True}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.json()['notify_messages'], resp.json()['notify_email']), (False, True))
        user.refresh_from_db()
        self.assertEqual((user.notify_messages, user.notify_email), (False, True))
        locked = self.client.patch('/api/v1/auth/me/', {'two_factor_enabled': True}, format='json')
        self.assertFalse(locked.json()['two_factor_enabled'])  # 2FA faqat SMS tasdiqlash orqali yoqiladi
