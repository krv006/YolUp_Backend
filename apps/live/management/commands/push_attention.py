"""Vaqti kelgan "Siz shu yerdamisiz?" tekshiruvlarini o'quvchilarga WebSocket orqali yuboradi (run_scheduler har 2 soniyada chaqiradi)."""
from django.core.management.base import BaseCommand

from apps.live import services


class Command(BaseCommand):
    help = "Vaqti kelgan diqqat tekshiruvlarini o'quvchilarning doska socketiga yuboradi."

    def handle(self, *args, **options):
        pushed = services.push_due_attention()
        if pushed:
            self.stdout.write(f'Yuborildi: {pushed}')
