"""Ota-ona uchun kirishlar tarixi (qurilma/brauzer/OS/filtrlar/seans) va farzand seanslari (BACKEND_OTA_ONA.md 6, 13, 14-bandlar)."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Consent, ParentChildLink, User, UserSession
from apps.accounts.sessions import parse_ua
from apps.notifications.models import NotificationRecipient

PASSWORD = 'StrongPass123!'
CHROME_WIN = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
ANDROID = 'Mozilla/5.0 (Linux; Android 14; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36'
IPAD = 'Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1'


def make(username, role, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def inbox(user, kind):
    return list(NotificationRecipient.objects.filter(user=user, notification__kind=kind).select_related('notification'))


class ParseUaTests(APITestCase):
    def test_desktop_phone_tablet_and_app(self):
        self.assertEqual(parse_ua(CHROME_WIN), {'browser': 'Chrome 130', 'os': 'Windows', 'device_type': 'computer'})
        phone = parse_ua(ANDROID)
        self.assertEqual((phone['browser'], phone['os'], phone['device_type']), ('Chrome 129', 'Android 14', 'phone'))
        tablet = parse_ua(IPAD)
        self.assertEqual((tablet['browser'], tablet['os'], tablet['device_type']), ('Safari 17', 'iOS 17.4', 'tablet'))
        self.assertEqual(parse_ua('okhttp/4.12')['device_type'], 'phone')
        self.assertEqual(parse_ua('')['device_type'], 'computer')


class ParentLoginHistoryTests(APITestCase):
    def setUp(self):
        self.parent = make('p1', User.Role.PARENT)
        self.other_parent = make('p2', User.Role.PARENT)
        self.student = make('s1', User.Role.STUDENT, first_name='Toshmat')
        ParentChildLink.objects.create(parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)

    def login(self, agent, ip='1.2.3.4'):
        response = APIClient().post('/api/v1/auth/login/', {'username': 's1', 'password': PASSWORD}, HTTP_USER_AGENT=agent, HTTP_X_FORWARDED_FOR=ip)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def history(self, query='', user=None):
        response = client_for(user or self.parent).get(f'/api/v1/auth/logins/?student={self.student.pk}{query}')
        return response

    def test_rows_carry_parsed_device_browser_os_and_session(self):
        tokens = self.login(ANDROID)
        body = self.history().json()
        row = body[0]
        self.assertEqual((row['browser'], row['os'], row['device_type']), ('Chrome 129', 'Android 14', 'phone'))
        self.assertIn('SM-A546B', row['device'])
        self.assertEqual(row['ip'], '1.2.3.4')
        self.assertTrue(row['session_active'])
        self.assertIsNotNone(row['duration_seconds'])
        self.assertEqual(row['session_id'], str(UserSession.objects.get(user=self.student).pk))
        self.assertIn('id', row)
        self.assertFalse(row['recognized'])
        self.assertIn('refresh', tokens)

    def test_session_state_follows_logout(self):
        tokens = self.login(CHROME_WIN)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        client.post('/api/v1/auth/logout/', {'refresh': tokens['refresh']}, format='json')
        row = self.history().json()[0]
        self.assertFalse(row['session_active'])

    def test_device_and_date_filters(self):
        self.login(CHROME_WIN)
        self.login(ANDROID)
        self.assertEqual({r['device_type'] for r in self.history().json()}, {'computer', 'phone'})
        phones = self.history('&device=phone').json()
        self.assertEqual([r['device_type'] for r in phones], ['phone'])
        self.assertEqual(self.history('&device=tablet').json(), [])
        self.assertEqual(self.history('&device=robot').status_code, 400)
        today = timezone.localtime().date()
        self.assertEqual(len(self.history(f'&from={today}&to={today}').json()), 2)
        tomorrow = today + timedelta(days=1)
        self.assertEqual(self.history(f'&from={tomorrow}').json(), [])

    def test_consent_and_link_gates(self):
        self.login(CHROME_WIN)
        self.assertEqual(self.history(user=self.other_parent).status_code, 403)
        Consent.objects.create(student=self.student, granted_by=self.parent, kind=Consent.Kind.ANALYTICS, granted=False)
        denied = self.history()
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()['error']['code'], 'consent_required')
        own = client_for(self.student).get('/api/v1/auth/logins/')  # o'quvchining o'z tarixi cheklanmaydi
        self.assertEqual(own.status_code, 200)

    def test_recognized_device_stops_raising_new_device_alerts(self):
        self.login(CHROME_WIN)
        self.login(ANDROID)  # yangi qurilma -> ota-onaga xabar
        self.assertEqual(len(inbox(self.parent, 'security.new_device')), 1)
        phone_row = next(r for r in self.history().json() if r['device_type'] == 'phone')
        self.assertTrue(phone_row['new_device'])
        response = client_for(self.parent).post(f"/api/v1/auth/logins/{phone_row['id']}/recognize/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(next(r for r in self.history().json() if r['id'] == phone_row['id'])['recognized'])
        self.login(CHROME_WIN)
        self.login(ANDROID)  # endi tanish qurilma: yana xabar yo'q
        self.assertEqual(len(inbox(self.parent, 'security.new_device')), 2)  # ...faqat Chrome<->Android almashuvi emas
        latest_phone = next(r for r in self.history().json() if r['device_type'] == 'phone')
        self.assertFalse(latest_phone['new_device'])
        self.assertTrue(latest_phone['recognized'])

    def test_recognize_is_limited_to_the_childs_parent(self):
        self.login(CHROME_WIN)
        row_id = self.history().json()[0]['id']
        self.assertEqual(client_for(self.other_parent).post(f'/api/v1/auth/logins/{row_id}/recognize/').status_code, 403)
        self.assertEqual(client_for(self.student).post(f'/api/v1/auth/logins/{row_id}/recognize/').status_code, 403)
        self.assertEqual(client_for(self.parent).post('/api/v1/auth/logins/00000000-0000-0000-0000-000000000000/recognize/').status_code, 404)


class ChildSessionsTests(APITestCase):
    def setUp(self):
        self.parent = make('p1', User.Role.PARENT)
        self.other_parent = make('p2', User.Role.PARENT)
        self.student = make('s1', User.Role.STUDENT, first_name='Toshmat')
        ParentChildLink.objects.create(parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)
        for agent, ip in ((CHROME_WIN, '1.1.1.1'), (ANDROID, '2.2.2.2')):
            APIClient().post('/api/v1/auth/login/', {'username': 's1', 'password': PASSWORD}, HTTP_USER_AGENT=agent, HTTP_X_FORWARDED_FOR=ip)
        self.base = f'/api/v1/auth/children/{self.student.pk}/sessions/'

    def test_list_shows_the_childs_sessions_with_parsed_device(self):
        body = client_for(self.parent).get(self.base).json()
        self.assertEqual(len(body), 2)
        self.assertTrue(all(item['active'] for item in body))
        self.assertEqual({item['device_type'] for item in body}, {'computer', 'phone'})
        self.assertEqual({item['ip'] for item in body}, {'1.1.1.1', '2.2.2.2'})

    def test_foreign_parent_and_student_cannot_manage_them(self):
        self.assertEqual(client_for(self.other_parent).get(self.base).status_code, 403)
        self.assertEqual(client_for(self.student).get(self.base).status_code, 403)

    def test_end_one_session_revokes_it_and_tells_the_child(self):
        session = UserSession.objects.filter(user=self.student).first()
        response = client_for(self.parent).delete(f'{self.base}{session.pk}/')
        self.assertEqual(response.status_code, 204)
        session.refresh_from_db()
        self.assertIsNotNone(session.revoked_at)
        self.assertEqual(len(inbox(self.student, 'security.session_ended')), 1)
        self.assertEqual(client_for(self.parent).delete(f'{self.base}{session.pk}/').status_code, 404)  # allaqachon yopilgan

    def test_logout_all_ends_every_active_session(self):
        response = client_for(self.parent).post(f'{self.base}logout-all/')
        self.assertEqual(response.json(), {'ended': 2})
        self.assertEqual(UserSession.objects.filter(user=self.student, revoked_at__isnull=True).count(), 0)
        (item,) = inbox(self.student, 'security.session_ended')
        self.assertEqual(item.notification.data['count'], 2)
        self.assertEqual(client_for(self.parent).post(f'{self.base}logout-all/').json(), {'ended': 0})

    def test_cannot_end_another_childs_session_through_this_childs_url(self):
        stranger = make('s9', User.Role.STUDENT)
        APIClient().post('/api/v1/auth/login/', {'username': 's9', 'password': PASSWORD})
        foreign = UserSession.objects.get(user=stranger)
        self.assertEqual(client_for(self.parent).delete(f'{self.base}{foreign.pk}/').status_code, 404)
        foreign.refresh_from_db()
        self.assertIsNone(foreign.revoked_at)
