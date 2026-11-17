from collections import namedtuple
from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import User
from apps.monitoring.management.commands import check_cpu_steal
from apps.notifications.models import NotificationRecipient

Times = namedtuple('Times', 'user nice system idle iowait irq softirq steal guest guest_nice')


def times(*, busy=0.0, idle=0.0, steal=0.0):
    return Times(user=busy, nice=0, system=0, idle=idle, iowait=0, irq=0, softirq=0, steal=steal, guest=0, guest_nice=0)


class MeasureTests(TestCase):
    def test_idle_server_has_no_steal(self):
        sample = check_cpu_steal.measure(times(), times(busy=1, idle=99))
        self.assertEqual((round(sample['st'], 2), round(sample['load'], 2), sample['demand_steal']), (0.0, 1.0, 0.0))

    def test_steal_is_reported_against_total_and_against_demand(self):
        sample = check_cpu_steal.measure(times(), times(busy=47, idle=50, steal=3))
        self.assertAlmostEqual(sample['st'], 3.0)            # top'dagi %st
        self.assertAlmostEqual(sample['load'], 50.0)          # band + steal
        self.assertAlmostEqual(sample['demand_steal'], 6.0)   # yuk tushganda CPU'ning 6% olib qo'yilgan

    def test_no_elapsed_time_or_no_steal_counter_gives_none(self):
        self.assertIsNone(check_cpu_steal.measure(times(), times()))
        self.assertIsNone(check_cpu_steal.measure(namedtuple('T', 'user nice system idle')(0, 0, 0, 0), times(idle=1)))


class CheckCpuStealTests(TestCase):
    def setUp(self):
        cache.clear()
        check_cpu_steal.reset_state()
        self.admin = User.objects.create_user(username='steal_admin', password='x', role=User.Role.ADMIN)
        self.counter = times()

    def tick(self, **delta):
        """Keyingi o'lchovni beradi (jami hisoblagich oshib boradi) va buyruqni ishga tushiradi."""
        c = self.counter
        self.counter = times(
            busy=c.user + delta.get('busy', 0), idle=c.idle + delta.get('idle', 0), steal=c.steal + delta.get('steal', 0),
        )
        with mock.patch('apps.monitoring.management.commands.check_cpu_steal.psutil.cpu_times', return_value=self.counter), \
                mock.patch('apps.monitoring.management.commands.check_cpu_steal.time.sleep'):
            call_command('check_cpu_steal', stdout=StringIO())

    def alerts(self):
        return NotificationRecipient.objects.filter(user=self.admin).count()

    def start(self):
        self.tick(idle=100)  # birinchi o'lchov: oldingi holat yo'q, `sleep` bilan o'lchanadi

    def test_sustained_steal_under_load_alerts_admin_once(self):
        self.start()
        for _ in range(12):
            self.tick(busy=70, idle=20, steal=10)  # yuk 80%, steal talabning 12.5%
        self.assertEqual(self.alerts(), 1)

    def test_short_spike_does_not_alert(self):
        self.start()
        for _ in range(3):
            self.tick(busy=70, idle=20, steal=10)
        for _ in range(12):
            self.tick(busy=70, idle=30)
        self.assertEqual(self.alerts(), 0)

    def test_steal_on_an_idle_server_is_ignored(self):
        self.start()
        for _ in range(12):
            self.tick(busy=1, idle=98, steal=1)  # yuk 2% < 10%: hukm chiqarilmaydi
        self.assertEqual(self.alerts(), 0)

    def test_steal_below_threshold_does_not_alert(self):
        self.start()
        for _ in range(12):
            self.tick(busy=78, idle=20, steal=2)  # talabning 2.5%
        self.assertEqual(self.alerts(), 0)

    def test_notification_has_a_title(self):
        from apps.notifications.serializers import KIND_TITLES

        self.assertEqual(KIND_TITLES['cpu_steal_alert'], 'CPU sekinlashishi')
