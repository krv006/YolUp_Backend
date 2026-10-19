"""Chat modellari — Telegram uslubi (FRD: EduTech.docx).

Qoidalar:
  - Har kurs = bitta guruh chat. Guruhni faqat o'qituvchi (kurs yaratish orqali) ochadi.
  - Direct chat FAQAT o'qituvchi ↔ o'quvchi. O'quvchilar orasida direct yo'q.
  - O'quvchi o'qituvchiga 1 martalik so'rov yuboradi; qabul qilingach chat ochiladi.
    O'qituvchi block qilsa, o'quvchi qayta so'rov yuborishi kerak.
"""
from django.db.models import (
    CASCADE,
    SET_NULL,
    BigIntegerField,
    BooleanField,
    CharField,
    DateTimeField,
    FileField,
    ForeignKey,
    ImageField,
    Index,
    JSONField,
    ManyToManyField,
    OneToOneField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    Q,
    TextChoices,
    TextField,
    UniqueConstraint,
    UUIDField,
)

from apps.core.models import TimeStampedUUIDModel


class ChatRoom(TimeStampedUUIDModel):
    class Kind(TextChoices):
        COURSE = 'course', 'Kurs guruhi'
        DIRECT = 'direct', 'Shaxsiy'

    class DirectStatus(TextChoices):
        PENDING = 'pending', "So'rov kutilmoqda"
        ACTIVE = 'active', 'Ochiq'
        BLOCKED = 'blocked', 'Bloklangan'

    kind = CharField(max_length=8, choices=Kind.choices, db_index=True)
    # kind=COURSE bo'lsa:
    course = OneToOneField(
        'lessons.Course', CASCADE, null=True, blank=True, related_name='chat_room',
    )
    # kind=DIRECT bo'lsa:
    teacher = ForeignKey(
        'accounts.User', CASCADE, null=True, blank=True, related_name='direct_chats_teacher',
    )
    student = ForeignKey(
        'accounts.User', CASCADE, null=True, blank=True, related_name='direct_chats_student',
    )
    direct_status = CharField(
        max_length=8, choices=DirectStatus.choices, default=DirectStatus.ACTIVE, db_index=True,
    )
    # kind=COURSE guruh rasmi — faqat o'qituvchi o'zgartira oladi
    image = ImageField(upload_to='group_images/', null=True, blank=True)
    # E'lon rejimi: true bo'lsa guruhga faqat o'qituvchi yozadi
    announcement_only = BooleanField(default=False)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            UniqueConstraint(
                fields=['teacher', 'student'],
                condition=Q(kind='direct'),
                name='unique_direct_teacher_student',
            ),
        ]

    def title_for(self, user) -> str:
        if self.kind == self.Kind.COURSE:
            return self.course.title
        other = self.teacher if user.id == self.student_id else self.student
        return (other.get_full_name() or other.username) if other else 'Chat'

    def __str__(self):
        if self.kind == self.Kind.COURSE:
            return f'guruh: {self.course.title}'
        return f'direct: {self.teacher} ↔ {self.student} [{self.direct_status}]'


class Message(TimeStampedUUIDModel):
    class Kind(TextChoices):
        USER = 'user', 'Foydalanuvchi'
        SYSTEM = 'system', 'Tizim'

    room = ForeignKey('chat.ChatRoom', CASCADE, related_name='messages')
    sender = ForeignKey('accounts.User', CASCADE, related_name='chat_messages')
    text = TextField()
    file = FileField(upload_to='chat_files/', blank=True)
    # Tizim tomonidan avtomatik yoziladigan xabarlar (masalan "video yozuvi
    # tayyor") uchun: `text` hamon bitta (hozircha o'zbekcha) render sifatida
    # to'ldiriladi (eski client/bildirishnoma preview'lari uchun fallback),
    # lekin `kind='system'` bo'lganda frontend `system_key`+`system_params`
    # orqali xabarni HAR BIR ko'ruvchining o'z tilida qayta render qilishi
    # mumkin — guruh chatida turli tilli o'quvchilar bo'lgani uchun bitta
    # saqlangan matn hammaga bir xil tilda ko'rinishi to'g'ri emas
    # (2026-09-06).
    kind = CharField(max_length=16, choices=Kind.choices, default=Kind.USER)
    system_key = CharField(max_length=64, blank=True, default='')
    system_params = JSONField(blank=True, default=dict)

    class Type(TextChoices):
        TEXT = 'text', 'Matn'
        FILE = 'file', 'Fayl'
        IMAGE = 'image', 'Rasm'
        VOICE = 'voice', 'Ovozli xabar'
        ASSIGNMENT = 'assignment', 'Vazifa kartasi'

    # Ko'rinishi (kind = kim yozgan: foydalanuvchi/tizim; message_type = ichi nima)
    message_type = CharField(max_length=12, choices=Type.choices, default=Type.TEXT)
    # Javob berilgan xabar (matn ichiga yozilgan `↪` hack'i o'rniga)
    reply_to = ForeignKey('self', SET_NULL, null=True, blank=True, related_name='replies')
    # Qayta yuborishda (internet uzilsa) xabar ikki marta tushmasligi uchun client UUID'si
    client_message_id = CharField(max_length=64, blank=True, default='')
    # Fayl haqida (hajm va sahifalar soni dizaynda ko'rsatiladi)
    file_name = CharField(max_length=255, blank=True, default='')
    file_type = CharField(max_length=100, blank=True, default='')
    file_size = BigIntegerField(default=0)
    page_count = PositiveIntegerField(null=True, blank=True)
    # Ovozli xabar
    duration = PositiveIntegerField(null=True, blank=True)
    waveform = JSONField(blank=True, default=list)
    # Tahrirlash / hamma uchun o'chirish / uzatish
    edited_at = DateTimeField(null=True, blank=True)
    deleted_at = DateTimeField(null=True, blank=True)
    forwarded_from_name = CharField(max_length=150, blank=True, default='')
    # Uzatilgan xabarning ASL manbasi (zanjir bo'ylab ham o'zgarmaydi): `forwarded_from` obyekti shundan yig'iladi
    forwarded_from_message = UUIDField(null=True, blank=True)
    forwarded_from_author = ForeignKey('accounts.User', SET_NULL, null=True, blank=True, related_name='+')
    forwarded_from_room = UUIDField(null=True, blank=True)
    # Xabarda @eslatilgan a'zolar (chat a'zolari bo'lishi shart); eslatilganga bildirishnoma boradi
    mentions = ManyToManyField('accounts.User', blank=True, related_name='chat_mentions')
    # Chatdagi vazifa kartasi
    assignment = ForeignKey('homework.Assignment', SET_NULL, null=True, blank=True, related_name='chat_messages')

    class Meta:
        ordering = ['created_at']
        indexes = [Index(fields=['room', 'created_at'])]
        constraints = [
            UniqueConstraint(
                fields=['room', 'sender', 'client_message_id'],
                condition=~Q(client_message_id=''),
                name='unique_message_client_id',
            ),
        ]

    def __str__(self):
        return f'{self.sender.username}: {self.text[:40]}'


class RoomRead(TimeStampedUUIDModel):
    """Har foydalanuvchining xonada oxirgi o'qigan vaqti — unread hisoblash uchun."""

    room = ForeignKey('chat.ChatRoom', CASCADE, related_name='reads')
    user = ForeignKey('accounts.User', CASCADE, related_name='chat_reads')
    last_read_at = DateTimeField()
    # Foydalanuvchining shu suhbatga nisbatan shaxsiy holati (faqat o'zi ko'radi)
    is_pinned = BooleanField(default=False)
    muted = BooleanField(default=False)
    muted_until = DateTimeField(null=True, blank=True)  # muted va bu bo'sh = doim ovozsiz
    hidden_at = DateTimeField(null=True, blank=True)  # "suhbatni o'chirish": yangi xabar kelguncha ro'yxatda yo'q

    class Meta:
        constraints = [
            UniqueConstraint(fields=['room', 'user'], name='unique_room_user_read'),
        ]


class MessageHide(TimeStampedUUIDModel):
    """"Men uchun o'chirish" — xabar faqat shu foydalanuvchiga ko'rinmaydi."""

    message = ForeignKey('chat.Message', CASCADE, related_name='hides')
    user = ForeignKey('accounts.User', CASCADE, related_name='hidden_chat_messages')

    class Meta:
        constraints = [UniqueConstraint(fields=['message', 'user'], name='unique_message_hide')]


class MessageReaction(TimeStampedUUIDModel):
    message = ForeignKey('chat.Message', CASCADE, related_name='reactions')
    user = ForeignKey('accounts.User', CASCADE, related_name='chat_reactions')
    emoji = CharField(max_length=16)

    class Meta:
        constraints = [UniqueConstraint(fields=['message', 'user', 'emoji'], name='unique_message_reaction')]


class PinnedMessage(TimeStampedUUIDModel):
    """Chat tepasidagi qadalgan xabarlar (bir nechta) — hamma a'zoga ko'rinadi. `created_at` = qadalgan payt.
    Guruhda faqat o'qituvchi, direct chatda ikkala tomon qadaydi."""

    room = ForeignKey('chat.ChatRoom', CASCADE, related_name='pins')
    message = ForeignKey('chat.Message', CASCADE, related_name='pins')
    pinned_by = ForeignKey('accounts.User', SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['-created_at']
        constraints = [UniqueConstraint(fields=['room', 'message'], name='unique_room_pinned_message')]


class MessageAttachment(TimeStampedUUIDModel):
    """Xabarga biriktirilgan fayl (bitta xabarda bir nechta bo'lishi mumkin). `Message.file*` maydonlari eski mijozlar
    uchun BIRINCHI biriktirmani aks ettirishda davom etadi."""

    message = ForeignKey('chat.Message', CASCADE, related_name='files')
    file = FileField(upload_to='chat_files/')
    name = CharField(max_length=255, blank=True, default='')
    mime = CharField(max_length=100, blank=True, default='')
    size = BigIntegerField(default=0)
    page_count = PositiveIntegerField(null=True, blank=True)
    order = PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'created_at']
