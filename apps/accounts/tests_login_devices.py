"""Kirish tarixi qurilmalar bo'yicha (`GET /auth/logins/?group=device`): har qurilma bitta qator, oxirgi kirish vaqti va soni bilan
(Trello "kirish tarixi qism da", 2026-11-21)."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Consent, ParentChildLink, User
from apps.core.models import AuditLog

PASSWORD = 'StrongPass123!'
CHROME_WIN = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36'
CHROME_WIN_NEWER = CHROME_WIN.replace('Chrome/157', 'Chrome/158')
CHROME_MAC = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36'
APP = 'okhttp/4.12.0'


def make(username, role):
    user = User(username=username, role=role)
    user.set_password(PASSWORD)
    user.save()
    return user


def client_for(user, **extra):
    client = APIClient(**extra)
    client.force_authenticate(user)
    return client


class LoginDevicesTests(APITestCase):
    def setUp(self):
        self.student = make('ld_s', User.Role.STUDENT)
        self.parent = make('ld_p', User.Role.PARENT)
        ParentChildLink.objects.create(parent=self.parent, student=self.student, status=ParentChildLink.Status.APPROVED)

    def login(self, agent, ip='1.2.3.4', device_name=None, force=True):
        extra = {'HTTP_USER_AGENT': agent, 'HTTP_X_FORWARDED_FOR': ip}
        if device_name:
            extra['HTTP_X_DEVICE_NAME'] = device_name
        data = {'username': 'ld_s', 'password': PASSWORD}
        if force:
            data['force'] = 'true'
        response = APIClient().post('/api/v1/auth/login/', data, **extra)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def devices(self, query='', user=None, **extra):
        return (client_for(user or self.student, **extra)).get(f'/api/v1/auth/logins/?group=device{query}')

    def test_many_logins_on_one_device_collapse_into_one_row(self):
        for ip in ('1.1.1.1', '1.1.1.2', '1.1.1.3'):
            self.login(CHROME_WIN, ip=ip)
        rows = self.devices().json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['login_count'], 3)
        self.assertEqual(rows[0]['last_ip'], '1.1.1.3')  # IP faqat oxirgi kirishdan
        self.assertEqual(rows[0]['device_type'], 'computer')
        self.assertIn('last_login_at', rows[0])
        self.assertLessEqual(rows[0]['first_login_at'], rows[0]['last_login_at'])

    def test_browser_update_does_not_make_a_new_device(self):
        self.login(CHROME_WIN)
        self.login(CHROME_WIN_NEWER)
        self.assertEqual(len(self.devices().json()), 1)

    def test_different_devices_are_separate_rows_newest_first(self):
        self.login(CHROME_WIN)
        self.login(CHROME_MAC)
        self.login(APP)
        rows = self.devices().json()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['device'], 'Mobil ilova')  # eng oxirgi kirgan birinchi
        self.assertEqual({r['device'] for r in rows}, {'Mobil ilova', 'Chrome · Windows', 'Chrome · macOS'})

    def test_two_phones_of_the_same_app_are_told_apart_by_device_name(self):
        self.login(APP, device_name='Xiaomi Redmi Note 12')
        self.login(APP, device_name='iPhone 15')
        self.login(APP, device_name='Xiaomi Redmi Note 12', ip='9.9.9.9')
        rows = self.devices().json()
        by_name = {r['device']: r for r in rows}
        self.assertEqual(set(by_name), {'Xiaomi Redmi Note 12', 'iPhone 15'})
        self.assertEqual(by_name['Xiaomi Redmi Note 12']['login_count'], 2)

    def test_last_active_follows_the_session_not_only_the_login(self):
        from apps.accounts.models import UserSession

        self.login(APP)
        before = self.devices().json()[0]
        self.assertEqual(before['last_seen_at'], before['last_login_at'])  # hali faollik yangilanmagan
        later = timezone.now() + timedelta(days=2)
        UserSession.objects.filter(user=self.student).update(last_active=later)
        row = self.devices().json()[0]
        self.assertGreater(row['last_seen_at'], row['last_login_at'])  # mobil ilova qayta kirmasdan ishlayapti
        self.assertEqual(row['last_login_at'], before['last_login_at'])  # kirish vaqti o'zgarmaydi

    def test_devices_are_ordered_by_last_seen(self):
        from apps.accounts.models import UserSession

        self.login(CHROME_WIN)
        self.login(APP)
        self.assertEqual([r['device'] for r in self.devices().json()], ['Mobil ilova', 'Chrome · Windows'])  # eng yangi kirish birinchi
        UserSession.objects.filter(user=self.student, user_agent__startswith='Mozilla').update(last_active=timezone.now() + timedelta(days=1))
        self.assertEqual([r['device'] for r in self.devices().json()], ['Chrome · Windows', 'Mobil ilova'])

    def test_current_device_and_session_state(self):
        self.login(CHROME_WIN)
        tokens = self.login(APP)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        rows = client.get('/api/v1/auth/logins/?group=device', HTTP_USER_AGENT=APP).json()
        current = [r for r in rows if r['is_current']]
        self.assertEqual([r['device'] for r in current], ['Mobil ilova'])
        self.assertTrue(current[0]['session_active'])
        win = next(r for r in rows if r['device'] == 'Chrome · Windows')
        self.assertTrue(win['session_active'])  # ikkala qurilma seansi ochiq
        client.post('/api/v1/auth/logout/', {'refresh': tokens['refresh']}, format='json')
        after = {r['device']: r for r in client_for(self.student).get('/api/v1/auth/logins/?group=device').json()}
        self.assertFalse(after['Mobil ilova']['session_active'])
        self.assertTrue(after['Chrome · Windows']['session_active'])

    def test_device_type_and_date_filters(self):
        self.login(CHROME_WIN)
        self.login(APP)
        self.assertEqual([r['device_type'] for r in self.devices('&device=phone').json()], ['phone'])
        self.assertEqual(self.devices('&device=tablet').json(), [])
        tomorrow = timezone.localtime().date() + timedelta(days=1)
        self.assertEqual(self.devices(f'&from={tomorrow}').json(), [])

    def test_paginated_envelope_counts_devices(self):
        self.login(CHROME_WIN)
        self.login(CHROME_MAC)
        self.login(APP)
        body = self.devices('&page=1&page_size=2').json()
        self.assertEqual(body['count'], 3)
        self.assertEqual(len(body['results']), 2)
        self.assertIsNotNone(body['next'])

    def test_invalid_group_is_rejected(self):
        self.assertEqual(client_for(self.student).get('/api/v1/auth/logins/?group=ip').status_code, 400)

    def test_without_group_the_old_per_login_list_is_unchanged(self):
        self.login(CHROME_WIN)
        self.login(CHROME_WIN)
        rows = client_for(self.student).get('/api/v1/auth/logins/').json()
        self.assertEqual(len(rows), 2)
        self.assertIn('user_agent', rows[0])

    def test_parent_sees_child_devices_with_consent_rules(self):
        self.login(CHROME_WIN)
        self.login(CHROME_WIN)
        rows = client_for(self.parent).get(f'/api/v1/auth/logins/?group=device&student={self.student.pk}').json()
        self.assertEqual((len(rows), rows[0]['login_count']), (1, 2))
        self.assertFalse(rows[0]['is_current'])  # ota-ona o'z qurilmasi emas
        stranger = make('ld_p2', User.Role.PARENT)
        self.assertEqual(client_for(stranger).get(f'/api/v1/auth/logins/?group=device&student={self.student.pk}').status_code, 403)
        Consent.objects.create(student=self.student, granted_by=self.parent, kind=Consent.Kind.ANALYTICS, granted=False)
        self.assertEqual(client_for(self.parent).get(f'/api/v1/auth/logins/?group=device&student={self.student.pk}').status_code, 403)

    def test_old_login_rows_without_device_name_still_group_by_user_agent(self):
        AuditLog.objects.create(actor=self.student, action='auth.login', ip_address='5.5.5.5', meta={'user_agent': CHROME_WIN})
        rows = self.devices().json()
        self.assertEqual((rows[0]['device'], rows[0]['login_count']), ('Chrome · Windows', 1))
