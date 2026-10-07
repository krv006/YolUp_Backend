"""Qotib qolgan ("tekshirilmoqda") uy vazifalarini qayta tekshiradi.

    python manage.py recover_stuck_submissions

AI tekshiruv server ichidagi fon oqimida ishlaydi; deploy yoki konteyner qayta
ishga tushganda ketayotgan tekshiruvlar yo'qoladi. Bu buyruq 10 daqiqadan beri
`checking`da turganlarini qayta ishga tushiradi (3 urinishgacha, keyin `error`).
Cron'da 5 daqiqalik siklda ishlaydi.
"""
from django.core.management.base import BaseCommand

from apps.homework import services


class Command(BaseCommand):
    help = "Qotib qolgan uy vazifasi tekshiruvlarini qayta ishga tushiradi."

    def handle(self, *args, **options):
        result = services.recover_stuck_checks()
        self.stdout.write(f"Qayta tekshirildi: {result['retried']}, xatoga o'tkazildi: {result['failed']}")
