from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import ChatRoom, Message


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'room', 'sender', 'text', 'file_url', 'created_at',
            'kind', 'system_key', 'system_params',
        ]
        read_only_fields = ['room', 'sender']

    def get_file_url(self, obj) -> str | None:
        if not obj.file:
            return None
        return f'/api/v1/chat/files/{obj.id}/'


class ChatRoomSerializer(serializers.ModelSerializer):
    """Chat ro'yxati qatori — Telegram uslubidagi list uchun hamma narsa bitta joyda."""

    title = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    live_lesson = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'kind', 'course', 'direct_status', 'image',
            'title', 'last_message', 'unread', 'other_user', 'live_lesson', 'updated_at',
        ]
        read_only_fields = ['image']

    def get_live_lesson(self, obj):
        """Kurs guruhida hozir jonli (LIVE) dars bo'lsa — "qo'shilish" tugmasi
        uchun kerakli maydonlar (Telegram guruh video chat chizig'i uslubi)."""
        if obj.kind != ChatRoom.Kind.COURSE or not obj.course_id:
            return None
        from apps.lessons.models import Lesson
        lesson = obj.course.lessons.filter(status=Lesson.Status.LIVE).first()
        if lesson is None:
            return None
        return {'id': str(lesson.id), 'title': lesson.course.title, 'room_name': lesson.room_name}

    def get_title(self, obj) -> str:
        return obj.title_for(self.context['request'].user)

    def get_other_user(self, obj):
        if obj.kind != ChatRoom.Kind.DIRECT:
            return None
        user = self.context['request'].user
        other = obj.teacher if user.id == obj.student_id else obj.student
        return UserSerializer(other).data if other else None

    def get_last_message(self, obj):
        # view'da prefetch qilingan bo'lsa ro'yxatdan olamiz (N+1 oldini olish)
        cached = getattr(obj, 'last_message_list', None)
        msg = cached[0] if cached else obj.messages.order_by('-created_at').first()
        if not msg:
            return None
        data = {
            'text': msg.text[:80],
            'sender': msg.sender.first_name or msg.sender.username,
            'created_at': msg.created_at,
        }
        if msg.file:
            data['file_url'] = f'/api/v1/chat/files/{msg.id}/'
        return data

    def get_unread(self, obj) -> int:
        user = self.context['request'].user
        read = next((r for r in getattr(obj, 'my_reads', [])), None)
        qs = obj.messages.exclude(sender=user)
        if read:
            qs = qs.filter(created_at__gt=read.last_read_at)
        return qs.count()
