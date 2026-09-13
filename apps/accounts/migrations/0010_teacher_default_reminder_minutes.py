# Generated manually — data migration, no schema change.
from django.db import migrations

TEACHER_LESSON_REMINDER_MINUTES = 10
_PREVIOUS_DEFAULT = 15


def set_teacher_default(apps, schema_editor):
    """Mavjud o'qituvchilar ham (feature qo'shilganda hali eski standart
    15 daqiqada qolgan bo'lsa) endi 10 daqiqaga o'tkaziladi. O'zi qo'lda
    boshqa qiymat qo'ygan o'qituvchiga tegilmaydi (15dan farqli bo'lsa)."""
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='teacher', lesson_reminder_minutes=_PREVIOUS_DEFAULT).update(
        lesson_reminder_minutes=TEACHER_LESSON_REMINDER_MINUTES,
    )


def reverse(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='teacher', lesson_reminder_minutes=TEACHER_LESSON_REMINDER_MINUTES).update(
        lesson_reminder_minutes=_PREVIOUS_DEFAULT,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_user_lesson_reminder_minutes'),
    ]

    operations = [
        migrations.RunPython(set_teacher_default, reverse),
    ]
