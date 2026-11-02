"""Uy vazifasi deadline eslatmalari — davriy chaqirish uchun (tashqi cron).

    python manage.py send_deadline_reminders

Loyihada Celery/Celery Beat yo'q — shu buyruq server crontab'ida (yoki
docker-compose'da alohida yengil cron konteynerida) har 5-15 daqiqada bir
ishga tushirilishi kerak. Har bir eslatma FAQAT BIR MARTA yuboriladi
(Assignment.reminder_halfway_sent_at / reminder_1h_sent_at bilan
belgilanadi) — buyruqni qancha tez-tez ishga tushirish farqi yo'q.
"""
from django.core.management.base import BaseCommand

from apps.homework import services


class Command(BaseCommand):
    help = "Deadline'i yaqinlashgan (yarim vaqt / 1 soat qoldi) vazifalar uchun hali topshirmagan o'quvchilarga eslatma yuboradi."

    def handle(self, *args, **options):
        sent = services.send_deadline_reminders()
        self.stdout.write(self.style.SUCCESS(
            f"Yuborildi: yarim-vaqt={sent['halfway']}, 1-soat={sent['1h']}, ota-onalarga 24-soat={sent['parents']}"
        ))
