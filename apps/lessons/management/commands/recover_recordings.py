"""Qotib qolgan/xato yozuvlarni (xom video+audio fayllari diskda bo'lsa) qayta birlashtiradi.

    python manage.py recover_recordings [--limit 3]

Cron konteynerida har 5 daqiqada ishlaydi (docker-compose.prod.yml). Har yozuvga ko'pi bilan 3 urinish.
"""
from django.core.management.base import BaseCommand

from apps.live import services


class Command(BaseCommand):
    help = "Deploy yoki uzilish tufayli qotib qolgan/xato yozuvlarni qayta birlashtiradi."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=3, help="Bir ishga tushishda ko'pi bilan nechta yozuv.")

    def handle(self, *args, **options):
        report = services.recover_recordings(limit=options['limit'])
        self.stdout.write(self.style.SUCCESS(
            f"Birlashtirildi: {report['merged']}, bitta tomon bilan: {report['single']}, "
            f"holati to'g'rilandi: {report['repaired']}, o'tkazib yuborildi: {report['skipped']}"
        ))
