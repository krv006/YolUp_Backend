"""Login: (IP + login) bo'yicha muvaffaqiyatsiz urinishlar chegarasi va alohida 'login' throttle'i (maktab Wi-Fi'si)."""
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from apps.accounts import views
from apps.accounts.models import User

PASSWORD = 'StrongPass123!'
URL = '/api/v1/auth/login/'


def make(username):
    user = User(username=username, role=User.Role.STUDENT)
    user.set_password(PASSWORD)
    user.save()
    return user


class LoginGuardTests(APITestCase):
    def setUp(self):
        cache.clear()
        make('guard_user')
        make('other_user')

    def post(self, username, password, ip='10.0.0.1'):
        return APIClient().post(URL, {'username': username, 'password': password}, HTTP_X_FORWARDED_FOR=ip)

    def test_blocks_after_limit_of_failures_for_same_ip_and_login(self):
        for _ in range(views.LOGIN_FAIL_LIMIT):
            self.assertEqual(self.post('guard_user', 'wrong').status_code, 401)
        blocked = self.post('guard_user', PASSWORD)  # even the right password is refused while blocked
        self.assertEqual(blocked.status_code, 429)

    def test_other_login_from_same_ip_is_not_blocked(self):
        for _ in range(views.LOGIN_FAIL_LIMIT):
            self.post('guard_user', 'wrong')
        self.assertEqual(self.post('other_user', PASSWORD).status_code, 200)

    def test_same_login_from_other_ip_is_not_blocked(self):
        for _ in range(views.LOGIN_FAIL_LIMIT):
            self.post('guard_user', 'wrong', ip='10.0.0.1')
        self.assertEqual(self.post('guard_user', PASSWORD, ip='10.0.0.2').status_code, 200)

    def test_successful_login_resets_the_counter(self):
        for _ in range(views.LOGIN_FAIL_LIMIT - 1):
            self.post('guard_user', 'wrong')
        self.assertEqual(self.post('guard_user', PASSWORD).status_code, 200)
        for _ in range(views.LOGIN_FAIL_LIMIT - 1):
            self.assertEqual(self.post('guard_user', 'wrong').status_code, 401)
        self.assertEqual(self.post('guard_user', PASSWORD).status_code, 200)

    def test_login_has_its_own_high_throttle_and_otp_scope_stays_strict(self):
        rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        self.assertEqual(rates['login'], '300/min')
        self.assertEqual(rates['auth'], '30/min')  # register / OTP / SMS stay strict (SMS costs money)
        self.assertEqual(views.LoginView.throttle_scope, 'login')


class LoginThrottleNotSharedWithAnonTests(APITestCase):
    """Bitta IP ostidagi ko'p o'quvchi (maktab Wi-Fi'si): umumiy anon chegarasi (60/min) login va yangilashni to'smasin."""

    def setUp(self):
        cache.clear()

    def test_login_and_refresh_use_only_the_login_scope(self):
        from rest_framework.throttling import ScopedRateThrottle
        for view in (views.LoginView, views.RefreshView, views.TwoFactorLoginView, views.SocialLoginView):
            self.assertEqual(view.throttle_scope, 'login', view)
            self.assertEqual(view.throttle_classes, [ScopedRateThrottle], view)

    def test_70_logins_from_one_ip_are_not_throttled(self):
        statuses = {
            APIClient().post(URL, {'username': f'nobody{i}', 'password': 'x'}, HTTP_X_FORWARDED_FOR='10.9.9.9').status_code
            for i in range(70)
        }
        self.assertEqual(statuses, {401})  # wrong credentials, never 429 (the anon limit is 60/min)

    def test_70_refreshes_from_one_ip_are_not_throttled(self):
        statuses = {
            APIClient().post('/api/v1/auth/token/refresh/', {'refresh': 'garbage'}, HTTP_X_FORWARDED_FOR='10.9.9.8').status_code
            for i in range(70)
        }
        self.assertEqual(statuses, {401})  # garbage refresh token: 401, never 429
