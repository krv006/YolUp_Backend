"""AI bilan test yaratish ishlarini bir qadam oldinga suradi.

    python manage.py sync_ai_quizzes

Faol ishlar (`queued`/`processing`/`generating`) uchun tashqi Test-creator xizmatini chaqiradi
(`TEST_CREATOR_URL` sozlangan bo'lsa); tayyor bo'lsa natija `draft` test bo'lib saqlanadi.
Xizmat sozlanmagan bo'lsa hech narsa qilmaydi. Savollar yaratish uzoq davom etishi mumkin,
shuning uchun cron'da alohida siklda ishlaydi.
"""
from django.core.management.base import BaseCommand

from apps.quizzes import ai_jobs


class Command(BaseCommand):
    help = "Tashqi Test-creator xizmatidan AI test natijalarini oladi."

    def handle(self, *args, **options):
        result = ai_jobs.sync_jobs()
        if any(result.values()):
            self.stdout.write(
                f"AI testlar: tayyor {result['done']}, xato {result['failed']}, kutilmoqda {result['waiting']}"
            )
