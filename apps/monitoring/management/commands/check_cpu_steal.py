"""Serverning "dedicated" yadrolari haqiqatan to'liq bizniki ekanini kuzatadi (CPU steal time).

    python manage.py check_cpu_steal [--threshold 3] [--min-load 10] [--window 10] [--bad 8]

Steal — virtual mashina CPU kerak bo'lganda ham uni olmagan vaqt (hypervisor boshqa mijozga bergan). netcup: har yadroda steal
doimiy 3% dan oshsa murojaat qilish kerak. Scheduler har daqiqada chaqiradi; oldingi o'lchov jarayon xotirasida turadi.

Ikki ko'rsatkich: `st` — `top` dagi %st (steal / umumiy vaqt) va `demand` — steal / (band + steal): serverga yuk tushganda
CPU'ning qancha qismi olib qo'yilgani (bo'sh serverda `st` har doim ~0 bo'ladi, shuning uchun hukm `demand` bo'yicha).
Hukm faqat yuk `--min-load` % dan yuqori bo'lgan o'lchovlarda chiqariladi. Oxirgi `--window` ta o'lchovdan `--bad` tasi
chegaradan oshsa — barcha adminlarga bildirishnoma (6 soatda bir marta). Har soatda log'ga qisqa xulosa yoziladi.
"""
import logging
import threading
import time
from collections import deque
from html import escape

import psutil
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.accounts.models import User

logger = logging.getLogger('apps')
REPEAT_SECONDS = 6 * 3600
SUMMARY_SECONDS = 3600
_lock = threading.Lock()
_state = {'prev': None, 'recent': deque(), 'summary': [], 'summary_started': None}


def _busy(times) -> float:
    return times.user + times.nice + times.system + times.irq + times.softirq


def _total(times) -> float:
    return _busy(times) + times.idle + times.iowait + times.steal


def measure(prev, cur) -> dict | None:
    """Ikki `psutil.cpu_times()` o'rtasidagi steal ulushlari (%). Steal ma'lum bo'lmasa (Linux emas) yoki vaqt o'tmagan bo'lsa None."""
    if not hasattr(cur, 'steal') or not hasattr(prev, 'steal'):
        return None
    total = _total(cur) - _total(prev)
    if total <= 0:
        return None
    steal = cur.steal - prev.steal
    busy = _busy(cur) - _busy(prev)
    demand = busy + steal
    return {
        'st': max(steal, 0.0) / total * 100,
        'load': demand / total * 100,
        'demand_steal': (max(steal, 0.0) / demand * 100) if demand > 0 else 0.0,
    }


def reset_state() -> None:
    with _lock:
        _state.update(prev=None, recent=deque(), summary=[], summary_started=None)


class Command(BaseCommand):
    help = "CPU steal time'ni kuzatadi; yuk ostida doimiy chegaradan oshsa adminlarga bildirishnoma yuboradi."

    def add_arguments(self, parser):
        parser.add_argument('--threshold', type=float, default=3.0, help='Steal chegarasi, % (standart 3 — netcup tavsiyasi)')
        parser.add_argument('--min-load', type=float, default=10.0, help="Hukm chiqarish uchun eng kam yuk, % (standart 10)")
        parser.add_argument('--window', type=int, default=10, help="Nechta oxirgi o'lchovga qaraladi (standart 10)")
        parser.add_argument('--bad', type=int, default=8, help="Shundan nechtasi chegaradan oshsa ogohlantiriladi (standart 8)")

    def handle(self, *args, **options):
        with _lock:
            prev = _state['prev']
        if prev is None:  # birinchi chaqiruv: qisqa oraliq bilan o'lchaymiz
            prev = psutil.cpu_times()
            time.sleep(1)
        cur = psutil.cpu_times()
        sample = measure(prev, cur)
        with _lock:
            _state['prev'] = cur
        if sample is None:
            self.stdout.write("CPU steal o'lchab bo'lmadi")
            return
        self.stdout.write(
            f"CPU yuk {sample['load']:.1f}% · steal(st) {sample['st']:.2f}% · steal(talab bo'yicha) {sample['demand_steal']:.2f}%"
        )
        role = settings.SERVER_ROLE or 'server'
        threshold, min_load = options['threshold'], options['min_load']
        loaded = sample['load'] >= min_load
        bad = loaded and sample['demand_steal'] >= threshold
        with _lock:
            recent = _state['recent']
            recent.append(bad)
            while len(recent) > options['window']:
                recent.popleft()
            bad_count = sum(recent)
            _state['summary'].append(sample | {'loaded': loaded})
            now = time.monotonic()
            if _state['summary_started'] is None:
                _state['summary_started'] = now
            summary = None
            if now - _state['summary_started'] >= SUMMARY_SECONDS:
                summary, _state['summary'], _state['summary_started'] = _state['summary'], [], now
        if summary:
            under_load = [item['demand_steal'] for item in summary if item['loaded']]
            logger.info(
                'cpu_steal %s: 1 soat, %d o\'lchov, st o\'rtacha %.3f%% / eng ko\'pi %.2f%%, yuk ostida talab bo\'yicha o\'rtacha %.2f%% / eng ko\'pi %.2f%% (%d o\'lchov)',
                role, len(summary), sum(i['st'] for i in summary) / len(summary), max(i['st'] for i in summary),
                (sum(under_load) / len(under_load)) if under_load else 0.0, max(under_load, default=0.0), len(under_load),
            )
        if sample['st'] >= 1.0:
            logger.warning('cpu_steal %s: st %.2f%%, talab bo\'yicha %.2f%%, yuk %.1f%%', role, sample['st'], sample['demand_steal'], sample['load'])
        if bad_count < options['bad']:
            return
        logger.warning('cpu_steal ogohlantirish %s: oxirgi %d o\'lchovdan %d tasida steal >= %s%%', role, len(recent), bad_count, threshold)
        if not cache.add(f'cpu-steal-alert:{role}', 1, REPEAT_SECONDS):
            return  # yaqinda yuborilgan
        admins = list(User.objects.filter(role=User.Role.ADMIN, is_active=True))
        if not admins:
            return
        from apps.notifications.services import send_notification

        text = escape(
            f"{role} serverida CPU steal doimiy {threshold:g}% dan yuqori (oxirgi o'lchovda {sample['demand_steal']:.1f}%). "
            f"Yadrolar hypervisor tomonidan sekinlashtirilgan bo'lishi mumkin — dars sig'imi kamayadi. Hosting qo'llab-quvvatlashiga murojaat qiling."
        )
        for admin in admins:
            try:
                send_notification(
                    sender=admins[0], description=text, target_type='user', user_id=admin.id, kind='cpu_steal_alert',
                )
            except Exception:  # noqa: BLE001 — bildirishnoma xatosi tekshiruvni to'xtatmasin
                logger.exception('cpu steal alert yuborilmadi: %s', admin.id)
