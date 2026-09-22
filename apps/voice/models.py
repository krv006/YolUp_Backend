"""Ovozli suhbat (guruh ichidagi voice chat) modellari.

Oqim:
  - Guruh a'zosi (o'qituvchi yoki o'quvchi) xona ochadi — ixtiyoriy
    boshlanish vaqti (`scheduled_at`) bilan yoki darhol.
  - Bir guruhda bir vaqtning o'zida faqat BITTA faol (scheduled/live)
    xona bo'lishi mumkin (`unique_active_voice_room_per_course`).
  - `open`: guruh a'zosi to'g'ridan-to'g'ri kiradi. `invite_only`: so'rov
    yuboradi, xona egasi (yoki kurs o'qituvchisi) tasdiqlaydi/rad etadi.
  - Xona bo'shab qolganda (oxirgi ishtirokchi `leave` chaqirganda)
    avtomatik yopiladi — `services._maybe_close_if_empty`. Tarmoq uzilib
    `leave` chaqirilmagan holatlar uchun xavfsizlik to'ri —
    `close_stale_voice_rooms` buyrug'i (cron).
"""
from django.conf import settings
from django.db.models import (
    CASCADE,
    CharField,
    DateTimeField,
    ForeignKey,
    Q,
    TextChoices,
    UniqueConstraint,
)

from apps.core.models import TimeStampedUUIDModel


class VoiceRoom(TimeStampedUUIDModel):
    class AccessMode(TextChoices):
        OPEN = 'open', 'Ochiq'
        INVITE_ONLY = 'invite_only', "So'rov asosida"

    class Status(TextChoices):
        SCHEDULED = 'scheduled', 'Rejalashtirilgan'
        LIVE = 'live', 'Jonli'
        ENDED = 'ended', 'Tugagan'

    course = ForeignKey('lessons.Course', CASCADE, related_name='voice_rooms')
    created_by = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='+')
    title = CharField(max_length=200, blank=True)
    access_mode = CharField(max_length=12, choices=AccessMode.choices, default=AccessMode.OPEN)
    status = CharField(max_length=10, choices=Status.choices, default=Status.LIVE, db_index=True)
    # Ixtiyoriy — bo'sh bo'lsa xona darhol "live" holatida yaratiladi.
    scheduled_at = DateTimeField(null=True, blank=True)
    started_at = DateTimeField(null=True, blank=True)
    ended_at = DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            UniqueConstraint(
                fields=['course'],
                condition=Q(status__in=['scheduled', 'live']),
                name='unique_active_voice_room_per_course',
            ),
        ]

    @property
    def room_name(self) -> str:
        return f'voice-{self.id}'

    def __str__(self):
        return f'{self.course.title} · {self.get_status_display()}'


class VoiceRoomJoinRequest(TimeStampedUUIDModel):
    class Status(TextChoices):
        PENDING = 'pending', 'Kutilmoqda'
        APPROVED = 'approved', 'Tasdiqlangan'
        DENIED = 'denied', 'Rad etilgan'

    room = ForeignKey(VoiceRoom, CASCADE, related_name='join_requests')
    user = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='+')
    status = CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ['created_at']
        constraints = [
            UniqueConstraint(fields=['room', 'user'], name='unique_voice_join_request'),
        ]

    def __str__(self):
        return f'{self.user.username} · {self.room} · {self.get_status_display()}'


class VoiceRoomParticipant(TimeStampedUUIDModel):
    """Bitta "ichkarida bo'lish" sessiyasi — `left_at IS NULL` = hozir ichkarida."""

    room = ForeignKey(VoiceRoom, CASCADE, related_name='participants')
    user = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='+')
    left_at = DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        state = 'ichkarida' if self.left_at is None else 'chiqqan'
        return f'{self.user.username} · {self.room} · {state}'
