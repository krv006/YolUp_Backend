"""Avtomatik ochilgan rol-akkaunt paroli (oldin tasodifiy edi), `sync_provisioned_passwords` buyrug'i va parol xabarlari tili."""
from io import StringIO

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.tests import PASSWORD, login, register
from apps.core import audit
from apps.core.models import AuditLog

PHONE = '+998907654399'
NEW_PASSWORD = 'BrandNewPass456!'


class ProvisionedPasswordTests(APITestCase):
    def switch(self, role):
        return self.client.post('/api/v1/auth/switch-role/', {'role': role}, format='json')

    def provisioned_parent(self):
        register(self.client, 'pp_teacher', 'teacher', phone=PHONE)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "pp_teacher")}')
        resp = self.switch('parent')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.client.credentials()
        return User.objects.get(phone=PHONE, role='parent')

    def test_a_new_role_account_gets_the_source_password(self):
        parent = self.provisioned_parent()
        teacher = User.objects.get(username='pp_teacher')
        self.assertEqual(parent.password, teacher.password)
        self.assertTrue(parent.check_password(PASSWORD))

    def test_the_new_account_can_log_in_with_its_login_and_the_known_password(self):
        parent = self.provisioned_parent()
        resp = self.client.post('/api/v1/auth/login/', {'username': parent.username, 'password': PASSWORD})
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_the_new_account_can_change_its_password(self):
        parent = self.provisioned_parent()
        token = self.client.post('/api/v1/auth/login/', {'username': parent.username, 'password': PASSWORD}).json()['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        resp = self.client.post('/api/v1/auth/password/change/', {'current_password': PASSWORD, 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        parent.refresh_from_db()
        self.assertTrue(parent.check_password(NEW_PASSWORD))
        # manba akkaunt paroli o'zgarmaydi
        self.assertTrue(User.objects.get(username='pp_teacher').check_password(PASSWORD))

    def test_a_wrong_current_password_is_still_rejected(self):
        parent = self.provisioned_parent()
        token = self.client.post('/api/v1/auth/login/', {'username': parent.username, 'password': PASSWORD}).json()['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        resp = self.client.post('/api/v1/auth/password/change/', {'current_password': 'Wrong-Pass-999!', 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_an_unlinked_account_does_not_inherit_anything(self):
        register(self.client, 'pp_other', 'teacher', phone='+998907654300')
        other = User.objects.get(username='pp_other')
        parent = self.provisioned_parent()
        self.assertNotEqual(parent.password, other.password)  # xesh tuzi boshqa; nusxa faqat manbadan


class SyncCommandTests(APITestCase):
    """Eski (tasodifiy parolli) avtomatik ochilgan akkauntlarni tuzatish."""

    def make_pair(self, suffix=''):
        teacher = User(username=f'sc_t{suffix}', role='teacher', is_approved=True, phone=PHONE)
        teacher.set_password(PASSWORD)
        teacher.save()
        parent = User(username=f'sc_p{suffix}', role='parent', phone=PHONE)
        parent.set_password('random-unknown-token')
        parent.save()
        from apps.accounts.services import _link_accounts

        _link_accounts(teacher, parent)
        audit.record(action='auth.role_auto_provisioned', actor=teacher, target=parent, meta={'role': 'parent'})
        return teacher, parent

    def run_cmd(self, *args):
        out = StringIO()
        call_command('sync_provisioned_passwords', *args, stdout=out)
        return out.getvalue()

    def test_dry_run_changes_nothing_and_says_so(self):
        teacher, parent = self.make_pair()
        before = parent.password
        text = self.run_cmd()
        parent.refresh_from_db()
        self.assertEqual(parent.password, before)
        self.assertIn('SINOV', text)
        self.assertIn('1 ta akkaunt', text)

    def test_apply_copies_the_source_password(self):
        teacher, parent = self.make_pair()
        self.run_cmd('--apply')
        parent.refresh_from_db()
        self.assertTrue(parent.check_password(PASSWORD))
        self.assertTrue(AuditLog.objects.filter(action='auth.password_synced_from_source', target_id=str(parent.pk)).exists())

    def test_a_password_the_user_set_is_never_overwritten(self):
        teacher, parent = self.make_pair()
        parent.set_password('My-Own-Password-1!')
        parent.password_changed_at = timezone.now()
        parent.save()
        text = self.run_cmd('--apply')
        parent.refresh_from_db()
        self.assertTrue(parent.check_password('My-Own-Password-1!'))
        self.assertIn("o'zgartirilgan", text)

    def test_unlinked_or_inactive_accounts_are_skipped(self):
        teacher, parent = self.make_pair('1')
        User.objects.filter(pk=parent.pk).update(link_group=None)
        teacher2, parent2 = self.make_pair('2')
        User.objects.filter(pk=parent2.pk).update(is_active=False)
        text = self.run_cmd('--apply')
        self.assertIn("0 ta akkaunt", text)
        self.assertIn("o'tkazib yuborilgan: 2", text)
        parent.refresh_from_db()
        self.assertFalse(parent.check_password(PASSWORD))

    def test_running_twice_is_safe(self):
        self.make_pair()
        self.run_cmd('--apply')
        text = self.run_cmd('--apply')
        self.assertIn('0 ta akkaunt', text)
        self.assertIn('allaqachon bir xil', text)
        self.assertEqual(AuditLog.objects.filter(action='auth.password_synced_from_source').count(), 1)

    def test_accounts_not_created_by_provisioning_are_never_touched(self):
        teacher = User(username='sc_plain_t', role='teacher', is_approved=True, phone='+998907654311')
        teacher.set_password(PASSWORD)
        teacher.save()
        parent = User(username='sc_plain_p', role='parent', phone='+998907654311')
        parent.set_password('other-password-1')
        parent.save()
        before = parent.password
        self.run_cmd('--apply')
        parent.refresh_from_db()
        self.assertEqual(parent.password, before)


class PasswordMessageLanguageTests(APITestCase):
    """Django parol tekshiruvi xabarlari uz/ru/en tilida (uz oldin inglizcha chiqardi)."""

    def setUp(self):
        register(self.client, 'pm_user', 'student')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(self.client, "pm_user")}')

    def change(self, lang, new_password):
        resp = self.client.post(
            '/api/v1/auth/password/change/', {'current_password': PASSWORD, 'new_password': new_password}, format='json',
            HTTP_ACCEPT_LANGUAGE=lang,
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        return ' | '.join(resp.json()['error']['details']['new_password'])

    def test_uzbek_messages(self):
        text = self.change('uz', '12345678')
        self.assertIn('Bu parol juda oddiy', text)
        self.assertIn('faqat raqamlardan', text)
        self.assertNotIn('This password', text)
        self.assertIn('kamida 8 ta belgi', self.change('uz', 'abc'))

    def test_the_similarity_message_is_uzbek_and_says_login(self):
        text = self.change('uz', 'pm_user12')
        self.assertIn('Parol quyidagi ma\'lumotga juda o\'xshash: login', text)

    def test_russian_and_english_are_unchanged(self):
        self.assertIn('слишком широко распространён', self.change('ru', '12345678'))
        self.assertIn('This password is too common.', self.change('en', '12345678'))

    def test_default_language_is_uzbek(self):
        resp = self.client.post('/api/v1/auth/password/change/', {'current_password': PASSWORD, 'new_password': '12345678'}, format='json')
        self.assertIn('Bu parol juda oddiy', ' '.join(resp.json()['error']['details']['new_password']))
