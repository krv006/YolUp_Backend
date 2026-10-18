from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0003_attempt_focus_events'),
    ]

    operations = [
        migrations.AddField(
            model_name='examattempt',
            name='advances',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
