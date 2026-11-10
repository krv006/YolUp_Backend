from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from . import selectors
from .models import Consent, ParentChildLink, TeacherCertificate, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = [
        'username', 'first_name', 'last_name', 'role', 'phone',
        'linked_accounts_count', 'invite_code', 'is_active',
    ]
    list_filter = ['role', 'is_active']
    readonly_fields = ['linked_accounts_display']
    fieldsets = UserAdmin.fieldsets + (
        ('EdTech', {'fields': ('role', 'phone', 'invite_code', 'can_create_tests', 'linked_accounts_display')}),
    )

    @admin.display(description='Shu raqamdagi boshqa akkauntlar')
    def linked_accounts_count(self, obj):
        return selectors.linked_accounts(obj).count() or ''

    @admin.display(description='Shu telefon raqamidagi boshqa akkauntlar')
    def linked_accounts_display(self, obj):
        if obj.pk is None:
            return '—'
        accounts = selectors.linked_accounts(obj)
        if not accounts:
            return "Yo'q"
        return ', '.join(f'{u.username} ({u.get_role_display()})' for u in accounts)


@admin.register(ParentChildLink)
class ParentChildLinkAdmin(admin.ModelAdmin):
    list_display = ['parent', 'student', 'status', 'created_at', 'responded_at']
    list_filter = ['status']


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ['student', 'kind', 'granted', 'granted_by', 'updated_at']
    list_filter = ['kind', 'granted']


@admin.register(TeacherCertificate)
class TeacherCertificateAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'title', 'created_at']
    search_fields = ['teacher__username', 'title']
