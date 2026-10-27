"""Dars yozuvlarining ortiqcha fayllarini tozalaydi (diskni bo'shatish).

    python manage.py prune_recordings                 # faqat HISOBOT: nima qancha joy bo'shatadi (hech narsa o'chmaydi)
    python manage.py prune_recordings --apply         # xom video/audio qismlarni o'chiradi
    python manage.py prune_recordings --apply --drop-webm   # + MP4 tayyor bo'lgan yozuvlarning asl WebM faylini ham

Xavfsizlik qoidalari (har bir o'chirishdan oldin tekshiriladi):
  - faqat TAYYOR (completed) yozuvlar va faqat `--older-than-days` (standart 7) kundan eski;
  - xom qismlar: yakuniy birlashtirilgan fayl diskda bor va bo'sh emas bo'lsagina;
  - asl WebM: MP4/M4A nusxa diskda bor, bo'sh emas va ffprobe uni o'qiy olsagina (yozuv MP4 bilan ko'rsatiladi).
Yozuv bazada qoladi (file_name o'zgarmaydi), ko'rsatish MP4 ga o'tadi (`lessons.services._recording_path`).
"""
import subprocess
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.lessons.models import LessonRecording


def _size(path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _usable(path) -> bool:
    return _size(path) > 0


def _readable(path) -> bool:
    """MP4/M4A haqiqatan o'qiladimi (davomiyligi bor) — ffprobe bilan."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(path)],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    try:
        return result.returncode == 0 and float(result.stdout.strip()) > 0
    except ValueError:
        return False


class Command(BaseCommand):
    help = "Dars yozuvlarining ortiqcha fayllarini (xom qismlar, ixtiyoriy — asl WebM) o'chiradi; standart — faqat hisobot."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help="Haqiqatan o'chirish (usiz — faqat hisobot)")
        parser.add_argument('--drop-webm', action='store_true', help="MP4 tayyor yozuvlarning asl WebM faylini ham o'chirish")
        parser.add_argument('--older-than-days', type=int, default=7, help="Faqat shuncha kundan eski yozuvlar (standart 7)")

    def handle(self, *args, **options):
        root = settings.RECORDINGS_DIR
        cutoff = timezone.now() - timedelta(days=options['older_than_days'])
        raw_bytes = webm_bytes = raw_files = webm_files = 0
        queryset = LessonRecording.objects.filter(status=LessonRecording.Status.COMPLETED, updated_at__lt=cutoff)
        for recording in queryset.iterator():
            final = root / recording.file_name if recording.file_name else None
            if options['drop_webm'] and recording.mp4_file_name and not recording.mp4_error:
                mp4 = root / recording.mp4_file_name
                if final is not None and _usable(final) and _usable(mp4) and _readable(mp4):
                    webm_bytes += _size(final)
                    webm_files += 1
                    if options['apply']:
                        final.unlink(missing_ok=True)
                    final = mp4  # xom qismlar uchun "yakuniy fayl" endi MP4
            if final is None or not _usable(final):
                continue  # yakuniy fayl yo'q — xom qismlar yagona nusxa bo'lishi mumkin, tegmaymiz
            for name in (recording.video_file_name, recording.audio_file_name):
                if not name or name in (recording.file_name, recording.mp4_file_name):
                    continue  # bir qism yakuniy fayl sifatida ishlatilgan bo'lishi mumkin — tegmaymiz
                path = root / name
                if path.exists() and path != final:
                    raw_bytes += _size(path)
                    raw_files += 1
                    if options['apply']:
                        path.unlink(missing_ok=True)

        verb = "o'chirildi" if options['apply'] else "o'chirilishi mumkin"
        gib = 1024 ** 3
        self.stdout.write(f'Xom video/audio qismlar: {raw_files} ta, {raw_bytes / gib:.2f} GB {verb}')
        if options['drop_webm']:
            self.stdout.write(f'Asl WebM (MP4 tayyor): {webm_files} ta, {webm_bytes / gib:.2f} GB {verb}')
        if not options['apply']:
            self.stdout.write("Bu faqat hisobot. Haqiqatan o'chirish uchun --apply qo'shing.")
