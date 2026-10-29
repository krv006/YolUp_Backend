"""Birlashtirib bo'lmagan yozuvlar haqida adminlarga bildiradi.

    python manage.py check_failed_recordings

`recover_recordings` har yozuvga ko'pi bilan `MERGE_MAX_ATTEMPTS` marta urinadi. Shundan keyin ham `FAILED` bo'lib qolgan
yozuv o'zi tuzalmaydi — dars yozuvi yo'qolishi mumkin, shuning uchun admin xabardor qilinadi (har yozuv uchun bir marta
tekshiriladi, 7 kun ichida takrorlanmaydi). Bildirishnoma yuborib bo'lmasa ham log yoziladi.
"""
import logging
from html import escape

from django.core.cache import cache
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.live.services import MERGE_MAX_ATTEMPTS

from ...models import LessonRecording

logger = logging.getLogger('apps')
REPEAT_SECONDS = 7 * 24 * 3600


class Command(BaseCommand):
    help = "Qayta urinishlardan keyin ham birlashmagan (FAILED) yozuvlar haqida adminlarga bildirishnoma yuboradi."

    def handle(self, *args, **options):
        stuck = list(
            LessonRecording.objects.select_related('lesson__course')
            .filter(status=LessonRecording.Status.FAILED, merge_attempts__gte=MERGE_MAX_ATTEMPTS)
            .order_by('updated_at')[:50]
        )
        fresh = [rec for rec in stuck if cache.add(f'recording-failed-alert:{rec.pk}', 1, REPEAT_SECONDS)]
        if not fresh:
            return
        for rec in fresh:
            logger.error('recording %s birlashmadi (%d urinish): %s', rec.pk, rec.merge_attempts, (rec.error or '')[:200])
        admins = list(User.objects.filter(role=User.Role.ADMIN, is_active=True))
        if not admins:
            return
        from apps.notifications.services import send_notification

        names = ', '.join(escape(rec.lesson.title or rec.lesson.course.title) for rec in fresh[:5])
        more = f' va yana {len(fresh) - 5} ta' if len(fresh) > 5 else ''
        text = (f"{len(fresh)} ta dars yozuvi {MERGE_MAX_ATTEMPTS} urinishdan keyin ham birlashtirilmadi: {names}{more}. "
                "Xom fayllar serverda saqlangan; xato matni admin panelida (Dars yozuvlari).")
        for admin in admins:
            try:
                send_notification(
                    sender=admins[0], description=text, target_type='user', user_id=admin.id, kind='recording_failed',
                )
            except Exception:  # noqa: BLE001 — bildirishnoma xatosi tekshiruvni to'xtatmasin
                logger.exception('recording_failed alert yuborilmadi: %s', admin.id)
        self.stdout.write(f'{len(fresh)} ta yozuv haqida xabar yuborildi')
