"""Eski bildirishnomalarni tozalaydi (jadval cheksiz o'smasligi uchun).

    python manage.py prune_notifications                  # faqat HISOBOT (hech narsa o'chmaydi)
    python manage.py prune_notifications --apply          # 180 kundan eskilarini o'chiradi
    python manage.py prune_notifications --apply --days 90

Bildirishnoma o'chganda uning qabul qiluvchi qatorlari ham o'chadi (CASCADE). Saqlash muddati — mahsulot qarori,
shuning uchun standart ehtiyotkor (180 kun) va `--apply`siz hech narsa o'zgarmaydi.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification, NotificationRecipient


class Command(BaseCommand):
    help = "Belgilangan muddatdan eski bildirishnomalarni o'chiradi (standart — faqat hisobot)."

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=180, help='Shu kundan eski bildirishnomalar (standart 180)')
        parser.add_argument('--apply', action='store_true', help="Haqiqatan o'chirish (usiz — faqat hisobot)")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options['days'])
        old = Notification.objects.filter(created_at__lt=cutoff)
        notifications = old.count()
        recipients = NotificationRecipient.objects.filter(notification__in=old).count()
        if options['apply']:
            # bo'laklab o'chiramiz — katta jadvalda bitta uzoq tranzaksiya bo'lmasin
            while True:
                batch = list(old.values_list('pk', flat=True)[:2000])
                if not batch:
                    break
                Notification.objects.filter(pk__in=batch).delete()
            self.stdout.write(f"{notifications} ta bildirishnoma ({recipients} ta qabul qiluvchi qatori) o'chirildi")
        else:
            self.stdout.write(f"{notifications} ta bildirishnoma ({recipients} ta qabul qiluvchi qatori) o'chirilishi mumkin; "
                              "o'chirish uchun --apply qo'shing")
