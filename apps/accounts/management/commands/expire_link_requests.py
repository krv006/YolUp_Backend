"""Muddati o'tgan (LINK_REQUEST_TTL_DAYS, standart 7 kun) javob kutilayotgan ota-ona -> o'quvchi so'rovlarini o'chiradi.

    python manage.py expire_link_requests
"""
from django.core.management.base import BaseCommand

from apps.accounts import services


class Command(BaseCommand):
    help = "Muddati o'tgan PENDING bog'lanish so'rovlarini o'chiradi."

    def handle(self, *args, **options):
        deleted = services.expire_link_requests()
        self.stdout.write(f"Muddati o'tgan so'rovlar o'chirildi: {deleted}")
