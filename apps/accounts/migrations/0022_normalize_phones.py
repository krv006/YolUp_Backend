"""Bazadagi barcha telefon raqamlarini `+998XXXXXXXXX` ko'rinishiga keltiradi (2026-11-10).

Sabab: frontend raqamni foydalanuvchi qanday yozsa shunday yuborgan ("901234567",
"+998 90 123 45 67", ...), shuning uchun bitta odamning rol-akkauntlari bir-biriga
bog'lanmay, akkaunt almashtirish faqat 1 ta akkaunt ko'rsatgan. `phone` UNIQUE emas,
shuning uchun to'qnashuv bo'lmaydi. Noto'g'ri (raqam bo'lmagan) qiymatlarga tegilmaydi.
Qaytarib bo'lmaydi (asl yozilish bilmaymiz) — reverse hech narsa qilmaydi.
"""
import re

from django.db import migrations


def _canonical(raw):
    digits = re.sub(r'\D', '', raw or '')
    if len(digits) == 9:
        digits = '998' + digits
    return f'+{digits}' if 9 <= len(digits) <= 15 else ''


def normalize_phones(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    batch = []
    for user in User.objects.exclude(phone__isnull=True).exclude(phone='').only('id', 'phone').iterator(chunk_size=500):
        new = _canonical(user.phone)
        if new and new != user.phone:
            user.phone = new
            batch.append(user)
        if len(batch) >= 500:
            User.objects.bulk_update(batch, ['phone'])
            batch = []
    if batch:
        User.objects.bulk_update(batch, ['phone'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_parent_design_fields'),
    ]

    operations = [
        migrations.RunPython(normalize_phones, migrations.RunPython.noop),
    ]
