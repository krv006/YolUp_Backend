"""Davriy vazifalarni BITTA doimiy jarayonda bajaradi (cron xizmati uchun).

    python manage.py run_scheduler [--startup-delay 30] [--only a,b] [--skip a,b]

`--skip` / `--only` — ikki serverli joylashtirishda vazifalarni bo'lish uchun: sayt serveri yozuv fayllari bilan bog'liq
vazifalarni o'tkazib yuboradi (`--skip recover_recordings`), yozuv serveri esa faqat o'zinikini bajaradi
(`--only recover_recordings,prune_orphan_recordings,check_disk`).

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
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

logger = logging.getLogger('apps')

# (nom, buyruq, buyruq argumentlari, davr soniyada) — avvalgi docker-compose sikllari bilan bir xil
JOBS = [
    ('auto_finish_expired_lessons', 'auto_finish_expired_lessons', (), 300),
    ('recover_recordings', 'recover_recordings', (), 300),
    ('send_deadline_reminders', 'send_deadline_reminders', (), 300),
    ('close_stale_voice_rooms', 'close_stale_voice_rooms', (), 300),
    ('sync_ai_quizzes', 'sync_ai_quizzes', (), 30),
    ('sync_exam_writing_ai', 'sync_exam_writing_ai', (), 30),
    ('send_lesson_reminders', 'send_lesson_reminders', (), 60),
    ('sync_homework_ai', 'sync_homework_ai', (), 60),
    ('check_disk', 'check_disk', (), 1800),
]
# Standart ro'yxatga KIRMAYDI (fayl o'chiradi) — faqat `--only` bilan aniq so'ralganda ishga tushadi
OPTIONAL_JOBS = [
    ('prune_orphan_recordings', 'prune_orphan_recordings', ('--apply',), 3600),
]


def select_jobs(only=None, skip=None) -> list:
    """`--only` bo'lsa shu nomlar (ixtiyoriylar ham), aks holda standart ro'yxat; so'ng `--skip` chiqarib tashlanadi."""
    known = {job[0]: job for job in JOBS + OPTIONAL_JOBS}
    for name in [*(only or []), *(skip or [])]:
        if name not in known:
            raise CommandError(f"Noma'lum vazifa: {name}. Mavjud: {', '.join(known)}")
    chosen = [known[name] for name in only] if only else list(JOBS)
    return [job for job in chosen if job[0] not in (skip or [])]


def run_job(command: str, args=()) -> bool:
    """Bitta vazifani bajaradi; xato butun rejalashtiruvchini yiqitmaydi. Muvaffaqiyat bo'lsa True."""
    try:
        call_command(command, *args, verbosity=0)
        return True
    except Exception:  # noqa: BLE001 — keyingi davrda qayta uriniladi
        logger.exception('scheduler: %s xato bilan tugadi', command)
        return False
    finally:
        close_old_connections()  # oqim uchun ochilgan baza ulanishi qolib ketmasin


def _names(value: str) -> list:
    return [item.strip() for item in (value or '').split(',') if item.strip()]


class Command(BaseCommand):
    help = "Davriy vazifalarni (eslatmalar, avto-yakunlash, yozuvni tiklash, AI sinxronizatsiya) bitta jarayonda bajaradi."

    def add_arguments(self, parser):
        parser.add_argument('--startup-delay', type=int, default=30, help="Birinchi ishga tushishdan oldin kutish (soniya)")
        parser.add_argument('--only', default='', help="Faqat shu vazifalar (vergul bilan)")
        parser.add_argument('--skip', default='', help="Shu vazifalarni o'tkazib yuborish (vergul bilan)")

    def handle(self, *args, **options):
        jobs = select_jobs(_names(options['only']), _names(options['skip']))
        stop = threading.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, lambda *_: stop.set())
            except ValueError:  # asosiy oqim emas
                pass

        def loop(label, command, command_args, period):
            while not stop.is_set():
                started = time.monotonic()
                run_job(command, command_args)
                stop.wait(max(1.0, period - (time.monotonic() - started)))

        if stop.wait(options['startup_delay']):
            return
        for label, command, command_args, period in jobs:
            threading.Thread(target=loop, args=(label, command, command_args, period), name=f'sched-{label}', daemon=True).start()
        self.stdout.write(f'Rejalashtiruvchi ishga tushdi: {len(jobs)} ta vazifa ({", ".join(job[0] for job in jobs)})')
        stop.wait()
