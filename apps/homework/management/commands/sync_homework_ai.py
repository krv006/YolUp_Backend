"""Tashqi AI xizmatidan uy vazifasi natijalarini olib keladi.

    python manage.py sync_homework_ai

`checking` holatidagi topshiriqlar uchun AI-home-checker xizmatidan natijani so'raydi
(`HOMEWORK_AI_URL` sozlangan bo'lsa). Tayyor bo'lsa topshiriq o'qituvchi baholashiga
o'tadi (ball AI taklifi bilan to'ldirilgan); xato yoki uzoq kutilsa — o'qituvchi qo'lda
baholaydi. Xizmat sozlanmagan bo'lsa hech narsa qilmaydi. Cron'da 60 soniyalik siklda ishlaydi.
"""
from django.core.management.base import BaseCommand

from apps.homework import services


class Command(BaseCommand):
    help = "Tashqi AI xizmatidan uy vazifasi natijalarini oladi."

    def handle(self, *args, **options):
        result = services.sync_ai_results()
        if any(result.values()):
            self.stdout.write(
                f"AI natijalari: tayyor {result['done']}, qo'lda baholashga {result['failed']}, "
                f"kutilmoqda {result['waiting']}"
            )
