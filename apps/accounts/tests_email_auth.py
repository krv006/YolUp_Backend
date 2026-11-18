"""Email bilan: ro'yxatdan o'tish (tasdiqlangan email), email bilan kirish, parolni emailga kod bilan tiklash, profilda emailni qo'shish."""
import re

from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User, UserSession
from apps.accounts.services import create_child

PASSWORD = 'StrongPass123!'
NEW_PASSWORD = 'BrandNewPass456!'
EMAIL = 'ali@example.com'


def make(username, role=User.Role.STUDENT, **extra):
    user = User(username=username, role=role, **extra)
    user.set_password(PASSWORD)
    user.save()
    return user


def details(response):
    return response.json()['error']['details']


def mailed_code():
    return re.search(r'\b(\d{5})\b', mail.outbox[-1].body).group(1)


class EmailCase(APITestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        self.client = APIClient()

    def post(self, path, data=None, client=None):
        return (client or self.client).post(f'/api/v1/auth/{path}/', data or {}, format='json')

    def verified_token(self, email=EMAIL):
        self.assertEqual(self.post('register/email/request', {'email': email}).status_code, 200)
        resp = self.post('register/email/verify', {'email': email, 'code': mailed_code()})
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()['email_token']

    def register_payload(self, **extra):
        return {'username': 'ali01', 'password': PASSWORD, 'first_name': 'Ali', 'last_name': 'Valiyev', 'role': 'student', **extra}


class RegisterEmailTests(EmailCase):
    def test_code_is_mailed_and_the_token_registers_a_verified_account(self):
        token = self.verified_token()
        self.assertEqual(mail.outbox[-1].to, [EMAIL])
        resp = self.post('register', self.register_payload(email=EMAIL, email_token=token))
        self.assertEqual(resp.status_code, 201, resp.content)
        user = User.objects.get(username='ali01')
        self.assertEqual((user.email, user.email_verified), (EMAIL, True))

    def test_email_is_lowercased_and_trimmed(self):
        token = self.verified_token(' Ali@Example.COM ')
        resp = self.post('register', self.register_payload(email='ALI@example.com', email_token=token))
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(User.objects.get(username='ali01').email, EMAIL)

    def test_token_works_once_and_only_for_its_own_email(self):
        token = self.verified_token()
        wrong = self.post('register', self.register_payload(email='other@example.com', email_token=token))
        self.assertEqual(wrong.status_code, 400)
        self.assertIn('email_token', details(wrong))
        self.assertEqual(self.post('register', self.register_payload(email=EMAIL, email_token=token)).status_code, 201)
        again = self.post('register', self.register_payload(username='ali02', email=EMAIL, email_token=token))
        self.assertEqual(again.status_code, 400)

    def test_wrong_code_is_rejected_and_five_misses_burn_the_code(self):
        self.post('register/email/request', {'email': EMAIL})
        real = mailed_code()
        for _ in range(5):
            self.assertEqual(self.post('register/email/verify', {'email': EMAIL, 'code': '00000' if real != '00000' else '11111'}).status_code, 400)
        self.assertEqual(self.post('register/email/verify', {'email': EMAIL, 'code': real}).status_code, 400)

    def test_invalid_email_is_rejected_before_anything_is_sent(self):
        resp = self.post('register/email/request', {'email': 'not-an-email'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(mail.outbox, [])

    def test_a_second_request_waits_for_the_cooldown(self):
        self.post('register/email/request', {'email': EMAIL})
        self.assertEqual(self.post('register/email/request', {'email': EMAIL}).status_code, 429)

    @override_settings(REGISTER_REQUIRES_EMAIL=False)
    def test_without_the_flag_registration_works_as_before(self):
        self.assertEqual(self.post('register', self.register_payload()).status_code, 201)

    @override_settings(REGISTER_REQUIRES_EMAIL=True)
    def test_with_the_flag_a_verified_email_is_mandatory(self):
        resp = self.post('register', self.register_payload())
        self.assertEqual(resp.status_code, 400)
        self.assertIn('email_token', details(resp))
        self.assertFalse(User.objects.exists())
        token = self.verified_token()
        self.assertEqual(self.post('register', self.register_payload(email=EMAIL, email_token=token)).status_code, 201)

    @override_settings(REGISTER_REQUIRES_EMAIL=True)
    def test_token_without_email_in_the_body_is_rejected(self):
        token = self.verified_token()
        resp = self.post('register', self.register_payload(email_token=token))
        self.assertEqual(resp.status_code, 400)

    def test_the_options_endpoint_tells_the_client_what_to_show(self):
        resp = self.client.get('/api/v1/auth/register/options/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.json()), {'email_required', 'email_available', 'phone_available'})
        with override_settings(REGISTER_REQUIRES_EMAIL=True):
            self.assertTrue(self.client.get('/api/v1/auth/register/options/').json()['email_required'])

    def test_new_logins_cannot_contain_an_at_sign(self):
        resp = self.post('register', self.register_payload(username='ali@home'))
        self.assertEqual(resp.status_code, 400)
        self.assertIn('username', details(resp))

    def test_a_child_created_by_a_parent_is_exempt_from_email(self):
        parent = make('p1', User.Role.PARENT)
        child = create_child(creator=parent, username='kid01', password=PASSWORD)
        self.assertTrue(child.email_exempt)


class EmailLoginTests(EmailCase):
    def login(self, identifier, password=PASSWORD):
        return self.post('login', {'username': identifier, 'password': password})

    def test_a_verified_email_logs_in_like_the_username(self):
        make('ali01', email=EMAIL, email_verified=True)
        resp = self.login(EMAIL)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn('access', resp.json())

    def test_email_login_is_case_insensitive(self):
        make('ali01', email=EMAIL, email_verified=True)
        self.assertEqual(self.login('ALI@Example.com').status_code, 200)

    def test_username_login_is_unchanged(self):
        make('ali01', email=EMAIL, email_verified=True)
        self.assertEqual(self.login('ali01').status_code, 200)

    def test_an_unverified_email_does_not_log_in(self):
        make('ali01', email=EMAIL, email_verified=False)
        self.assertEqual(self.login(EMAIL).status_code, 401)

    def test_a_wrong_password_looks_like_any_failed_login(self):
        make('ali01', email=EMAIL, email_verified=True)
        unknown = self.login('nobody@example.com')
        wrong = self.login(EMAIL, 'WrongPass999!')
        self.assertEqual((unknown.status_code, wrong.status_code), (401, 401))
        self.assertEqual(unknown.json(), wrong.json())

    def test_a_login_that_contains_an_at_sign_still_works_as_a_username(self):
        make('legacy@home')
        self.assertEqual(self.login('legacy@home').status_code, 200)

    def test_a_username_wins_over_an_email_with_the_same_text(self):
        make('shared@example.com')  # eski login, email ko'rinishida
        make('other', email='shared@example.com', email_verified=True)
        resp = self.login('shared@example.com')
        self.assertEqual(resp.status_code, 200)
        user = User.objects.get(pk=__import__('jwt').decode(resp.json()['access'], options={'verify_signature': False})['user_id'])
        self.assertEqual(user.username, 'shared@example.com')

    def test_several_accounts_on_one_email_pick_the_one_that_matches_the_password(self):
        a = make('ali.student', email=EMAIL, email_verified=True)
        b = make('ali.teacher', User.Role.TEACHER, email=EMAIL, email_verified=True)
        b.set_password('AnotherPass789!')
        b.save()
        self.assertEqual(self.login(EMAIL).status_code, 200)
        self.assertEqual(self.login(EMAIL, 'AnotherPass789!').status_code, 200)
        self.assertIsNotNone(a.pk)

    def test_same_password_on_several_accounts_asks_for_the_login(self):
        make('ali.student', email=EMAIL, email_verified=True)
        make('ali.teacher', User.Role.TEACHER, email=EMAIL, email_verified=True)
        resp = self.login(EMAIL)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('login', str(resp.json()).lower())

    def test_a_deactivated_account_does_not_log_in_by_email(self):
        make('ali01', email=EMAIL, email_verified=True, is_active=False)
        self.assertEqual(self.login(EMAIL).status_code, 401)

    def test_failed_email_logins_count_towards_the_login_guard(self):
        make('ali01', email=EMAIL, email_verified=True)
        codes = [self.login(EMAIL, 'WrongPass999!').status_code for _ in range(12)]
        self.assertIn(429, codes)


class EmailResetTests(EmailCase):
    def start(self, email=EMAIL):
        return self.post('password/reset/request', {'email': email})

    def token(self, email=EMAIL):
        self.assertEqual(self.start(email).status_code, 200)
        resp = self.post('password/reset/verify', {'email': email, 'code': mailed_code()})
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()['reset_token']

    def test_full_flow_resets_the_password_and_the_new_one_logs_in(self):
        user = make('ali01', email=EMAIL, email_verified=True)
        token = self.token()
        self.assertEqual(mail.outbox[-1].to, [EMAIL])
        resp = self.post('password/reset/confirm', {'reset_token': token, 'password': NEW_PASSWORD})
        self.assertEqual((resp.status_code, resp.json()), (200, {'ok': True}))
        user.refresh_from_db()
        self.assertTrue(user.check_password(NEW_PASSWORD))
        self.assertEqual(self.post('login', {'username': 'ali01', 'password': NEW_PASSWORD}).status_code, 200)
        self.assertEqual(self.post('login', {'username': 'ali01', 'password': PASSWORD}).status_code, 401)

    def test_all_sessions_are_closed_after_the_reset(self):
        user = make('ali01', email=EMAIL, email_verified=True)
        self.post('login', {'username': 'ali01', 'password': PASSWORD})
        self.assertTrue(UserSession.objects.filter(user=user, revoked_at__isnull=True).exists())
        self.post('password/reset/confirm', {'reset_token': self.token(), 'password': NEW_PASSWORD})
        self.assertFalse(UserSession.objects.filter(user=user, revoked_at__isnull=True).exists())

    def test_an_unknown_email_gets_the_same_answer_and_no_mail(self):
        make('ali01', email=EMAIL, email_verified=True)
        known = self.start()
        cache.clear()
        mail.outbox.clear()
        unknown = self.start('nobody@example.com')
        self.assertEqual((unknown.status_code, set(unknown.json())), (known.status_code, set(known.json())))
        self.assertEqual(mail.outbox, [])

    def test_an_unknown_email_cannot_get_a_reset_token_with_a_guessed_code(self):
        self.start('nobody@example.com')
        resp = self.post('password/reset/verify', {'email': 'nobody@example.com', 'code': '12345'})
        self.assertEqual(resp.status_code, 400)

    def test_an_unknown_email_is_throttled_like_a_known_one(self):
        self.start('nobody@example.com')
        self.assertEqual(self.start('nobody@example.com').status_code, 429)

    def test_an_unverified_email_receives_nothing(self):
        make('ali01', email=EMAIL, email_verified=False)
        self.assertEqual(self.start().status_code, 200)
        self.assertEqual(mail.outbox, [])

    def test_a_wrong_code_gives_no_token(self):
        make('ali01', email=EMAIL, email_verified=True)
        self.start()
        resp = self.post('password/reset/verify', {'email': EMAIL, 'code': '00000' if mailed_code() != '00000' else '11111'})
        self.assertEqual(resp.status_code, 400)

    def test_every_account_on_the_verified_email_is_reset(self):
        a = make('ali.student', email=EMAIL, email_verified=True)
        b = make('ali.teacher', User.Role.TEACHER, email=EMAIL, email_verified=True)
        other = make('boshqa', email='boshqa@example.com', email_verified=True)
        self.post('password/reset/confirm', {'reset_token': self.token(), 'password': NEW_PASSWORD})
        for user in (a, b):
            user.refresh_from_db()
            self.assertTrue(user.check_password(NEW_PASSWORD))
        other.refresh_from_db()
        self.assertTrue(other.check_password(PASSWORD))

    def test_a_weak_password_is_refused_and_the_token_stays_usable(self):
        make('ali01', email=EMAIL, email_verified=True)
        token = self.token()
        self.assertEqual(self.post('password/reset/confirm', {'reset_token': token, 'password': '123'}).status_code, 400)
        self.assertEqual(self.post('password/reset/confirm', {'reset_token': token, 'password': NEW_PASSWORD}).status_code, 200)

    def test_the_token_is_single_use(self):
        make('ali01', email=EMAIL, email_verified=True)
        token = self.token()
        self.post('password/reset/confirm', {'reset_token': token, 'password': NEW_PASSWORD})
        self.assertEqual(self.post('password/reset/confirm', {'reset_token': token, 'password': 'Third456!!pass'}).status_code, 400)

    def test_phone_or_email_is_required(self):
        self.assertEqual(self.post('password/reset/request', {}).status_code, 400)

    @override_settings(EMAIL_HOST='', EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_without_a_mail_service_the_answer_is_503_for_everyone(self):
        make('ali01', email=EMAIL, email_verified=True)
        self.assertEqual(self.start().status_code, 503)
        self.assertEqual(self.start('nobody@example.com').status_code, 503)

    @override_settings(SMS_BACKEND='console')
    def test_the_phone_flow_still_works(self):
        from apps.core import sms

        sms.sent.clear()
        make('ali01', phone='+998901234567')
        self.assertEqual(self.post('password/reset/request', {'phone': '+998901234567'}).status_code, 200)
        code = re.search(r'\b(\d{5})\b', sms.sent[-1][1]).group(1)
        token = self.post('password/reset/verify', {'phone': '+998901234567', 'code': code}).json()['reset_token']
        self.assertEqual(self.post('password/reset/confirm', {'reset_token': token, 'password': NEW_PASSWORD}).status_code, 200)

    @override_settings(SMS_BACKEND='console')
    def test_an_unknown_phone_is_still_a_404(self):
        self.assertEqual(self.post('password/reset/request', {'phone': '+998909999999'}).status_code, 404)


class ProfileEmailTests(EmailCase):
    def setUp(self):
        super().setUp()
        self.user = make('ali01')
        self.client.force_authenticate(self.user)

    def test_adding_an_email_needs_the_code_sent_to_the_new_address(self):
        self.assertEqual(self.post('me/email/request', {'email': EMAIL}).status_code, 200)
        self.assertEqual(mail.outbox[-1].to, [EMAIL])
        self.user.refresh_from_db()
        self.assertEqual((self.user.email, self.user.email_verified), ('', False))  # kod tasdiqlanguncha o'zgarmaydi
        resp = self.post('me/email/confirm', {'email': EMAIL, 'code': mailed_code()})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.json()['email'], resp.json()['email_verified']), (EMAIL, True))
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_a_code_sent_to_one_address_does_not_confirm_another(self):
        self.post('me/email/request', {'email': EMAIL})
        resp = self.post('me/email/confirm', {'email': 'other@example.com', 'code': mailed_code()})
        self.assertEqual(resp.status_code, 400)

    def test_another_users_code_does_not_work(self):
        self.post('me/email/request', {'email': EMAIL})
        code = mailed_code()
        mallory = make('mallory')
        client = APIClient()
        client.force_authenticate(mallory)
        self.assertEqual(self.post('me/email/confirm', {'email': EMAIL, 'code': code}, client=client).status_code, 400)

    def test_changing_the_email_through_the_profile_drops_the_verification(self):
        self.user.email, self.user.email_verified = EMAIL, True
        self.user.save()
        resp = self.client.patch('/api/v1/auth/me/', {'email': 'new@example.com'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_authentication_is_required(self):
        self.assertEqual(self.post('me/email/request', {'email': EMAIL}, client=APIClient()).status_code, 401)


class EmailSetupHintTests(EmailCase):
    def me(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client.get('/api/v1/auth/me/').json()

    def test_nothing_is_asked_while_the_requirement_is_off(self):
        data = self.me(make('ali01'))
        self.assertEqual((data['email_setup_required'], data['email_setup_deadline']), (False, None))

    @override_settings(REGISTER_REQUIRES_EMAIL=True, EMAIL_SETUP_DEADLINE='2026-12-02')
    def test_a_user_without_a_verified_email_is_asked_with_the_deadline(self):
        data = self.me(make('ali01'))
        self.assertEqual((data['email_setup_required'], data['email_setup_deadline']), (True, '2026-12-02'))

    @override_settings(REGISTER_REQUIRES_EMAIL=True, EMAIL_SETUP_DEADLINE='2026-12-02')
    def test_a_verified_user_is_not_asked(self):
        data = self.me(make('ali01', email=EMAIL, email_verified=True))
        self.assertEqual((data['email_setup_required'], data['email_setup_deadline']), (False, None))

    @override_settings(REGISTER_REQUIRES_EMAIL=True, EMAIL_SETUP_DEADLINE='2026-12-02')
    def test_children_created_by_adults_are_never_asked(self):
        child = make('kid01', email_exempt=True)
        self.assertEqual(self.me(child)['email_setup_required'], False)

    @override_settings(REGISTER_REQUIRES_EMAIL=True, EMAIL_SETUP_DEADLINE='')
    def test_no_deadline_means_a_reminder_only(self):
        data = self.me(make('ali01'))
        self.assertEqual((data['email_setup_required'], data['email_setup_deadline']), (True, None))


class TranslationTests(EmailCase):
    """Yangi xabarlar ru/en tilida ham chiqadi (oldin faqat o'zbekcha edi)."""

    def post_lang(self, lang, path, data):
        return self.client.post(f'/api/v1/auth/{path}/', data, format='json', HTTP_ACCEPT_LANGUAGE=lang)

    def test_the_email_token_error_is_translated(self):
        for lang, expected in (('ru', 'Токен подтверждения email'), ('en', 'email verification token')):
            resp = self.post_lang(lang, 'register', {
                'username': f'tr_{lang}', 'password': PASSWORD, 'role': 'student', 'email': EMAIL, 'email_token': 'bad'})
            self.assertEqual(resp.status_code, 400)
            self.assertIn(expected, resp.json()['error']['message'])

    def test_the_invalid_email_message_is_translated(self):
        ru = self.post_lang('ru', 'register/email/request', {'email': 'nope'})
        en = self.post_lang('en', 'register/email/request', {'email': 'nope'})
        self.assertIn('корректный адрес', ru.json()['error']['message'])
        self.assertIn('valid email address', en.json()['error']['message'])

    def test_the_at_sign_rule_is_translated(self):
        ru = self.post_lang('ru', 'register', {'username': 'a@b', 'password': PASSWORD, 'role': 'student'})
        self.assertIn('«@»', str(details(ru)['username']))

    def test_the_wrong_code_message_is_translated(self):
        resp = self.post_lang('ru', 'register/email/verify', {'email': EMAIL, 'code': '00000'})
        self.assertIn('Код неверен', resp.json()['error']['message'])

    def test_uzbek_stays_the_default(self):
        resp = self.post('register/email/request', {'email': 'nope'})
        self.assertIn("To'g'ri email manzil kiriting", resp.json()['error']['message'])


class SideChannelTests(EmailCase):
    """Email bor-yo'qligi javob vaqtidan ham bilinmasin: parol hisoblash soni va xat yuborish usuli bir xil."""

    def hash_operations(self, identifier, password):
        from unittest import mock

        with mock.patch.object(User, 'set_password', autospec=True, side_effect=User.set_password) as dummy, \
                mock.patch.object(User, 'check_password', autospec=True, side_effect=User.check_password) as check:
            self.post('login', {'username': identifier, 'password': password})
        return dummy.call_count + check.call_count

    def test_login_does_the_same_number_of_hash_operations_for_known_and_unknown_emails(self):
        make('ali01', email=EMAIL, email_verified=True)
        known_wrong = self.hash_operations(EMAIL, 'WrongPass999!')
        known_right = self.hash_operations(EMAIL, PASSWORD)
        unknown = self.hash_operations('nobody@example.com', PASSWORD)
        unverified = self.hash_operations(EMAIL.replace('ali', 'x'), PASSWORD)
        self.assertEqual({known_wrong, known_right, unknown, unverified}, {2})

    def test_a_plain_unknown_login_is_unchanged(self):
        self.assertEqual(self.hash_operations('nobody', PASSWORD), 1)

    def test_the_reset_mail_goes_through_the_background_only_for_known_emails(self):
        from unittest import mock

        make('ali01', email=EMAIL, email_verified=True)
        with mock.patch('apps.accounts.otp.background.run') as run:
            self.post('password/reset/request', {'email': EMAIL})
            self.assertEqual(run.call_count, 1)
            cache.clear()
            self.post('password/reset/request', {'email': 'nobody@example.com'})
            self.assertEqual(run.call_count, 1)  # noma'lum email: xat ham, fon vazifasi ham yo'q

    def test_a_failing_mail_does_not_change_the_answer(self):
        from unittest import mock

        make('ali01', email=EMAIL, email_verified=True)
        with mock.patch('apps.core.mailer.send_email', side_effect=RuntimeError('smtp down')):
            resp = self.post('password/reset/request', {'email': EMAIL})
        self.assertEqual((resp.status_code, resp.json()['sent']), (200, True))


class LoginGuardSharedTests(EmailCase):
    """Login va email bilan urinishlar bitta hisoblagichga yig'iladi (10 ta xato — 429), shunda email "ikkinchi imkoniyat" bo'lib qolmaydi."""

    def test_username_and_email_failures_share_one_counter(self):
        make('ali01', email=EMAIL, email_verified=True)
        for _ in range(5):
            self.assertEqual(self.post('login', {'username': 'ali01', 'password': 'WrongPass999!'}).status_code, 401)
        for _ in range(5):
            self.assertEqual(self.post('login', {'username': EMAIL, 'password': 'WrongPass999!'}).status_code, 401)
        self.assertEqual(self.post('login', {'username': 'ali01', 'password': PASSWORD}).status_code, 429)
        self.assertEqual(self.post('login', {'username': EMAIL, 'password': PASSWORD}).status_code, 429)

    def test_case_variants_of_the_email_share_the_counter_too(self):
        make('ali01', email=EMAIL, email_verified=True)
        for variant in ('ali@example.com', 'ALI@example.com', 'Ali@Example.com', 'ali@example.com', 'ALI@EXAMPLE.COM') * 2:
            self.post('login', {'username': variant, 'password': 'WrongPass999!'})
        self.assertEqual(self.post('login', {'username': 'ali01', 'password': PASSWORD}).status_code, 429)

    def test_another_account_is_not_blocked(self):
        make('ali01', email=EMAIL, email_verified=True)
        make('vali01', email='vali@example.com', email_verified=True)
        for _ in range(10):
            self.post('login', {'username': EMAIL, 'password': 'WrongPass999!'})
        self.assertEqual(self.post('login', {'username': 'vali01', 'password': PASSWORD}).status_code, 200)

    def test_canonical_login_leaves_plain_and_ambiguous_identifiers_alone(self):
        from apps.accounts import services

        make('Ali01')
        make('legacy@home')
        make('a.student', email='shared@example.com', email_verified=True)
        make('a.teacher', User.Role.TEACHER, email='shared@example.com', email_verified=True)
        self.assertEqual(services.canonical_login('Ali01'), 'ali01')
        self.assertEqual(services.canonical_login('legacy@home'), 'legacy@home')
        self.assertEqual(services.canonical_login('shared@example.com'), 'shared@example.com')  # ikki akkaunt: aniq emas
        self.assertEqual(services.canonical_login('nobody@example.com'), 'nobody@example.com')
