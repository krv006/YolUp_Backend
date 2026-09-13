from django.conf import settings
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.tests import login, register


def make_admin(client, username='admin1'):
    """RegisterView faqat teacher/parent'ni ochiq ro'yxatdan o'tkazadi — admin to'g'ridan-to'g'ri yaratiladi."""
    user = User.objects.create_user(username=username, password='StrongPass123!', role=User.Role.ADMIN)
    return user


class NotificationTests(APITestCase):
    def setUp(self):
        self.admin = make_admin(self.client)
        self.admin_token = login(self.client, self.admin.username)

        register(self.client, 't1', 'teacher')
        self.teacher_token = login(self.client, 't1')
        self.teacher = User.objects.get(username='t1')

        register(self.client, 'p1', 'parent')
        self.parent_token = login(self.client, 'p1')

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_non_admin_cannot_send(self):
        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/notifications/send/', {
            'description': '<p>Salom</p>', 'target_type': 'user', 'user_id': str(self.teacher.id),
        })
        self.assertEqual(resp.status_code, 403)

    def test_admin_sends_to_single_user(self):
        self.auth(self.admin_token)
        resp = self.client.post('/api/v1/notifications/send/', {
            'description': '<p>Ertaga nazorat ishi</p>', 'target_type': 'user',
            'user_id': str(self.teacher.id),
        })
        self.assertEqual(resp.status_code, 201)

        # teacher inbox'ida ko'rinadi, o'qilmagan
        self.auth(self.teacher_token)
        inbox = self.client.get('/api/v1/notifications/').json()['results']
        self.assertEqual(len(inbox), 1)
        self.assertFalse(inbox[0]['is_read'])
        self.assertIn('Ertaga nazorat ishi', inbox[0]['notification']['description'])

        # boshqa foydalanuvchi (parent) inbox'ida ko'rinmaydi
        self.auth(self.parent_token)
        inbox = self.client.get('/api/v1/notifications/').json()['results']
        self.assertEqual(len(inbox), 0)

    def test_admin_sends_to_all(self):
        self.auth(self.admin_token)
        resp = self.client.post('/api/v1/notifications/send/', {
            'description': '<p>Platforma yangilandi</p>', 'target_type': 'all',
        })
        self.assertEqual(resp.status_code, 201)
        notification_id = resp.json()['id']

        for token in (self.teacher_token, self.parent_token):
            self.auth(token)
            inbox = self.client.get('/api/v1/notifications/').json()['results']
            self.assertEqual(len(inbox), 1)

        # admin o'zining sent ro'yxatida umumiy/o'qilgan sonini ko'radi
        self.auth(self.admin_token)
        sent = self.client.get('/api/v1/notifications/sent/').json()['results']
        self.assertEqual(sent[0]['total_count'], 2)  # teacher + parent (admin o'ziga yubormaydi)
        self.assertEqual(sent[0]['read_count'], 0)

        recipients = self.client.get(f'/api/v1/notifications/{notification_id}/recipients/').json()
        self.assertEqual(len(recipients), 2)

    def test_mark_read_updates_unread_count_and_sent_stats(self):
        self.auth(self.admin_token)
        resp = self.client.post('/api/v1/notifications/send/', {
            'description': '<p>Xabar</p>', 'target_type': 'user', 'user_id': str(self.teacher.id),
        })
        notification_id = resp.json()['id']

        self.auth(self.teacher_token)
        self.assertEqual(self.client.get('/api/v1/notifications/unread-count/').json()['count'], 1)
        self.client.post(f'/api/v1/notifications/{notification_id}/read/')
        self.assertEqual(self.client.get('/api/v1/notifications/unread-count/').json()['count'], 0)

        self.auth(self.admin_token)
        sent = self.client.get('/api/v1/notifications/sent/').json()['results']
        self.assertEqual(sent[0]['read_count'], 1)

    def test_html_is_sanitized(self):
        self.auth(self.admin_token)
        resp = self.client.post('/api/v1/notifications/send/', {
            'description': '<p>Salom</p><script>alert(1)</script>',
            'target_type': 'user', 'user_id': str(self.teacher.id),
        })
        self.assertEqual(resp.status_code, 201)
        self.assertNotIn('<script>', resp.json()['description'])

    def test_empty_description_rejected(self):
        self.auth(self.admin_token)
        resp = self.client.post('/api/v1/notifications/send/', {
            'description': '   ', 'target_type': 'user', 'user_id': str(self.teacher.id),
        })
        self.assertEqual(resp.status_code, 400)

    def test_user_search_admin_only(self):
        self.auth(self.teacher_token)
        resp = self.client.get('/api/v1/auth/users/search/?q=p1')
        self.assertEqual(resp.status_code, 403)

        self.auth(self.admin_token)
        resp = self.client.get('/api/v1/auth/users/search/?q=p1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(resp.json()[0]['username'], 'p1')


class PushNotificationTests(APITestCase):
    """Web Push obunasi — ilova/tab yopiq bo'lganda ham xabar yetkazish."""

    def setUp(self):
        self.admin = make_admin(self.client)
        self.admin_token = login(self.client, self.admin.username)
        register(self.client, 'pt1', 'teacher')
        self.teacher_token = login(self.client, 'pt1')
        self.teacher = User.objects.get(username='pt1')

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_vapid_key_is_public(self):
        self.auth(self.teacher_token)
        resp = self.client.get('/api/v1/notifications/push/vapid-key/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['public_key'], settings.VAPID_PUBLIC_KEY)

    def test_subscribe_and_unsubscribe(self):
        from apps.notifications.models import PushSubscription

        self.auth(self.teacher_token)
        resp = self.client.post('/api/v1/notifications/push/subscribe/', {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/abc123',
            'keys': {'p256dh': 'pkey', 'auth': 'akey'},
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(PushSubscription.objects.filter(user=self.teacher).count(), 1)

        resp = self.client.post('/api/v1/notifications/push/unsubscribe/', {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/abc123',
        })
        self.assertEqual(resp.json()['removed'], True)
        self.assertEqual(PushSubscription.objects.filter(user=self.teacher).count(), 0)

    def test_resubscribing_same_endpoint_updates_not_duplicates(self):
        from apps.notifications.models import PushSubscription

        self.auth(self.teacher_token)
        body = {'endpoint': 'https://fcm.googleapis.com/fcm/send/dup', 'keys': {'p256dh': 'p1', 'auth': 'a1'}}
        self.client.post('/api/v1/notifications/push/subscribe/', body, format='json')
        body['keys']['p256dh'] = 'p2'
        self.client.post('/api/v1/notifications/push/subscribe/', body, format='json')
        self.assertEqual(PushSubscription.objects.filter(endpoint=body['endpoint']).count(), 1)
        self.assertEqual(PushSubscription.objects.get(endpoint=body['endpoint']).p256dh, 'p2')

    def test_sending_notification_triggers_web_push_to_subscribed_device(self):
        from unittest.mock import patch

        from . import services

        services.save_push_subscription(
            user=self.teacher, endpoint='https://fcm.googleapis.com/fcm/send/xyz',
            p256dh='pkey', auth='akey',
        )
        # send_notification `transaction.on_commit`da yuboradi — TestCase'ning
        # o'ralgan tranzaksiyasi hech qachon commit bo'lmaydi, shuning uchun
        # on_commit hook'larni majburan ishga tushirish kerak.
        with patch('pywebpush.webpush') as mock_webpush, self.captureOnCommitCallbacks(execute=True):
            self.auth(self.admin_token)
            resp = self.client.post('/api/v1/notifications/send/', {
                'description': '<p>Salom</p>', 'target_type': 'user', 'user_id': str(self.teacher.id),
            })
            self.assertEqual(resp.status_code, 201)
        mock_webpush.assert_called_once()
        call_kwargs = mock_webpush.call_args.kwargs
        self.assertEqual(call_kwargs['subscription_info']['endpoint'], 'https://fcm.googleapis.com/fcm/send/xyz')

    def test_expired_subscription_is_removed_on_410(self):
        from unittest.mock import patch

        from pywebpush import WebPushException

        from apps.notifications.models import PushSubscription

        from . import services

        services.save_push_subscription(
            user=self.teacher, endpoint='https://fcm.googleapis.com/fcm/send/gone',
            p256dh='pkey', auth='akey',
        )

        class FakeResponse:
            status_code = 410

        with patch('pywebpush.webpush', side_effect=WebPushException('gone', response=FakeResponse())), \
                self.captureOnCommitCallbacks(execute=True):
            self.auth(self.admin_token)
            self.client.post('/api/v1/notifications/send/', {
                'description': '<p>Salom</p>', 'target_type': 'user', 'user_id': str(self.teacher.id),
            })
        self.assertFalse(PushSubscription.objects.filter(endpoint='https://fcm.googleapis.com/fcm/send/gone').exists())
