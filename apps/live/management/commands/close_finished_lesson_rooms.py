"""Tugagan darsning hamon ochiq (yoki qayta ochilgan) LiveKit xonasini yopadi.

    python manage.py close_finished_lesson_rooms

Sabab: dars tugaganda xona yopiladi, lekin o'quvchida eski token qolgan bo'lsa (yoki brauzer o'zi qayta ulansa) LiveKit
xonani qayta yaratib yuboradi va dars "tugagan" bo'lsa ham odam kira oladi. Cron har daqiqa ishga tushiradi.
"""
from django.core.management.base import BaseCommand

from apps.live import services


class Command(BaseCommand):
    help = "Tugagan yoki bekor qilingan darslarning ochiq qolgan LiveKit xonalarini yopadi."

    def handle(self, *args, **options):
        closed = services.close_finished_lesson_rooms()
        self.stdout.write(self.style.SUCCESS(f'Yopilgan xonalar: {closed}'))
