"""Bazadagi barcha ma'lumotni o'chiradi, faqat hisoblar qoladi.

    python manage.py wipe_data_keep_accounts                      # dry-run: faqat sanaydi
    python manage.py wipe_data_keep_accounts --confirm \
        --backup-file /path/backup.sql                            # haqiqiy o'chirish

Qoladi: `accounts.User`, `accounts.ParentChildLink` (+ standart: `Consent`,
`TeacherCertificate` — `--wipe-account-extras` bilan ular ham o'chadi) va
tizim jadvallari (contenttypes, auth ruxsatlari, sessiyalar, JWT blacklist).

Faqat BAZA tozalanadi — diskdagi fayllar (`recordings`, `media`) tegilmaydi.
Hammasi bitta tranzaksiyada: xato bo'lsa hech narsa o'chmaydi. Haqiqiy
o'chirish uchun bo'sh bo'lmagan zaxira fayl yo'li majburiy.
"""
import os
from collections import Counter

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import CASCADE, ProtectedError

KEEP = {'accounts.user', 'accounts.parentchildlink'}
ACCOUNT_EXTRAS = {'accounts.consent', 'accounts.teachercertificate'}
KEEP_APPS = {'contenttypes', 'auth', 'sessions', 'token_blacklist'}


def _label(model) -> str:
    return model._meta.label_lower


class Command(BaseCommand):
    help = "Hisoblardan (User, ParentChildLink) tashqari barcha ma'lumotni o'chiradi."

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help="Haqiqatan o'chirish (usiz — dry-run).")
        parser.add_argument('--backup-file', help="Bo'sh bo'lmagan zaxira (pg_dump) fayl yo'li — --confirm bilan majburiy.")
        parser.add_argument(
            '--wipe-account-extras', action='store_true',
            help="Consent va TeacherCertificate'ni ham o'chirish (standart: qoladi).",
        )

    def handle(self, *args, **options):
        keep = set(KEEP)
        if not options['wipe_account_extras']:
            keep |= ACCOUNT_EXTRAS
        kept_models = [m for m in apps.get_models() if _label(m) in keep]
        wipe_models = [
            m for m in apps.get_models()
            if _label(m) not in keep and m._meta.app_label not in KEEP_APPS
            and not m._meta.auto_created
        ]
        self._guard_kept_models(kept_models, wipe_models)

        counts = {_label(m): m.objects.count() for m in wipe_models}
        total = sum(counts.values())
        self.stdout.write("O'chiriladigan qatorlar (0 dan katta jadvallar):")
        for label, n in sorted(counts.items(), key=lambda x: -x[1]):
            if n:
                self.stdout.write(f'  {label}: {n}')
        self.stdout.write(f'JAMI: {total} qator, {sum(1 for n in counts.values() if n)} jadvaldan.')
        self.stdout.write("Qoladi: " + ', '.join(f'{_label(m)}={m.objects.count()}' for m in kept_models))

        if not options['confirm']:
            self.stdout.write(self.style.WARNING("DRY-RUN — hech narsa o'chirilmadi. Haqiqiy o'chirish: --confirm --backup-file <fayl>"))
            return

        backup = options['backup_file']
        if not backup or not os.path.isfile(backup) or os.path.getsize(backup) == 0:
            raise CommandError("--confirm uchun bo'sh bo'lmagan --backup-file majburiy (avval pg_dump qiling).")

        with transaction.atomic():
            self._delete_all(wipe_models)
        self.stdout.write(self.style.SUCCESS(f"Tayyor: {total} qator o'chirildi."))

    def _guard_kept_models(self, kept_models, wipe_models):
        """Qoladigan model qatori o'chadigan modelga CASCADE bilan bog'langan
        bo'lsa, o'chirish hisoblarni ham olib ketardi — shunda to'xtaymiz."""
        wipe = set(wipe_models)
        for model in kept_models:
            for field in model._meta.concrete_fields:
                remote = field.remote_field
                if remote is not None and remote.model in wipe and remote.on_delete is CASCADE:
                    raise CommandError(
                        f'XAVFLI: {model._meta.label}.{field.name} -> {remote.model._meta.label} '
                        f'CASCADE. O\'chirish hisoblarni ham o\'chirardi; to\'xtatildi.'
                    )

    def _delete_all(self, models):
        """PROTECT bog'lanishlar tufayli tartib muhim — ProtectedError bo'lsa,
        keyingi modelga o'tib, oxirida takrorlaymiz (progress bo'lmasa xato)."""
        pending = list(models)
        while pending:
            failed = []
            for model in pending:
                try:
                    with transaction.atomic():
                        model.objects.all().delete()
                except ProtectedError:
                    failed.append(model)
            if len(failed) == len(pending):
                names = Counter(_label(m) for m in failed)
                raise CommandError(f"PROTECT sababli o'chirib bo'lmadi: {dict(names)}")
            pending = failed
