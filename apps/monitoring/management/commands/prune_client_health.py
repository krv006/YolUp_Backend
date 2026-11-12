"""Eski mijoz salomatlik hisobotlarini o'chiradi (standart 14 kundan eski)."""
from django.core.management.base import BaseCommand

from apps.monitoring import client_health


class Command(BaseCommand):
    help = "14 kundan eski ClientHealthReport yozuvlarini o'chiradi"

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=client_health.RETENTION_DAYS)

    def handle(self, *args, **options):
        self.stdout.write(f"O'chirildi: {client_health.prune(days=options['days'])}")
