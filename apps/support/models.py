"""Yordam markazi: murojaatlar (qo'llab-quvvatlash), video qo'llanmalar va tez-tez beriladigan savollar (admin boshqaradi)."""
from django.conf import settings
from django.db.models import (
    CASCADE, BooleanField, CharField, ForeignKey, PositiveIntegerField, PositiveSmallIntegerField, TextChoices, TextField, URLField,
)

from apps.core.models import TimeStampedUUIDModel


class SupportTicket(TimeStampedUUIDModel):
    class Status(TextChoices):
        OPEN = 'open', 'Ochiq'
        ANSWERED = 'answered', 'Javob berildi'
        CLOSED = 'closed', 'Yopilgan'

    user = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='support_tickets')
    subject = CharField(max_length=200)
    status = CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.subject} · {self.user_id}'


class SupportMessage(TimeStampedUUIDModel):
    ticket = ForeignKey(SupportTicket, CASCADE, related_name='messages')
    author = ForeignKey(settings.AUTH_USER_MODEL, CASCADE, related_name='support_messages')
    body = TextField()
    from_staff = BooleanField(default=False)

    class Meta:
        ordering = ['created_at']


class HelpVideo(TimeStampedUUIDModel):
    title = CharField(max_length=200)
    url = URLField(max_length=500)
    duration_seconds = PositiveIntegerField(default=0)
    role = CharField(max_length=16, blank=True, default='', help_text="Bo'sh = hamma uchun; teacher/student/parent")
    order = PositiveSmallIntegerField(default=0)
    is_active = BooleanField(default=True)

    class Meta:
        ordering = ['order', 'created_at']


class FaqItem(TimeStampedUUIDModel):
    question = CharField(max_length=300)
    answer = TextField()
    role = CharField(max_length=16, blank=True, default='', help_text="Bo'sh = hamma uchun; teacher/student/parent")
    order = PositiveSmallIntegerField(default=0)
    is_active = BooleanField(default=True)

    class Meta:
        ordering = ['order', 'created_at']
