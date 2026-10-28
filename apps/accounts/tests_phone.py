"""Telefonni SMS bilan tasdiqlash (ro'yxatdan o'tish va raqamni o'zgartirish), profil rasmini o'chirish, kirishlar tarixi."""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.core import sms

from .models import User
from .tests_sms_flows import PASSWORD, PHONE, SmsTestCase, last_code, make

NEW_PHONE = '+998935556677'


def register_body(**extra):
    return {'username': 'newbie', 'password': PASSWORD, 'role': 'student', 'phone': PHONE, **extra}


class RegisterPhoneTests(SmsTestCase):
    def verified_token(self, phone=PHONE):
        self.assertEqual(self.client.post('/api/v1/auth/register/phone/request/', {'phone': phone}).status_code, 200)
        response = self.client.post('/api/v1/auth/register/phone/verify/', {'phone': phone, 'code': last_code()})
        self.assertEqual(response.status_code, 200)
        return response.json()['phone_token']

    def test_request_returns_timing_and_sends_five_digit_code(self):
        response = self.client.post('/api/v1/auth/register/phone/request/', {'phone': PHONE})
        data = response.json()
        self.assertEqual((data['sent'], data['expires_in'], data['retry_after']), (True, 120, 45))
        self.assertEqual(len(last_code()), 5)

    def test_too_early_resend_has_retry_after(self):
        self.client.post('/api/v1/auth/register/phone/request/', {'phone': PHONE})
        response = self.client.post('/api/v1/auth/register/phone/request/', {'phone': PHONE})
        self.assertEqual(response.status_code, 429)

    def test_wrong_code_rejected(self):
        self.client.post('/api/v1/auth/register/phone/request/', {'phone': PHONE})
        response = self.client.post('/api/v1/auth/register/phone/verify/', {'phone': PHONE, 'code': '00000'})
        self.assertEqual(response.status_code, 400)

    def test_bad_phone_rejected(self):
        self.assertEqual(self.client.post('/api/v1/auth/register/phone/request/', {'phone': 'abc'}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/auth/register/phone/request/', {}).status_code, 400)

    def test_register_with_token_marks_phone_verified(self):
        token = self.verified_token()
        response = self.client.post('/api/v1/auth/register/', register_body(phone_token=token), format='json')
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username='newbie')
        self.assertTrue(user.phone_verified)
        self.assertIsNotNone(user.phone_verified_at)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
        me = self.client.get('/api/v1/auth/me/').json()
        self.assertTrue(me['phone_verified'])
        self.assertIsNotNone(me['phone_verified_at'])

    def test_register_without_token_stays_unverified(self):
        response = self.client.post('/api/v1/auth/register/', register_body(), format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(User.objects.get(username='newbie').phone_verified)

    def test_token_is_single_use(self):
        token = self.verified_token()
        self.assertEqual(self.client.post('/api/v1/auth/register/', register_body(phone_token=token), format='json').status_code, 201)
        second = self.client.post('/api/v1/auth/register/', register_body(username='other', phone_token=token), format='json')
        self.assertEqual(second.status_code, 400)

    def test_token_for_another_number_rejected(self):
        token = self.verified_token()
        response = self.client.post('/api/v1/auth/register/', register_body(phone=NEW_PHONE, phone_token=token), format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='newbie').exists())

    def test_garbage_token_rejected(self):
        self.assertEqual(self.client.post('/api/v1/auth/register/', register_body(phone_token='nope'), format='json').status_code, 400)


class ChangePhoneTests(SmsTestCase):
    def setUp(self):
        super().setUp()
        self.user = make('changer', phone=PHONE, phone_verified=False)
        self.client.force_authenticate(self.user)

    def test_change_flow_replaces_number_and_verifies(self):
        self.assertEqual(self.client.post('/api/v1/auth/me/phone/request/', {'phone': NEW_PHONE}).status_code, 200)
        self.assertEqual(sms.sent[-1][0], '998935556677')
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, PHONE)  # tasdiqlanguncha o'zgarmaydi
        response = self.client.post('/api/v1/auth/me/phone/confirm/', {'phone': NEW_PHONE, 'code': last_code()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['phone'], NEW_PHONE)
        self.assertTrue(response.json()['phone_verified'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, NEW_PHONE)

    def test_wrong_code_keeps_old_number(self):
        self.client.post('/api/v1/auth/me/phone/request/', {'phone': NEW_PHONE})
        self.assertEqual(self.client.post('/api/v1/auth/me/phone/confirm/', {'phone': NEW_PHONE, 'code': '00000'}).status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, PHONE)

    def test_code_for_other_user_does_not_work(self):
        self.client.post('/api/v1/auth/me/phone/request/', {'phone': NEW_PHONE})
        code = last_code()
        intruder = make('intruder', phone='+998901112222')
        other = APIClient()
        other.force_authenticate(intruder)
        self.assertEqual(other.post('/api/v1/auth/me/phone/confirm/', {'phone': NEW_PHONE, 'code': code}).status_code, 400)

    def test_requires_login(self):
        self.assertEqual(APIClient().post('/api/v1/auth/me/phone/request/', {'phone': NEW_PHONE}).status_code, 401)

    def test_patch_phone_resets_verification(self):
        self.user.phone_verified = True
        self.user.save()
        response = self.client.patch('/api/v1/auth/me/', {'phone': NEW_PHONE}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['phone_verified'])


class AvatarAndUsernameTests(SmsTestCase):
    def test_delete_avatar(self):
        user = make('picture')
        buffer = io.BytesIO()
        Image.new('RGB', (20, 20), 'red').save(buffer, 'PNG')
        user.avatar = SimpleUploadedFile('a.png', buffer.getvalue(), content_type='image/png')
        user.save()
        self.client.force_authenticate(user)
        self.assertEqual(self.client.delete('/api/v1/auth/me/avatar/').status_code, 204)
        user.refresh_from_db()
        self.assertFalse(user.avatar)
        self.assertEqual(self.client.delete('/api/v1/auth/me/avatar/').status_code, 204)  # takroriy chaqiruv xato emas

    def test_username_can_be_changed_and_duplicates_rejected(self):
        user = make('before')
        make('taken')
        self.client.force_authenticate(user)
        self.assertEqual(self.client.patch('/api/v1/auth/me/', {'username': 'after_x'}, format='json').status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.username, 'after_x')
        response = self.client.patch('/api/v1/auth/me/', {'username': 'taken'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.json()['error']['details'])


class LoginHistoryTests(SmsTestCase):
    def setUp(self):
        super().setUp()
        self.user = make('hist')
        for i in range(12):
            self.client.post('/api/v1/auth/login/', {'username': 'hist', 'password': PASSWORD}, HTTP_USER_AGENT=f'Agent-{i % 2}')
        token = self.client.post('/api/v1/auth/login/', {'username': 'hist', 'password': PASSWORD}, HTTP_USER_AGENT='Agent-me').json()['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}', HTTP_USER_AGENT='Agent-me')

    def test_plain_array_by_default(self):
        data = self.client.get('/api/v1/auth/logins/').json()
        self.assertIsInstance(data, list)
        self.assertIn('location', data[0])

    def test_pagination_and_current_flag(self):
        page1 = self.client.get('/api/v1/auth/logins/?page=1&page_size=5').json()
        self.assertEqual((page1['count'], len(page1['results'])), (13, 5))
        self.assertIsNotNone(page1['next'])
        self.assertIsNone(page1['previous'])
        self.assertTrue(page1['results'][0]['is_current'])
        self.assertEqual(sum(r['is_current'] for r in page1['results']), 1)
        page3 = self.client.get('/api/v1/auth/logins/?page=3&page_size=5').json()
        self.assertEqual(len(page3['results']), 3)
        self.assertIsNone(page3['next'])
