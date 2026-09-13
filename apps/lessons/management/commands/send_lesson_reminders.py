"""Dars boshlanishidan oldin eslatma — davriy chaqirish uchun (tashqi cron).

    python manage.py send_lesson_reminders

Loyihada Celery yo'q — shu buyruq server crontab'ida **har daqiqada**
ishga tushirilishi kerak (boshqa davriy vazifalardan farqli — bu yerda
vaqt aniqligi muhim, 10 daqiqalik cron oralig'i eslatmani 5-15 daqiqa
orasida noaniq qilib qo'yardi). Har (dars, foydalanuvchi) juftligiga
eslatma FAQAT BIR MARTA yuboriladi (Lesson.reminders — LessonReminder
modeli) — buyruqni qancha tez-tez ishga tushirish xavfsiz.
"""
from django.core.management.base import BaseCommand

from apps.lessons import services


class Command(BaseCommand):
    help = "Boshlanishiga oz qolgan darslar uchun o'qituvchi va o'quvchilarga eslatma yuboradi."

    def handle(self, *args, **options):
        sent = services.send_lesson_reminders()
        self.stdout.write(self.style.SUCCESS(f'Yuborilgan eslatmalar: {sent}'))
