import uuid

from django.db import migrations, models


def backfill_from_audit(apps, schema_editor):
    """`switch-role` bilan ochilgan juftliklarni (audit `auth.role_auto_provisioned`) bog'langan deb belgilaydi.
    Faqat raqami bir xil bo'lgan, lekin shunday ochilmagan juftliklar bog'lanmaydi (parol bilan bog'lanadi)."""
    User = apps.get_model('accounts', 'User')
    AuditLog = apps.get_model('core', 'AuditLog')

    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for actor_id, target_id in AuditLog.objects.filter(action='auth.role_auto_provisioned').values_list('actor_id', 'target_id'):
        if actor_id and target_id:
            parent[find(str(actor_id))] = find(str(target_id))

    groups = {}
    for node in list(parent):
        groups.setdefault(find(node), []).append(node)
    for members in groups.values():
        if len(members) < 2:
            continue
        User.objects.filter(pk__in=members).update(link_group=uuid.uuid4())


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0025_alter_user_role'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='link_group',
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(backfill_from_audit, migrations.RunPython.noop),
    ]
