"""Xavfsizlik sozlamalari (2026-10-29 audit): API hujjati, CORS, prodda dev standart sirlarini rad etish."""
import os
import re
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings

from apps.accounts.models import User

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GOOD_ENV = {
    'DJANGO_ENV': 'prod', 'SECRET_KEY': 'x' * 50, 'POSTGRES_DB': 'edtech', 'POSTGRES_PASSWORD': 'x',
    'LIVEKIT_API_KEY': 'fokus_prod', 'LIVEKIT_API_SECRET': 'y' * 40, 'VAPID_PRIVATE_KEY': 'private',
}


class ApiDocsAccessTests(TestCase):
    URLS = ('/api/docs/', '/api/schema/')

    @override_settings(API_DOCS_PUBLIC=True)
    def test_public_when_enabled(self):
        for url in self.URLS:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    @override_settings(API_DOCS_PUBLIC=False)
    def test_closed_for_anonymous_and_regular_users_when_disabled(self):
        for url in self.URLS:
            self.assertEqual(self.client.get(url).status_code, 403, url)
        user = User.objects.create_user(username='docs_u', password='x', role=User.Role.TEACHER)
        self.client.force_login(user)
        for url in self.URLS:
            self.assertEqual(self.client.get(url).status_code, 403, url)

    @override_settings(API_DOCS_PUBLIC=False)
    def test_open_for_staff_after_login(self):
        staff = User.objects.create_user(username='docs_s', password='x', role=User.Role.ADMIN, is_staff=True)
        self.client.force_login(staff)
        for url in self.URLS:
            self.assertEqual(self.client.get(url).status_code, 200, url)


class CorsOriginTests(SimpleTestCase):
    def allowed(self, origin):
        return origin in settings.CORS_ALLOWED_ORIGINS or any(re.match(rx, origin) for rx in settings.CORS_ALLOWED_ORIGIN_REGEXES)

    def test_this_projects_vercel_deployments_are_allowed(self):
        for origin in ('https://edu-front-silk.vercel.app', 'https://edu-front-git-feature-team.vercel.app'):
            self.assertTrue(self.allowed(origin), origin)

    def test_other_vercel_apps_and_lookalikes_are_not(self):
        for origin in ('https://evil.vercel.app', 'https://not-edu-front.vercel.app', 'https://edu-front.vercel.app.evil.com',
                       'http://edu-front-x.vercel.app'):
            self.assertFalse(self.allowed(origin), origin)


class ProdRefusesDevDefaultsTests(SimpleTestCase):
    """`root.settings.prod` import qilinganda dev standart sirlari bilan ishga tushmasligi kerak (alohida jarayonda)."""

    def load(self, **overrides):
        env = {**os.environ, **GOOD_ENV, **overrides}
        return subprocess.run(
            [sys.executable, '-c', 'import root.settings.prod'], cwd=BASE_DIR, env=env, capture_output=True, text=True, timeout=120,
        )

    def test_a_complete_environment_loads(self):
        result = self.load()
        self.assertEqual(result.returncode, 0, result.stderr[-500:])

    def test_dev_livekit_credentials_are_refused(self):
        for overrides in ({'LIVEKIT_API_SECRET': 'devsecret_change_me_32chars_min!'}, {'LIVEKIT_API_KEY': 'devkey'},
                          {'LIVEKIT_API_SECRET': ''}, {'LIVEKIT_API_KEY': ''}):
            result = self.load(**overrides)
            self.assertNotEqual(result.returncode, 0, overrides)
            self.assertIn('LIVEKIT', result.stderr, overrides)

    def test_the_public_default_vapid_key_is_refused_except_on_the_media_server(self):
        result = self.load(VAPID_PRIVATE_KEY='')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('VAPID', result.stderr)
        self.assertEqual(self.load(VAPID_PRIVATE_KEY='', SERVER_ROLE='media').returncode, 0)

    def test_api_docs_are_closed_by_default_in_prod(self):
        script = 'import root.settings.prod as s; print(s.API_DOCS_PUBLIC)'
        env = {**os.environ, **GOOD_ENV}
        env.pop('API_DOCS_PUBLIC', None)
        out = subprocess.run([sys.executable, '-c', script], cwd=BASE_DIR, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip().splitlines()[-1], 'False', out.stderr[-300:])
        env['API_DOCS_PUBLIC'] = '1'
        out = subprocess.run([sys.executable, '-c', script], cwd=BASE_DIR, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.stdout.strip().splitlines()[-1], 'True')
