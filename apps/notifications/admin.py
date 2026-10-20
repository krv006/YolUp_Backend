"""Bildirishnoma admin — CRUD forma emas, maxsus "Yangi xabar yuborish" sahifasi.

Standart Django "Add" formasi bu yerda ATAYLAB o'chirilgan: Notification
modelini to'g'ridan-to'g'ri saqlash NotificationRecipient qatorlarini
yaratmaydi (fan-out faqat services.send_notification()da bo'ladi) — ya'ni
oddiy forma orqali "saqlangan" xabar hech kimga bormay qoladi. Shuning
o'rniga /admin/notifications/notification/send/ sahifasi to'g'ridan-to'g'ri
service qatlamini chaqiradi (sender = tizimga kirgan admin, sanitizatsiya,
qabul qiluvchilarni yaratish, real-time push, audit — hammasi bir joyda).
"""
from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from apps.accounts.models import User

from . import services
from .models import Notification, NotificationRecipient


class SendNotificationForm(forms.Form):
    target_type = forms.ChoiceField(
        choices=[(value, label) for value, label in Notification.Target.choices if value in ('user', 'all')],
        widget=forms.RadioSelect, label='Kimga',
    )
    user = forms.ModelChoiceField(
        queryset=User.objects.order_by('username'), required=False, label='Foydalanuvchi',
        help_text='Faqat "Bitta foydalanuvchi" tanlanganda kerak.',
    )
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 6}), label='Xabar matni')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('target_type') == Notification.Target.USER and not cleaned.get('user'):
            self.add_error('user', "Bitta foydalanuvchiga yuborish uchun uni tanlang.")
        return cleaned


class NotificationRecipientInline(admin.TabularInline):
    model = NotificationRecipient
    extra = 0
    readonly_fields = ['user', 'read_at']
    can_delete = False
    verbose_name_plural = "Qabul qiluvchilar (kim o'qidi)"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Faqat ko'rish/jurnal — yuborish uchun "Yangi xabar yuborish" tugmasi."""

    list_display = ['sender', 'target_type', 'created_at', 'recipient_count', 'read_count']
    list_filter = ['target_type']
    search_fields = ['sender__username', 'description']
    date_hierarchy = 'created_at'
    inlines = [NotificationRecipientInline]
    change_list_template = 'notifications/notification_changelist.html'

    def has_add_permission(self, request):
        return False

    @admin.display(description='Qabul qiluvchilar')
    def recipient_count(self, obj):
        return obj.recipients.count()

    @admin.display(description="O'qildi")
    def read_count(self, obj):
        return obj.recipients.filter(read_at__isnull=False).count()

    def get_urls(self):
        custom = [
            path(
                'send/', self.admin_site.admin_view(self.send_view),
                name='notifications_notification_send',
            ),
        ]
        return custom + super().get_urls()

    def send_view(self, request):
        if not request.user.has_perm('notification.send') and not request.user.is_superuser:
            # RBAC bilan bir xil ruxsat — Jazzmin'dan kirgan admin ham,
            # oddiy Django is_staff ham role='admin' bo'lmasa yubora olmaydi
            from apps.core.permissions import user_has_perm
            if not user_has_perm(request.user, 'notification.send'):
                messages.error(request, "Sizda bildirishnoma yuborish huquqi yo'q.")
                return HttpResponseRedirect(reverse('admin:notifications_notification_changelist'))

        if request.method == 'POST':
            form = SendNotificationForm(request.POST)
            if form.is_valid():
                target_type = form.cleaned_data['target_type']
                user = form.cleaned_data.get('user')
                notification = services.send_notification(
                    sender=request.user,
                    description=form.cleaned_data['description'],
                    target_type=target_type,
                    user_id=str(user.id) if user else None,
                    request=request,
                )
                count = notification.recipients.count()
                messages.success(request, f"Xabar yuborildi — {count} ta qabul qiluvchiga.")
                return HttpResponseRedirect(reverse('admin:notifications_notification_changelist'))
        else:
            form = SendNotificationForm()

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Yangi bildirishnoma yuborish',
            'opts': self.model._meta,
        }
        return render(request, 'notifications/send_notification.html', context)
