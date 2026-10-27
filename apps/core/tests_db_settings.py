"""Prod baza sozlamasi: ulanishlar puli (ASGI) va doimiy ulanish (WSGI/cron)."""
from django.test import SimpleTestCase

from root.settings.db import build_database

BASE = {'POSTGRES_DB': 'edtech', 'POSTGRES_USER': 'u', 'POSTGRES_PASSWORD': 'p', 'POSTGRES_HOST': 'db'}


class BuildDatabaseTests(SimpleTestCase):
    def test_default_is_a_persistent_connection(self):
        config = build_database(BASE)
        self.assertEqual((config['CONN_MAX_AGE'], config['HOST'], config['PORT'], config['NAME']), (60, 'db', '5432', 'edtech'))
        self.assertNotIn('OPTIONS', config)

    def test_pool_disables_persistent_connections(self):
        config = build_database({**BASE, 'DB_POOL_MAX': '20'})
        self.assertEqual(config['CONN_MAX_AGE'], 0)  # Django: pul bilan CONN_MAX_AGE faqat 0 bo'lishi mumkin
        self.assertEqual(config['OPTIONS']['pool'], {'min_size': 2, 'max_size': 20, 'timeout': 20})

    def test_blank_or_zero_values_mean_no_pool(self):
        for value in ('', '0', None):
            self.assertNotIn('OPTIONS', build_database({**BASE, 'DB_POOL_MAX': value} if value is not None else BASE))
        self.assertEqual(build_database({**BASE, 'DB_CONN_MAX_AGE': '120'})['CONN_MAX_AGE'], 120)

    def test_tiny_pool_keeps_min_below_max(self):
        self.assertEqual(build_database({**BASE, 'DB_POOL_MAX': '1'})['OPTIONS']['pool']['min_size'], 1)

    def test_psycopg_pool_is_installed(self):
        import psycopg_pool  # noqa: F401  (requirements.txt: psycopg[binary,pool])
