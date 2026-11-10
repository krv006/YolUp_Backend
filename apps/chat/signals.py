"""Guruh a'zoligi va ota-ona bog'lanishi o'zgarganda kanallarni sinxronlaydi (2026-11-10): guruhga keyin qo'shilgan o'quvchi
va uning ota-onalari bog'langan kanalga avtomatik qo'shiladi, guruhdan chiqqani chiqadi. Xato asosiy amalni (yozilish,
bog'lanish) to'xtatmasin."""
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.models import ParentChildLink
from apps.lessons.models import Enrollment

logger = logging.getLogger('apps')


def _safe(fn, *args):
    try:
        fn(*args)
    except Exception:  # noqa: BLE001
        logger.exception('channel membership sync failed')


@receiver(post_save, sender=Enrollment)
def enrollment_saved(sender, instance, **kwargs):
    from . import channel_service

    if instance.status == Enrollment.Status.APPROVED:
        _safe(channel_service.sync_student_joined, instance.course_id, instance.student_id)
    else:
        _safe(channel_service.sync_student_left, instance.course_id, instance.student_id)


@receiver(post_delete, sender=Enrollment)
def enrollment_deleted(sender, instance, **kwargs):
    from . import channel_service

    _safe(channel_service.sync_student_left, instance.course_id, instance.student_id)


@receiver(post_save, sender=ParentChildLink)
def link_saved(sender, instance, **kwargs):
    from . import channel_service

    if instance.status == ParentChildLink.Status.APPROVED:
        _safe(channel_service.sync_parent_linked, instance.parent_id, instance.student_id)
    else:
        _safe(channel_service.sync_parent_unlinked, instance.parent_id)


@receiver(post_delete, sender=ParentChildLink)
def link_deleted(sender, instance, **kwargs):
    from . import channel_service

    _safe(channel_service.sync_parent_unlinked, instance.parent_id)
