from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import NotificationRecipient

from .models import FaqItem, HelpVideo


class SupportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sp_u', password='x', role='student')
        self.other = User.objects.create_user(username='sp_o', password='x', role='student')
        self.admin = User.objects.create_user(username='sp_a', password='x', role='admin')

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def create(self):
        return self.api(self.user).post(
            '/api/v1/support/tickets/', {'subject': 'Kira olmayapman', 'message': 'Parol ishlamayapti'}, format='json',
        )

    def test_create_notifies_admin_and_lists_own_only(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['messages'][0]['body'], 'Parol ishlamayapti')
        self.assertTrue(NotificationRecipient.objects.filter(user=self.admin, notification__kind='support_new').exists())
        self.assertEqual(len(self.api(self.user).get('/api/v1/support/tickets/').json()), 1)
        self.assertEqual(len(self.api(self.other).get('/api/v1/support/tickets/').json()), 0)

    def test_validation(self):
        api = self.api(self.user)
        self.assertEqual(api.post('/api/v1/support/tickets/', {'subject': '', 'message': 'x'}, format='json').status_code, 400)
        self.assertEqual(api.post('/api/v1/support/tickets/', {'subject': 'x', 'message': ' '}, format='json').status_code, 400)

    def test_other_user_cannot_read_but_admin_can(self):
        ticket_id = self.create().json()['id']
        self.assertEqual(self.api(self.other).get(f'/api/v1/support/tickets/{ticket_id}/').status_code, 403)
        self.assertEqual(self.api(self.admin).get(f'/api/v1/support/tickets/{ticket_id}/').status_code, 200)

    def test_admin_reply_notifies_user_and_changes_status(self):
        ticket_id = self.create().json()['id']
        response = self.api(self.admin).post(f'/api/v1/support/tickets/{ticket_id}/reply/', {'message': 'Parolni tiklang'}, format='json')
        self.assertEqual((response.status_code, response.json()['status']), (200, 'answered'))
        self.assertTrue(response.json()['messages'][-1]['from_staff'])
        self.assertTrue(NotificationRecipient.objects.filter(user=self.user, notification__kind='support_reply').exists())
        back = self.api(self.user).post(f'/api/v1/support/tickets/{ticket_id}/reply/', {'message': 'Rahmat'}, format='json')
        self.assertEqual(back.json()['status'], 'open')

    def test_admin_sees_all_tickets_with_flag(self):
        self.create()
        self.assertEqual(len(self.api(self.admin).get('/api/v1/support/tickets/?all=1').json()), 1)
        self.assertEqual(len(self.api(self.admin).get('/api/v1/support/tickets/').json()), 0)

    def test_closed_ticket_rejects_replies(self):
        ticket_id = self.create().json()['id']
        self.api(self.user).post(f'/api/v1/support/tickets/{ticket_id}/close/')
        response = self.api(self.user).post(f'/api/v1/support/tickets/{ticket_id}/reply/', {'message': 'yana'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_help_videos_and_faq_filter_by_role(self):
        HelpVideo.objects.create(title='Umumiy', url='https://example.com/1', duration_seconds=90)
        HelpVideo.objects.create(title='Teacher', url='https://example.com/2', role='teacher')
        HelpVideo.objects.create(title='Yashirin', url='https://example.com/3', is_active=False)
        FaqItem.objects.create(question='Q1', answer='A1')
        FaqItem.objects.create(question='Q2', answer='A2', role='teacher')
        api = self.api(self.user)
        self.assertEqual([v['title'] for v in api.get('/api/v1/help/videos/').json()], ['Umumiy'])
        self.assertEqual(len(api.get('/api/v1/help/videos/?role=teacher').json()), 2)
        self.assertEqual([f['question'] for f in api.get('/api/v1/help/faq/').json()], ['Q1'])
