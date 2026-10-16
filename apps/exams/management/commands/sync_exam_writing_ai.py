"""IELTS Writing uchun navbatdagi AI tahlillarini bajaradi (cron, har 30 soniyada).

    python manage.py sync_exam_writing_ai
"""
from django.core.management.base import BaseCommand

from apps.exams import services


class Command(BaseCommand):
    help = "Imtihon Writing javoblarini AI bilan IELTS mezonlari bo'yicha baholaydi."

    def handle(self, *args, **options):
        result = services.sync_writing_ai()
        if any(result.values()):
            self.stdout.write(f"Writing AI: tayyor {result['done']}, xato {result['failed']}")
