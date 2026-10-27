"""Bazada yozuvi qolmagan (kurs o'chirilgan) yetim yozuv fayllarini o'chiradi.

    python manage.py prune_orphan_recordings            # faqat hisobot
    python manage.py prune_orphan_recordings --apply    # o'chiradi

Ikki serverli joylashtirishda kursni sayt serveri o'chiradi, fayllar esa yozuv serverida turadi — shu buyruq u yerda
yetim qolgan fayllarni tozalaydi. Xavfsizlik: faqat `--min-age-hours` (standart 48) dan eski fayllar (yuklanayotganlarga
tegmaydi); bir ishga tushishda ko'pi bilan `--max-delete` (standart 50) fayl; baza ulanmagan/bo'sh bo'lsa (yozuv qatori
umuman yo'q) hech narsa o'chirilmaydi; `RECORDINGS_LOCAL=0` serverda ishlamaydi.
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.lessons.models import LessonRecording

NAME_FIELDS = ('file_name', 'mp4_file_name', 'video_file_name', 'audio_file_name')


def referenced_names() -> set:
    names = set()
    for row in LessonRecording.objects.values_list(*NAME_FIELDS).iterator():
        names.update(name for name in row if name)
    return names


class Command(BaseCommand):
    help = "Bazada yozuvi yo'q yetim yozuv fayllarini o'chiradi (standart — faqat hisobot)."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help="Haqiqatan o'chirish")
        parser.add_argument('--min-age-hours', type=int, default=48)
        parser.add_argument('--max-delete', type=int, default=50)

    def handle(self, *args, **options):
        if not settings.RECORDINGS_LOCAL:
            self.stdout.write("Bu serverda yozuv fayllari yo'q (RECORDINGS_LOCAL=0)")
            return
        root = settings.RECORDINGS_DIR
        files = [p for p in root.iterdir() if p.is_file()]
        if files and not LessonRecording.objects.exists():
            self.stdout.write("Bazada birorta yozuv qatori yo'q, lekin fayllar bor — xavfsizlik uchun hech narsa o'chirilmadi")
            return
        known = referenced_names()
        cutoff = time.time() - options['min_age_hours'] * 3600
        orphans = [p for p in files if p.name not in known and p.stat().st_mtime < cutoff]
        size = sum(p.stat().st_size for p in orphans)
        gib = 1024 ** 3
        if not options['apply']:
            self.stdout.write(f"Yetim fayllar: {len(orphans)} ta, {size / gib:.2f} GB (o'chirish uchun --apply)")
            return
        removed = 0
        for path in orphans[:options['max_delete']]:
            path.unlink(missing_ok=True)
            removed += 1
        self.stdout.write(f"{removed} ta yetim fayl o'chirildi (jami topilgan: {len(orphans)})")
