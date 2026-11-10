"""Telefon raqami `+998XXXXXXXXX` ko'rinishida saqlanadi; akkauntlar raqamlar bo'yicha bog'lanadi (2026-11-10)."""
import importlib

from django.apps import apps as django_apps
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts import selectors
from apps.accounts.models import User


def make(username, role=User.Role.TEACHER, phone=None):
    user = User(username=username, role=role, phone=phone, is_approved=True)
    user.set_password('x')
    user.save()
    return user


class PhoneNormalizeTests(TestCase):
    def test_save_normalizes_every_input_style(self):
        for i, raw in enumerate(['901234567', '+998 90 123 45 67', '998901234567', '+998(90)123-45-67', '+998901234567']):
            self.assertEqual(make(f'n{i}', phone=raw).phone, '+998901234567', raw)

    def test_garbage_and_empty_are_left_alone(self):
        self.assertEqual(make('g1', phone='abc').phone, 'abc')
        self.assertIsNone(make('g2', phone=None).phone)
        self.assertEqual(make('g3', phone='').phone, '')

    def test_accounts_saved_in_different_styles_are_linked(self):
        teacher = make('t1', User.Role.TEACHER, '901234567')
        parent = make('p1', User.Role.PARENT, '+998 90 123 45 67')
        student = make('s1', User.Role.STUDENT, '998901234567')
        self.assertEqual({u.pk for u in selectors.linked_accounts(teacher)}, {parent.pk, student.pk})

    def test_linking_works_even_for_rows_stored_in_the_old_style(self):
        teacher = make('t1', User.Role.TEACHER, '+998901234567')
        parent = make('p1', User.Role.PARENT, '+998901234567')
        # eski (migratsiyagacha) ma'lumot: save() chetlab to'g'ridan-to'g'ri yoziladi
        User.objects.filter(pk=parent.pk).update(phone='901234567')
        self.assertEqual([u.pk for u in selectors.linked_accounts(teacher)], [parent.pk])

    def test_me_lists_all_three_accounts_and_switch_works(self):
        teacher = make('t1', User.Role.TEACHER, '901234567')
        make('p1', User.Role.PARENT, '+998 90 123 45 67')
        make('s1', User.Role.STUDENT, '+998901234567')
        client = APIClient()
        client.force_authenticate(teacher)
        me = client.get('/api/v1/auth/me/').json()
        self.assertEqual(sorted(a['username'] for a in me['linked_accounts']), ['p1', 's1'])

    def test_data_migration_normalizes_existing_rows(self):
        a = make('m1', phone='+998901234567')
        b = make('m2', phone='+998900000002')
        c = make('m3', phone='+998900000003')
        User.objects.filter(pk=a.pk).update(phone='90 123 45 67')
        User.objects.filter(pk=b.pk).update(phone='998900000002')
        User.objects.filter(pk=c.pk).update(phone='nomer yo\'q')
        migration = importlib.import_module('apps.accounts.migrations.0022_normalize_phones')
        migration.normalize_phones(django_apps, None)
        self.assertEqual(User.objects.get(pk=a.pk).phone, '+998901234567')
        self.assertEqual(User.objects.get(pk=b.pk).phone, '+998900000002')
        self.assertEqual(User.objects.get(pk=c.pk).phone, "nomer yo'q")
