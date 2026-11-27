"""Email bilan kirish: tasdiqlangan email (katta-kichik harfsiz), tasdiqlanmagan email uchun aniq xabar, o'zbekcha xato, kirish tarixi."""
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.core.models import AuditLog

PASSWORD = 'Test-pass-123'


class EmailLoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='ali', password=PASSWORD, role='teacher', is_approved=True, email='Ali.Test@Mail.uz', email_verified=True)
        self.unverified = User.objects.create_user(
            username='vali', password=PASSWORD, role='teacher', is_approved=True, email='vali@mail.uz', email_verified=False)

    def login(self, identifier, password=PASSWORD):
        return self.client.post('/api/v1/auth/login/', {'username': identifier, 'password': password}, format='json')

    def test_verified_email_works_case_insensitive_and_trimmed(self):
        for identifier in ('ali', 'Ali.Test@Mail.uz', 'ali.test@mail.uz', 'ALI.TEST@MAIL.UZ', '  ali.test@mail.uz '):
            self.assertEqual(self.login(identifier).status_code, 200, identifier)

    def test_unverified_email_with_the_right_password_gets_a_clear_message(self):
        response = self.login('vali@mail.uz')
        self.assertEqual(response.status_code, 400)
        self.assertIn('tasdiqlanmagan', response.json()['error']['message'])

    def test_unverified_email_with_a_wrong_password_stays_generic(self):
        response = self.login('vali@mail.uz', 'xato-parol')
        self.assertEqual(response.status_code, 401)  # email bor-yo'qligi begonaga bilinmaydi
        self.assertEqual(self.login('yoq@mail.uz', 'xato-parol').json(), response.json())

    def test_wrong_credentials_message_is_uzbek(self):
        for response in (self.login('ali', 'xato'), self.login('ali.test@mail.uz', 'xato'), self.login('nomalum', 'xato')):
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['error']['message'], "Login yoki parol noto'g'ri.")

    def test_login_by_email_is_written_to_the_login_journal(self):
        before = AuditLog.objects.filter(action='auth.login', actor=self.user).count()
        self.assertEqual(self.login('ali.test@mail.uz').status_code, 200)
        self.assertEqual(AuditLog.objects.filter(action='auth.login', actor=self.user).count(), before + 1)

    def test_email_on_several_accounts_asks_for_the_login(self):
        User.objects.create_user(
            username='ali_parent', password=PASSWORD, role='parent', is_approved=True, email='ali.test@mail.uz', email_verified=True)
        response = self.login('ali.test@mail.uz')
        self.assertEqual(response.status_code, 400)
        self.assertIn('bir nechta akkaunt', response.json()['error']['message'])
