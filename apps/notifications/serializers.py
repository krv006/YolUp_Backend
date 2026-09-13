from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import Notification, NotificationRecipient


class NotificationSerializer(serializers.ModelSerializer):
    """Xabarning o'zi — sender + matn (inbox va WS push uchun ham ishlatiladi)."""

    sender = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'sender', 'description', 'target_type', 'kind', 'link_type', 'link_id', 'created_at']


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
