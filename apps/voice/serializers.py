from django.utils import timezone
from rest_framework import serializers

from .models import VoiceRoom, VoiceRoomJoinRequest


class VoiceRoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceRoom
        fields = ['course', 'title', 'access_mode', 'scheduled_at']

    def validate_scheduled_at(self, value):
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError("Boshlanish vaqti kelajakda bo'lishi kerak.")
        return value


class VoiceRoomSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    participant_count = serializers.SerializerMethodField()
    # Xona egasi: `host_id` — foydalanuvchi id'si; `host_identity` — LiveKit'dagi ishtirokchi `identity`si (`user-<id>`),
    # shu bilan `participant.identity` ni to'g'ridan-to'g'ri solishtirish mumkin ("Xona egasi" belgisi uchun)
    host_id = serializers.SerializerMethodField()
    host_identity = serializers.SerializerMethodField()

    class Meta:
        model = VoiceRoom
        fields = [
            'id', 'course', 'created_by', 'created_by_name', 'title', 'access_mode', 'status',
            'scheduled_at', 'started_at', 'ended_at', 'participant_count', 'created_at', 'host_id', 'host_identity',
        ]

    def get_host_id(self, obj) -> str:
        return str(obj.created_by_id)

    def get_host_identity(self, obj) -> str:
        return f'user-{obj.created_by_id}'

    def get_participant_count(self, obj) -> int:
        return obj.participants.filter(left_at__isnull=True).count()


class VoiceRoomJoinRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = VoiceRoomJoinRequest
        fields = ['id', 'room', 'user', 'user_name', 'status', 'created_at']
