"""Jonli dars boshlanib 10 daqiqa o'tgan, lekin kirmagan o'quvchilarning ota-onalariga "darsga kelmadi" xabari.

    python manage.py send_absence_alerts
"""
from django.core.management.base import BaseCommand

from apps.lessons import services


class Command(BaseCommand):
    help = "Kirmagan o'quvchilar haqida ota-onaga bildirishnoma (har o'quvchi/dars uchun bir marta)."

    def handle(self, *args, **options):
        self.stdout.write(f'Yuborildi: {services.send_absence_alerts()}')
