from django.contrib import admin

from .models import VoiceRoom, VoiceRoomJoinRequest, VoiceRoomParticipant


class VoiceRoomParticipantInline(admin.TabularInline):
    model = VoiceRoomParticipant
    extra = 0


class VoiceRoomJoinRequestInline(admin.TabularInline):
    model = VoiceRoomJoinRequest
    extra = 0


@admin.register(VoiceRoom)
class VoiceRoomAdmin(admin.ModelAdmin):
    list_display = ['course', 'created_by', 'access_mode', 'status', 'scheduled_at', 'created_at']
    list_filter = ['status', 'access_mode']
    search_fields = ['course__title', 'created_by__username']
    inlines = [VoiceRoomJoinRequestInline, VoiceRoomParticipantInline]
