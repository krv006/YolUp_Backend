from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.tests import PASSWORD, login

from . import services
from .models import ResourceSample


def make_admin(username='mon_admin') -> User:
    return User.objects.create_user(username=username, password=PASSWORD, role=User.Role.ADMIN)


def _mock_memory(percent, used_mb, total_mb):
    mem = MagicMock()
    mem.percent = percent
    mem.used = used_mb * 1024 * 1024
    mem.total = total_mb * 1024 * 1024
    return mem


class RecordSampleServiceTests(APITestCase):
    @patch('apps.monitoring.services.psutil')
    def test_record_sample_stores_cpu_and_memory(self, mock_psutil):
        mock_psutil.cpu_percent.return_value = 42.5
        mock_psutil.virtual_memory.return_value = _mock_memory(60.0, 2048, 4096)

        sample = services.record_sample()
        self.assertEqual(sample.cpu_percent, 42.5)
        self.assertEqual(sample.memory_percent, 60.0)
        self.assertEqual(sample.memory_used_mb, 2048)
        self.assertEqual(sample.memory_total_mb, 4096)

    @patch('apps.monitoring.services.psutil')
    def test_record_sample_prunes_old_rows(self, mock_psutil):
        mock_psutil.cpu_percent.return_value = 10.0
        mock_psutil.virtual_memory.return_value = _mock_memory(10.0, 100, 1000)

        old = ResourceSample.objects.create(
            cpu_percent=1, memory_percent=1, memory_used_mb=1, memory_total_mb=1000,
        )
        ResourceSample.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=91),
        )
        services.record_sample()
        self.assertFalse(ResourceSample.objects.filter(pk=old.pk).exists())


class MonitoringViewTests(APITestCase):
    def setUp(self):
        make_admin()
        self.admin_token = login(self.client, 'mon_admin')

        register_teacher_resp = self.client.post('/api/v1/auth/register/', {
            'username': 'mon_teacher', 'password': PASSWORD, 'role': 'teacher',
        })
        self.assertEqual(register_teacher_resp.status_code, 201)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_non_admin_forbidden(self):
        self.auth(login(self.client, 'mon_teacher'))
        self.assertEqual(self.client.get('/api/v1/monitoring/current/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/monitoring/history/').status_code, 403)

    def test_current_returns_none_when_no_samples_yet(self):
        self.auth(self.admin_token)
        resp = self.client.get('/api/v1/monitoring/current/')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json())

    def test_current_returns_latest_sample(self):
        ResourceSample.objects.create(cpu_percent=10, memory_percent=20, memory_used_mb=100, memory_total_mb=1000)
        ResourceSample.objects.create(cpu_percent=99, memory_percent=88, memory_used_mb=900, memory_total_mb=1000)

        self.auth(self.admin_token)
        resp = self.client.get('/api/v1/monitoring/current/')
        self.assertEqual(resp.json()['cpu_percent'], 99)

    def test_history_reports_peak_within_window(self):
        now = timezone.now()
        low = ResourceSample.objects.create(
            cpu_percent=20, memory_percent=20, memory_used_mb=100, memory_total_mb=1000,
        )
        ResourceSample.objects.filter(pk=low.pk).update(created_at=now - timedelta(hours=2))

        peak = ResourceSample.objects.create(
            cpu_percent=95, memory_percent=90, memory_used_mb=900, memory_total_mb=1000,
        )
        ResourceSample.objects.filter(pk=peak.pk).update(created_at=now - timedelta(hours=1))

        # Oyna tashqarisidagi eski namuna — peak sifatida hisobga olinmasligi kerak.
        outside = ResourceSample.objects.create(
            cpu_percent=100, memory_percent=100, memory_used_mb=1000, memory_total_mb=1000,
        )
        ResourceSample.objects.filter(pk=outside.pk).update(created_at=now - timedelta(hours=30))

        self.auth(self.admin_token)
        resp = self.client.get('/api/v1/monitoring/history/?hours=24')
        data = resp.json()
        self.assertEqual(len(data['samples']), 2)
        self.assertEqual(data['peak']['cpu_percent'], 95)

    def test_history_hours_param_is_clamped(self):
        self.auth(self.admin_token)
        resp = self.client.get('/api/v1/monitoring/history/?hours=999999')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['hours'], 24 * 30)
