from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import Notification, NotificationRecipient, PushDevice


CATEGORIES = (
    'assignment', 'submission', 'lesson_reminder', 'member_joined', 'mention', 'payment', 'announcement',
)


def category_of(kind: str, link_type: str = '') -> str:
    """Frontend ikonka tanlashi uchun barqaror tur: `kind` ichki va ko'p (yangilari qo'shilaveradi),
    `category` esa doim yuqoridagi 7 tadan biri."""
    kind = kind or ''
    if kind in CATEGORIES:
        return kind
    if kind.startswith(('new_assignment', 'deadline')) or link_type == 'assignment':
        return 'assignment'
    if kind.startswith('homework_') or link_type == 'submission':
        return 'submission'
    if kind.startswith('payment'):
        return 'payment'
    return 'announcement'


CATEGORY_TITLES = {
    'assignment': 'Yangi vazifa', 'submission': 'Vazifa natijasi', 'lesson_reminder': 'Dars eslatmasi',
    'member_joined': "Qo'shilish so'rovi", 'mention': 'Sizni eslatishdi', 'payment': "To'lov", 'announcement': "E'lon",
}
KIND_TITLES = {
    'homework_pending_review': 'Tekshiruv kutmoqda', 'homework_reviewed': 'Yangi baho',
    'homework_resubmit': 'Qayta topshirish', 'homework_reminder': 'Vazifa eslatmasi',
    'ai_quiz_ready': 'AI test tayyor', 'ai_quiz_failed': 'AI test yaratilmadi',
    'lesson_cancelled': 'Dars bekor qilindi', 'exam_scheduled': 'Imtihon belgilandi',
    'teacher_approved': 'Hisob tasdiqlandi', 'teacher_pending_approval': 'Tasdiq kutilmoqda',
    'chat_message': 'Yangi xabar',
    'certificate_verified': 'Sertifikat tasdiqlandi', 'certificate_rejected': 'Sertifikat rad etildi',
    'certificate_pending': 'Sertifikat tekshiruvi', 'recording_ready': 'Dars yozuvi tayyor', 'disk_alert': 'Disk to\'lmoqda',
    'recording_failed': 'Yozuv birlashtirilmadi',
}


def title_of(kind: str, link_type: str = '') -> str:
    """Qisqa sarlavha (ro'yxat kartasi uchun): `kind` bo'yicha, bo'lmasa `category` bo'yicha."""
    return KIND_TITLES.get(kind or '') or CATEGORY_TITLES[category_of(kind, link_type)]


class NotificationSerializer(serializers.ModelSerializer):
    """Xabarning o'zi — sender + matn (inbox va WS push uchun ham ishlatiladi). `title` — qisqa sarlavha,
    `body` — HTML'siz oddiy matn; `description` (HTML) eskicha qoladi."""

    sender = UserSerializer(read_only=True)
    category = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'sender', 'description', 'title', 'body', 'target_type', 'kind', 'category', 'link_type', 'link_id',
            'created_at',
        ]

    def get_category(self, obj) -> str:
        return category_of(obj.kind, obj.link_type)

    def get_title(self, obj) -> str:
        return title_of(obj.kind, obj.link_type)

    def get_body(self, obj) -> str:
        from .services import strip_html

        return strip_html(obj.description or '')


class InboxItemSerializer(serializers.ModelSerializer):
    """Foydalanuvchining inbox qatori — NotificationRecipient asosida."""

    notification = NotificationSerializer(read_only=True)
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = NotificationRecipient
        fields = ['id', 'notification', 'is_read', 'read_at', 'created_at']

    def get_is_read(self, obj) -> bool:
        return obj.read_at is not None


class RecipientStatusSerializer(serializers.ModelSerializer):
    """Admin uchun: aynan kim o'qidi, kim o'qimadi."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = NotificationRecipient
        fields = ['user', 'read_at']


class SentNotificationSerializer(serializers.ModelSerializer):
    """Admin yuborganlar ro'yxati — o'qildi/jami soni bilan."""

    read_count = serializers.SerializerMethodField()
    total_count = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'description', 'target_type', 'created_at', 'read_count', 'total_count']

    def get_read_count(self, obj) -> int:
        return sum(1 for r in obj.recipients.all() if r.read_at is not None)

    def get_total_count(self, obj) -> int:
        return len(obj.recipients.all())


class SendNotificationSerializer(serializers.Serializer):
    description = serializers.CharField()
    target_type = serializers.ChoiceField(choices=Notification.Target.choices)
    user_id = serializers.UUIDField(required=False, allow_null=True)
    # `users` / `parents_of` uchun: bitta so'rovda ko'pchilikka (ko'pi bilan 500)
    user_ids = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=False, max_length=500)
    kind = serializers.CharField(required=False, allow_blank=True, max_length=32, default='')
    link_type = serializers.CharField(required=False, allow_blank=True, max_length=32, default='')
    link_id = serializers.CharField(required=False, allow_blank=True, max_length=64, default='')


class PushSubscribeSerializer(serializers.Serializer):
    """Brauzerning `PushSubscription.toJSON()` shakli."""

    endpoint = serializers.URLField(max_length=500)
    keys = serializers.DictField(child=serializers.CharField())

    def validate_keys(self, value):
        missing = {'p256dh', 'auth'} - set(value)
        if missing:
            raise serializers.ValidationError(f"Kalitlar yetishmayapti: {sorted(missing)}")
        return value


class PushUnsubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=500)


class PushDeviceSerializer(serializers.Serializer):
    """Mobil (FCM) qurilmani ro'yxatga olish — PUSH-BACKEND.md 2.1."""

    token = serializers.CharField(max_length=512)
    platform = serializers.ChoiceField(choices=PushDevice.Platform.choices)
    device_id = serializers.CharField(max_length=128)
    app_version = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')


class PushDeviceRemoveSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=128)
