"""Tugagan IELTS imtihonlaridagi Writing insholarini Gemini bilan baholaydi.

    python manage.py grade_exam_writing

Natija o'qituvchiga TAKLIF sifatida saqlanadi (`apps.exams.writing`) — ball
o'qituvchi tasdiqlamaguncha o'quvchiga/umumiy bandga o'tmaydi. Cron'da 5
daqiqalik siklda ishlaydi; bir yurishda `CRON_BATCH` insho (kvota uchun).
"""
import logging

from django.core.management.base import BaseCommand

from apps.exams import writing

logger = logging.getLogger('apps')


class Command(BaseCommand):
    help = "Tugagan IELTS imtihonlarida Writing insholarini AI bilan baholaydi (taklif sifatida)."

    def handle(self, *args, **options):
        done = 0
        for attempt_id in writing.pending_attempts():
            if not writing._claim(attempt_id):
                continue
            writing.run_check(attempt_id)
            done += 1
        self.stdout.write(f'Baholangan insholar: {done}')
