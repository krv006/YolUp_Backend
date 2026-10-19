"""Faol seanslar (qurilmalar) va akkauntni faolsizlantirish."""
from unittest import mock

from django.test import TransactionTestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import sessions
from apps.accounts.models import User, UserSession
from apps.lessons.models import Course

PASSWORD = 'StrongPass123!'
CHROME = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
PHONE = 'Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36'


def make(username, role, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def login(username='u1', agent=CHROME, **headers):
    client = APIClient()
    resp = client.post(
        '/api/v1/auth/login/', {'username': username, 'password': PASSWORD}, HTTP_USER_AGENT=agent, **headers,
    )
    assert resp.status_code == 200, resp.content
    return resp.json()


def authed(tokens):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
    return client


class SessionTests(APITestCase):
    def setUp(self):
        self.user = make('u1', User.Role.STUDENT)

    def test_login_creates_a_session_and_the_list_marks_the_current_one(self):
        web = login()
        phone = login(agent=PHONE)
        rows = authed(web).get('/api/v1/auth/sessions/').json()
        self.assertEqual(len(rows), 2)
        current = [r for r in rows if r['is_current']]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]['device'], 'Chrome · Windows')
        self.assertEqual({r['device'] for r in rows}, {'Chrome · Windows', 'Chrome · SM-A546B'})
        self.assertIsNone(rows[0]['city'])
        self.assertEqual(len(authed(phone).get('/api/v1/auth/sessions/').json()), 2)

    def test_app_can_name_its_device(self):
        tokens = login(agent='okhttp/4.12', HTTP_X_DEVICE_NAME='Samsung Galaxy A54')
        rows = authed(tokens).get('/api/v1/auth/sessions/').json()
        self.assertEqual(rows[0]['device'], 'Samsung Galaxy A54')
        self.assertEqual(sessions.parse_device('okhttp/4.12'), 'Mobil ilova')
        self.assertEqual(sessions.parse_device(''), "Noma'lum qurilma")

    def test_logout_others_kicks_the_other_device_immediately(self):
        web, phone = login(), login(agent=PHONE)
        self.assertEqual(authed(phone).get('/api/v1/auth/me/').status_code, 200)
        resp = authed(web).post('/api/v1/auth/sessions/logout-others/')
        self.assertEqual(resp.json(), {'revoked': 1})
        self.assertEqual(authed(phone).get('/api/v1/auth/me/').status_code, 401)  # access token darhol o'chdi
        refresh = APIClient().post('/api/v1/auth/token/refresh/', {'refresh': phone['refresh']}, format='json')
        self.assertEqual(refresh.status_code, 401)
        self.assertEqual(authed(web).get('/api/v1/auth/me/').status_code, 200)  # joriy qurilma joyida
        self.assertEqual(len(authed(web).get('/api/v1/auth/sessions/').json()), 1)

    def test_delete_one_session(self):
        web, phone = login(), login(agent=PHONE)
        rows = authed(web).get('/api/v1/auth/sessions/').json()
        other = next(r for r in rows if not r['is_current'])
        self.assertEqual(authed(web).delete(f'/api/v1/auth/sessions/{other["id"]}/').status_code, 204)
        self.assertEqual(authed(phone).get('/api/v1/auth/me/').status_code, 401)
        self.assertEqual(authed(web).delete(f'/api/v1/auth/sessions/{other["id"]}/').status_code, 404)

    def test_other_users_sessions_are_untouchable(self):
        make('u2', User.Role.STUDENT)
        theirs = login('u2')
        theirs_id = authed(theirs).get('/api/v1/auth/sessions/').json()[0]['id']
        mine = login()
        self.assertEqual(authed(mine).delete(f'/api/v1/auth/sessions/{theirs_id}/').status_code, 404)
        self.assertEqual(authed(theirs).get('/api/v1/auth/me/').status_code, 200)

    def test_refresh_keeps_the_session_and_updates_activity(self):
        tokens = login()
        before = UserSession.objects.get(user=self.user)
        resp = APIClient().post('/api/v1/auth/token/refresh/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        fresh = resp.json()
        self.assertEqual(RefreshToken(fresh['refresh'])['sid'], str(before.id))
        rows = authed(fresh).get('/api/v1/auth/sessions/').json()
        self.assertEqual([r['is_current'] for r in rows], [True])
        self.assertGreaterEqual(UserSession.objects.get(user=self.user).last_active, before.last_active)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)

    def test_legacy_tokens_are_upgraded_on_refresh(self):
        legacy = RefreshToken.for_user(self.user)  # `sid`siz eski token
        self.assertNotIn('sid', legacy)
        self.assertEqual(authed({'access': str(legacy.access_token)}).post('/api/v1/auth/sessions/logout-others/').status_code, 400)
        resp = APIClient().post('/api/v1/auth/token/refresh/', {'refresh': str(legacy)}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)
        upgraded = resp.json()
        self.assertEqual([r['is_current'] for r in authed(upgraded).get('/api/v1/auth/sessions/').json()], [True])
        self.assertEqual(authed(upgraded).post('/api/v1/auth/sessions/logout-others/').json(), {'revoked': 0})

    def test_logout_closes_the_session(self):
        web, phone = login(), login(agent=PHONE)
        resp = authed(web).post('/api/v1/auth/logout/', {'refresh': web['refresh']}, format='json')
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(authed(web).get('/api/v1/auth/me/').status_code, 401)
        self.assertEqual(len(authed(phone).get('/api/v1/auth/sessions/').json()), 1)

    def test_register_and_account_switch_tokens_carry_a_session(self):
        resp = APIClient().post('/api/v1/auth/register/', {
            'username': 'new1', 'password': PASSWORD, 'role': 'parent', 'phone': '+998901112233',
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertTrue(RefreshToken(resp.json()['refresh'])['sid'])
        self.assertEqual(len(authed(resp.json()).get('/api/v1/auth/sessions/').json()), 1)
        make('new1_teacher', User.Role.TEACHER, phone='+998901112233')
        target = User.objects.get(username='new1_teacher')
        switched = authed(resp.json()).post(f'/api/v1/auth/switch/{target.id}/')
        self.assertEqual(switched.status_code, 200, switched.content)
        self.assertTrue(RefreshToken(switched.json()['refresh'])['sid'])
        self.assertEqual(UserSession.objects.filter(user=target).count(), 1)

    def test_old_sessions_are_capped(self):
        with mock.patch.object(sessions, 'MAX_ACTIVE_SESSIONS', 2):
            first = login()
            login()
            login()
        self.assertEqual(UserSession.objects.filter(user=self.user, revoked_at__isnull=True).count(), 2)
        self.assertEqual(authed(first).get('/api/v1/auth/me/').status_code, 401)

    def test_other_logins_are_unaffected(self):
        resp = APIClient().post('/api/v1/auth/login/', {'username': 'u1', 'password': 'wrong'})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(UserSession.objects.count(), 0)


class DeactivateAccountTests(APITestCase):
    def test_account_is_deactivated_not_deleted(self):
        teacher = make('t1', User.Role.TEACHER, phone='+998900000001')
        course = Course.objects.create(teacher=teacher, title='Algebra')
        tokens = login('t1')
        other = login('t1', agent=PHONE)
        resp = authed(tokens).delete('/api/v1/auth/me/')
        self.assertEqual(resp.status_code, 204, resp.content)
        teacher.refresh_from_db()
        course.refresh_from_db()
        self.assertFalse(teacher.is_active)
        self.assertFalse(course.is_active)
        self.assertTrue(User.objects.filter(pk=teacher.pk).exists())
        self.assertTrue(Course.objects.filter(pk=course.pk).exists())
        for token in (tokens, other):
            self.assertEqual(authed(token).get('/api/v1/auth/me/').status_code, 401)
            refresh = APIClient().post('/api/v1/auth/token/refresh/', {'refresh': token['refresh']}, format='json')
            self.assertEqual(refresh.status_code, 401)
        self.assertEqual(APIClient().post('/api/v1/auth/login/', {'username': 't1', 'password': PASSWORD}).status_code, 401)
        self.assertEqual(UserSession.objects.filter(user=teacher, revoked_at__isnull=True).count(), 0)

    def test_password_is_checked_when_given(self):
        make('s1', User.Role.STUDENT)
        tokens = login('s1')
        wrong = authed(tokens).delete('/api/v1/auth/me/', {'password': 'wrong'}, format='json')
        self.assertEqual(wrong.status_code, 400)
        self.assertTrue(User.objects.get(username='s1').is_active)
        ok = authed(tokens).delete('/api/v1/auth/me/', {'password': PASSWORD}, format='json')
        self.assertEqual(ok.status_code, 204)

    def test_admins_cannot_deactivate_themselves(self):
        make('adm', User.Role.ADMIN)
        tokens = login('adm')
        self.assertEqual(authed(tokens).delete('/api/v1/auth/me/').status_code, 403)
        self.assertTrue(User.objects.get(username='adm').is_active)

    def test_deactivated_account_disappears_from_linked_accounts_and_role_switch(self):
        teacher = make('t1', User.Role.TEACHER, phone='+998900000002')
        parent = make('p1', User.Role.PARENT, phone='+998900000002')
        tokens = login('t1')
        self.assertEqual([a['username'] for a in authed(tokens).get('/api/v1/auth/me/').json()['linked_accounts']], ['p1'])
        parent.is_active = False
        parent.save()
        self.assertEqual(authed(tokens).get('/api/v1/auth/me/').json()['linked_accounts'], [])
        resp = authed(tokens).post('/api/v1/auth/switch-role/', {'role': 'parent'}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(User.objects.filter(phone='+998900000002').count(), 2)
        self.assertTrue(teacher.is_active)

    def test_requires_login(self):
        self.assertEqual(APIClient().delete('/api/v1/auth/me/').status_code, 401)


class SocketRevocationTests(TransactionTestCase):
    def test_revoked_session_token_is_not_accepted_by_websocket_auth(self):
        from asgiref.sync import async_to_sync

        from apps.chat.ws_auth import _user_from_token

        make('u1', User.Role.STUDENT)
        tokens = login()
        user = async_to_sync(_user_from_token)(tokens['access'])
        self.assertEqual(user.username, 'u1')
        sessions.revoke(UserSession.objects.get())
        self.assertFalse(async_to_sync(_user_from_token)(tokens['access']).is_authenticated)
