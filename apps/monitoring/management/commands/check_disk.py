"""Disk to'lib borayotganini adminlarga bildiradi (yozuvlar kuniga 9-20 GB qo'shadi).

    python manage.py check_disk [--warn 80] [--critical 90]

Chegaradan oshsa — barcha adminlarga bildirishnoma (har daraja uchun 12 soatda bir marta, takrorlanmaydi). Bildirishnoma
yuborib bo'lmasa ham log yoziladi.
"""
import logging
from html import escape

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.monitoring import services

logger = logging.getLogger('apps')
REPEAT_SECONDS = 12 * 3600


class Command(BaseCommand):
    help = "Disk to'lganligini tekshiradi; chegaradan oshsa adminlarga bildirishnoma yuboradi."

    def add_arguments(self, parser):
        parser.add_argument('--warn', type=float, default=80.0, help='Ogohlantirish chegarasi, % (standart 80)')
        parser.add_argument('--critical', type=float, default=90.0, help='Jiddiy chegara, % (standart 90)')

    def handle(self, *args, **options):
        percent = services.disk_percent()
        if percent is None:
            self.stdout.write("Diskni o'lchab bo'lmadi")
            return
        self.stdout.write(f'Disk: {percent}%')
        if percent >= options['critical']:
            level = 'critical'
        elif percent >= options['warn']:
            level = 'warn'
        else:
            return
        role = settings.SERVER_ROLE or 'server'
        logger.warning('disk %s: %s%% (%s)', level, percent, role)
        if not cache.add(f'disk-alert:{role}:{level}', 1, REPEAT_SECONDS):
            return  # yaqinda yuborilgan
        admins = list(User.objects.filter(role=User.Role.ADMIN, is_active=True))
        if not admins:
            return
        from apps.notifications.services import send_notification

        prefix = 'JIDDIY: ' if level == 'critical' else ''
        text = escape(f"{prefix}{role} serverida disk {percent}% to'lgan. Yozuvlarni tozalash yoki disk qo'shish kerak.")
        for admin in admins:
            try:
                send_notification(
                    sender=admins[0], description=text, target_type='user', user_id=admin.id, kind='disk_alert',
                )
            except Exception:  # noqa: BLE001 — bildirishnoma xatosi tekshiruvni to'xtatmasin
                logger.exception('disk alert yuborilmadi: %s', admin.id)
