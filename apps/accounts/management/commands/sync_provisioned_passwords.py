"""Avtomatik ochilgan rol-akkauntlarning noma'lum (tasodifiy) parolini manba akkaunt parolidan nusxalaydi.

    python manage.py sync_provisioned_passwords            # faqat ko'rsatadi (hech narsa yozmaydi)
    python manage.py sync_provisioned_passwords --apply    # yozadi

Oldin `switch_or_provision_role` yangi akkauntga tasodifiy parol qo'yardi (uni hech kim bilmasdi, "Parolni o'zgartirish" ishlamasdi).
Endi yangilari manba parolini oladi; bu buyruq eskilarini tuzatadi. Xavfsizlik shartlari (hammasi bajarilsa nusxalanadi):
  - akkaunt audit'da `auth.role_auto_provisioned` bilan ochilgan (manba — audit yozuvidagi `actor`);
  - parol HECH QACHON o'zgartirilmagan (`password_changed_at` bo'sh): foydalanuvchi o'zi qo'ygan parol bosilmaydi;
  - manba va nishon hozir ham bitta `link_group` da va ikkalasi faol;
  - parollari allaqachon bir xil emas.
Takror ishga tushirish xavfsiz (ikkinchi marta hech narsa o'zgarmaydi).
"""
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.core import audit
from apps.core.models import AuditLog


class Command(BaseCommand):
    help = "Avtomatik ochilgan rol-akkauntlarga manba akkaunt parolini nusxalaydi (standart: faqat ko'rsatadi)."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Haqiqatan yozish (bo\'lmasa faqat ro\'yxat)')

    def handle(self, *args, **options):
        apply = options['apply']
        changed = skipped = 0
        for log in AuditLog.objects.filter(action='auth.role_auto_provisioned').select_related('actor').order_by('created_at'):
            source, target = log.actor, User.objects.filter(pk=log.target_id).first()
            reason = self._skip_reason(source, target)
            label = f'{getattr(target, "username", log.target_id)} ({getattr(target, "role", "?")})'
            if reason:
                skipped += 1
                self.stdout.write(f'  o\'tkazildi: {label}: {reason}')
                continue
            changed += 1
            self.stdout.write(f'  {"yangilandi" if apply else "yangilanadi"}: {label} <- {source.username} ({source.role})')
            if apply:
                target.password = source.password
                target.save(update_fields=['password'])
                audit.record(action='auth.password_synced_from_source', actor=None, target=target, meta={'source_id': str(source.pk)})
        mode = 'YOZILDI' if apply else "SINOV (hech narsa yozilmadi; yozish uchun --apply)"
        self.stdout.write(self.style.SUCCESS(f'{mode}: {changed} ta akkaunt, o\'tkazib yuborilgan: {skipped}'))

    @staticmethod
    def _skip_reason(source, target):
        if source is None or target is None:
            return 'manba yoki nishon akkaunt topilmadi'
        if not (source.is_active and target.is_active):
            return 'akkauntlardan biri faol emas'
        if not source.link_group or source.link_group != target.link_group:
            return 'endi bitta bog\'langan guruhda emas'
        if target.password_changed_at is not None:
            return "parol o'zgartirilgan (foydalanuvchi o'zi qo'ygan), tegilmaydi"
        if source.password == target.password:
            return 'parollar allaqachon bir xil'
        return ''
