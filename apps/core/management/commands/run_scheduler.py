"""Davriy vazifalarni BITTA doimiy jarayonda bajaradi (cron xizmati uchun).

    python manage.py run_scheduler [--startup-delay 30]

Avval har vazifa uchun `sleep` sikli ichida alohida `python manage.py ...` ishga tushardi: har safar Django qayta yuklanib
~1 CPU-soniya ketardi (o'lchangan: Linux, Postgres) va doimiy ~0,15 yadro band bo'lardi. Endi Django bir marta yuklanadi.
Har vazifa o'z oqimida (thread) ishlaydi — sekin vazifa (masalan tashqi AI) qolganlarni to'xtatmaydi; xato bo'lsa
log yoziladi va keyingi davrda qayta uriniladi.
"""
import logging
import signal
import threading
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import close_old_connections

logger = logging.getLogger('apps')

# (buyruq, davr soniyada) — avvalgi docker-compose sikllari bilan bir xil
JOBS = [
    ('auto_finish_expired_lessons', 300),
    ('recover_recordings', 300),
    ('send_deadline_reminders', 300),
    ('close_stale_voice_rooms', 300),
    ('sync_ai_quizzes', 30),
    ('sync_exam_writing_ai', 30),
    ('send_lesson_reminders', 60),
    ('sync_homework_ai', 60),
]


def run_job(name: str) -> bool:
    """Bitta vazifani bajaradi; xato butun rejalashtiruvchini yiqitmaydi. Muvaffaqiyat bo'lsa True."""
    try:
        call_command(name, verbosity=0)
        return True
    except Exception:  # noqa: BLE001 — keyingi davrda qayta uriniladi
        logger.exception('scheduler: %s xato bilan tugadi', name)
        return False
    finally:
        close_old_connections()  # oqim uchun ochilgan baza ulanishi qolib ketmasin


class Command(BaseCommand):
    help = "Davriy vazifalarni (eslatmalar, avto-yakunlash, yozuvni tiklash, AI sinxronizatsiya) bitta jarayonda bajaradi."

    def add_arguments(self, parser):
        parser.add_argument('--startup-delay', type=int, default=30, help="Birinchi ishga tushishdan oldin kutish (soniya)")

    def handle(self, *args, **options):
        stop = threading.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, lambda *_: stop.set())
            except ValueError:  # asosiy oqim emas
                pass

        def loop(name, period):
            while not stop.is_set():
                started = time.monotonic()
                run_job(name)
                stop.wait(max(1.0, period - (time.monotonic() - started)))

        if stop.wait(options['startup_delay']):
            return
        threads = [threading.Thread(target=loop, args=job, name=f'sched-{job[0]}', daemon=True) for job in JOBS]
        for thread in threads:
            thread.start()
        self.stdout.write(f'Rejalashtiruvchi ishga tushdi: {len(JOBS)} ta vazifa')
        stop.wait()
