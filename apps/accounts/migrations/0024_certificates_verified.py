"""Doim "Tekshirilmoqda" bo'lib qolgan sertifikatlarni tasdiqlangan qiladi (Trello: "profile qismda xato", 2026-11-10).
Admin tasdig'i amalda ishlatilmagan; rad etilganlarga tegilmaydi. Qaytarib bo'lmaydi (reverse hech narsa qilmaydi)."""
from django.db import migrations
from django.utils import timezone


def verify_pending(apps, schema_editor):
    Certificate = apps.get_model('accounts', 'TeacherCertificate')
    Certificate.objects.filter(status='pending').update(status='verified', verified_at=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_can_create_tests'),
    ]

    operations = [
        migrations.RunPython(verify_pending, migrations.RunPython.noop),
    ]
