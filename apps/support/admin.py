from django.contrib import admin

from .models import FaqItem, HelpVideo, SupportMessage, SupportTicket


class MessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'updated_at')
    list_filter = ('status',)
    inlines = [MessageInline]


@admin.register(HelpVideo)
class HelpVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'role', 'order', 'is_active')


@admin.register(FaqItem)
class FaqItemAdmin(admin.ModelAdmin):
    list_display = ('question', 'role', 'order', 'is_active')
