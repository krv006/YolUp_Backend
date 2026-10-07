"""AI tekshiruv olib tashlangach, `checking` (tekshirilmoqda) va `error` (AI xatosi)
holatida qolgan topshiriqlar hech qachon avtomatik qayta ishlanmaydi. Ularni
`pending_review` (o'qituvchi baholashi kutilmoqda) ga o'tkazamiz — faylda
topshiriq bor, o'qituvchi uni o'zi baholaydi."""
from django.db import migrations


def unstick(apps, schema_editor):
    Submission = apps.get_model('homework', 'Submission')
    Submission.objects.filter(status__in=['checking', 'error']).update(status='pending_review', error='')


class Migration(migrations.Migration):
    dependencies = [
        ('homework', '0008_submission_check_attempts'),
    ]

    operations = [
        migrations.RunPython(unstick, migrations.RunPython.noop),
    ]
