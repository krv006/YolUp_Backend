"""Google / Apple bilan kirish: token tekshiruvi (haqiqiy RSA imzo bilan) va kirish/ro'yxatdan o'tish oqimi."""
import time
from unittest import mock

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APITestCase

from . import social
from .models import SocialIdentity, User

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_token(**overrides):
    claims = {
        'iss': 'https://accounts.google.com', 'aud': 'web-client', 'sub': 'g-123', 'email': 'Ali@Example.com',
        'email_verified': True, 'given_name': 'Ali', 'family_name': 'Valiyev', 'exp': int(time.time()) + 600,
    }
    claims.update(overrides)
    signer = overrides.pop('_key', None) or KEY
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, signer, algorithm='RS256')


class FakeJwks:
    def get_signing_key_from_jwt(self, token):
        return mock.Mock(key=KEY.public_key())


@override_settings(GOOGLE_CLIENT_IDS=['web-client', 'ios-client'], APPLE_CLIENT_IDS=['com.yolup.app'])
class VerifyTokenTests(SimpleTestCase):
    def verify(self, token, provider='google'):
        with mock.patch.object(social, '_jwks_client', return_value=FakeJwks()):
            return social.verify_id_token(provider, token)

    def test_valid_google_token(self):
        claims = self.verify(make_token())
        self.assertEqual((claims.subject, claims.email, claims.email_verified), ('g-123', 'ali@example.com', True))
        self.assertEqual((claims.first_name, claims.last_name), ('Ali', 'Valiyev'))

    def test_second_audience_accepted(self):
        self.assertEqual(self.verify(make_token(aud='ios-client')).subject, 'g-123')

    def test_wrong_audience_rejected(self):
        with self.assertRaises(AuthenticationFailed):
            self.verify(make_token(aud='someone-elses-app'))

    def test_wrong_issuer_rejected(self):
        with self.assertRaises(AuthenticationFailed):
            self.verify(make_token(iss='https://evil.example.com'))

    def test_expired_rejected(self):
        with self.assertRaises(AuthenticationFailed):
            self.verify(make_token(exp=int(time.time()) - 10))

    def test_bad_signature_rejected(self):
        token = jwt.encode({'iss': 'https://accounts.google.com', 'aud': 'web-client', 'sub': 'x', 'exp': int(time.time()) + 60},
                           OTHER_KEY, algorithm='RS256')
        with self.assertRaises(AuthenticationFailed):
            self.verify(token)

    def test_missing_subject_rejected(self):
        with self.assertRaises(AuthenticationFailed):
            self.verify(make_token(sub=None))

    def test_apple_string_email_verified(self):
        token = make_token(iss='https://appleid.apple.com', aud='com.yolup.app', email_verified='true')
        self.assertTrue(self.verify(token, 'apple').email_verified)

    def test_empty_token_rejected(self):
        with self.assertRaises(AuthenticationFailed):
            self.verify('')

    @override_settings(GOOGLE_CLIENT_IDS=[])
    def test_unconfigured_provider(self):
        with self.assertRaises(social.SocialLoginNotConfigured):
            self.verify(make_token())


def claims(**kw):
    data = dict(provider='google', subject='g-123', email='ali@example.com', email_verified=True, first_name='Ali', last_name='Valiyev')
    data.update(kw)
    return social.SocialClaims(**data)


class SocialLoginFlowTests(APITestCase):
    url = '/api/v1/auth/social/google/'

    def post(self, found=None, **body):
        with mock.patch.object(social, 'verify_id_token', return_value=found or claims()):
            return self.client.post(self.url, {'id_token': 'x', **body}, format='json')

    def test_new_user_without_role_asks_for_signup(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['signup_required'])
        self.assertEqual(response.json()['email'], 'ali@example.com')
        self.assertFalse(User.objects.exists())

    def test_new_user_with_role_is_created_and_logged_in(self):
        response = self.post(role='student')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('access', data)
        user = User.objects.get(pk=data['id'])
        self.assertEqual((user.role, user.email, user.email_verified, user.first_name), ('student', 'ali@example.com', True, 'Ali'))
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.username, 'ali')
        self.assertTrue(SocialIdentity.objects.filter(user=user, provider='google', subject='g-123').exists())
        # token ishlaydi
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 200)

    def test_returning_user_logs_in_without_role(self):
        first = self.post(role='parent')
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(first.status_code, 201)

    def test_username_collision_gets_suffix(self):
        User.objects.create_user(username='ali', password='x')
        response = self.post(role='student')
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(response.json()['username'], 'ali')
        self.assertTrue(response.json()['username'].startswith('ali'))

    def test_links_to_existing_account_with_verified_email(self):
        existing = User.objects.create_user(username='ali_old', password='x', email='ali@example.com', email_verified=True)
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(SocialIdentity.objects.filter(user=existing).exists())

    def test_does_not_link_when_existing_email_unverified(self):
        User.objects.create_user(username='ali_old', password='x', email='ali@example.com', email_verified=False)
        response = self.post()
        self.assertTrue(response.json()['signup_required'])
        self.assertFalse(SocialIdentity.objects.exists())

    def test_does_not_link_when_provider_email_unverified(self):
        User.objects.create_user(username='ali_old', password='x', email='ali@example.com', email_verified=True)
        response = self.post(found=claims(email_verified=False))
        self.assertTrue(response.json()['signup_required'])

    def test_ambiguous_email_is_not_linked(self):
        for name in ('a1', 'a2'):
            User.objects.create_user(username=name, password='x', email='ali@example.com', email_verified=True)
        self.assertTrue(self.post().json()['signup_required'])

    def test_two_factor_account_gets_challenge_not_tokens(self):
        user = User.objects.create_user(username='tf', password='x', two_factor_enabled=True, phone='+998901112233')
        SocialIdentity.objects.create(user=user, provider='google', subject='g-123')
        with mock.patch('apps.accounts.services.two_factor_challenge', return_value={'two_factor_required': True, 'challenge_token': 'c'}):
            response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['two_factor_required'])
        self.assertNotIn('access', response.json())

    def test_inactive_user_rejected(self):
        user = User.objects.create_user(username='off', password='x', is_active=False)
        SocialIdentity.objects.create(user=user, provider='google', subject='g-123')
        self.assertEqual(self.post().status_code, 403)

    def test_invalid_role_rejected(self):
        self.assertEqual(self.post(role='admin').status_code, 400)

    def test_unknown_provider_404(self):
        response = self.client.post('/api/v1/auth/social/facebook/', {'id_token': 'x'}, format='json')
        self.assertEqual(response.status_code, 404)

    @override_settings(GOOGLE_CLIENT_IDS=[], APPLE_CLIENT_IDS=[])
    def test_unconfigured_returns_503(self):
        response = self.client.post(self.url, {'id_token': 'x'}, format='json')
        self.assertEqual(response.status_code, 503)

    def test_bad_token_is_401(self):
        with override_settings(GOOGLE_CLIENT_IDS=['web-client']):
            with mock.patch.object(social, '_jwks_client', side_effect=Exception('network')):
                response = self.client.post(self.url, {'id_token': 'abc.def.ghi'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_apple_names_from_client_are_used(self):
        with mock.patch.object(social, 'verify_id_token', return_value=claims(provider='apple', first_name='', last_name='', subject='a-1')):
            response = self.client.post(
                '/api/v1/auth/social/apple/', {'id_token': 'x', 'role': 'student', 'first_name': 'Sardor', 'last_name': 'Karimov'},
                format='json',
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual((response.json()['first_name'], response.json()['last_name']), ('Sardor', 'Karimov'))
