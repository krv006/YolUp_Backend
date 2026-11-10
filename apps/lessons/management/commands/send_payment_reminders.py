"""To'lov muddati eslatmalari (har soat ishga tushiriladi, har eslatma bir martadan yuboriladi).

    python manage.py send_payment_reminders
"""
from django.core.management.base import BaseCommand

from apps.lessons import payments


class Command(BaseCommand):
    help = "Muddatdan 3/5/7 kun oldin to'lamagan o'quvchilar va ularning ota-onalariga eslatma yuboradi."

    def handle(self, *args, **options):
        sent = payments.send_reminders()
        self.stdout.write(self.style.SUCCESS(f"Yuborildi: o'quvchilarga={sent['students']}, ota-onalarga={sent['parents']}"))
