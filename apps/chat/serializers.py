from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from . import presence, selectors
from .models import ChatRoom, Message, RoomRead


def _preview_text(message: Message) -> str:
    """Xabarning qisqa matni (ro'yxat, javob va qadalgan panel uchun): matn yo'q bo'lsa fayl nomi."""
    return (message.text or message.file_name or '')[:200]


def _sender_name(user) -> str:
    return user.get_full_name() or user.username


def reply_snippet(message: Message | None):
    if message is None:
        return None
    gone = message.deleted_at is not None
    return {
        'id': str(message.id),
        'sender_name': _sender_name(message.sender),
        'text': '' if gone else _preview_text(message),
        'message_type': message.message_type,
        'is_deleted': gone,
    }


class MessageSerializer(serializers.ModelSerializer):
    """Xabar. `context`: `viewer` (kim ko'ryapti — reaksiyadagi `reacted` uchun) va `peer_read_at`
    (boshqa a'zolar eng oxirgi o'qigan vaqt — o'z xabarimdagi `status` uchun). Berilmasa (WebSocket tarqatish) —
    `status='sent'` va `reacted=false`."""

    sender = UserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    assignment = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'room', 'sender', 'text', 'file_url', 'created_at',
            'kind', 'system_key', 'system_params',
            'message_type', 'reply_to', 'client_message_id', 'status', 'edited_at', 'forwarded_from_name',
            'file_name', 'file_type', 'file_size', 'page_count', 'duration', 'waveform',
            'reactions', 'assignment',
        ]
        read_only_fields = ['room', 'sender']

    def get_file_url(self, obj) -> str | None:
        if not obj.file:
            return None
        return f'/api/v1/chat/files/{obj.id}/'

    def get_reply_to(self, obj):
        return reply_snippet(obj.reply_to)

    def get_status(self, obj) -> str:
        peer = self.context.get('peer_read_at')
        if peer is not None and obj.created_at <= peer:
            return 'read'
        return 'sent'

    def get_reactions(self, obj) -> list:
        viewer = self.context.get('viewer')
        counts: dict = {}
        mine: set = set()
        for reaction in obj.reactions.all():
            counts[reaction.emoji] = counts.get(reaction.emoji, 0) + 1
            if viewer is not None and reaction.user_id == viewer.id:
                mine.add(reaction.emoji)
        return [{'emoji': e, 'count': c, 'reacted': e in mine} for e, c in counts.items()]

    def get_assignment(self, obj):
        assignment = obj.assignment
        if assignment is None:
            return None
        from apps.homework.models import Submission
        from apps.lessons.models import Enrollment

        return {
            'id': str(assignment.id), 'title': assignment.title, 'due_at': assignment.due_at,
            'submitted_count': Submission.objects.filter(assignment=assignment).values('student').distinct().count(),
            'total_count': Enrollment.objects.filter(
                course_id=assignment.course_id, status=Enrollment.Status.APPROVED,
            ).count(),
        }


class ChatRoomSerializer(serializers.ModelSerializer):
    """Chat ro'yxati qatori — Telegram uslubidagi list uchun hamma narsa bitta joyda."""

    title = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    first_unread_message_id = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    live_lesson = serializers.SerializerMethodField()
    is_pinned = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()
    pinned_message = serializers.SerializerMethodField()
    online_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'kind', 'course', 'direct_status', 'image', 'announcement_only',
            'title', 'last_message', 'unread', 'unread_count', 'first_unread_message_id',
            'other_user', 'live_lesson', 'is_pinned', 'is_muted', 'pinned_message', 'online_count', 'updated_at',
        ]
        read_only_fields = ['image']

    def _my_read(self, obj):
        reads = getattr(obj, 'my_reads', None)
        if reads is None:
            reads = RoomRead.objects.filter(room=obj, user=self.context['request'].user)[:1]
        return next(iter(reads), None)

    def get_live_lesson(self, obj):
        """Kurs guruhida hozir jonli (LIVE) dars bo'lsa — "qo'shilish" tugmasi
        uchun kerakli maydonlar (Telegram guruh video chat chizig'i uslubi)."""
        if obj.kind != ChatRoom.Kind.COURSE or not obj.course_id:
            return None
        from apps.lessons.models import Lesson
        lesson = obj.course.lessons.filter(status=Lesson.Status.LIVE).first()
        if lesson is None:
            return None
        return {'id': str(lesson.id), 'title': lesson.title or lesson.course.title, 'room_name': lesson.room_name}

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
        if cached is not None:
            msg = cached[0] if cached else None
        else:
            msg = obj.messages.filter(deleted_at__isnull=True).order_by('-created_at').first()
        if not msg:
            return None
        data = {
            'id': str(msg.id),
            'text': _preview_text(msg)[:80],
            'message_type': msg.message_type,
            'sender': msg.sender.first_name or msg.sender.username,
            'created_at': msg.created_at,
        }
        if msg.file:
            data['file_url'] = f'/api/v1/chat/files/{msg.id}/'
        return data

    def _unread_qs(self, obj):
        user = self.context['request'].user
        read = self._my_read(obj)
        qs = obj.messages.exclude(sender=user).filter(deleted_at__isnull=True).exclude(hides__user=user)
        if read:
            qs = qs.filter(created_at__gt=read.last_read_at)
        return qs

    def _unread_info(self, obj) -> tuple:
        """(soni, birinchi o'qilmagan xabar id'si) — bir xona uchun bir marta hisoblanadi; xabar bo'lmasa
        ikkinchi so'rov yuborilmaydi."""
        cache = self.__dict__.setdefault('_unread_cache', {})
        if obj.pk not in cache:
            qs = self._unread_qs(obj)
            count = qs.count()
            first = qs.order_by('created_at').values_list('id', flat=True).first() if count else None
            cache[obj.pk] = (count, str(first) if first else None)
        return cache[obj.pk]

    def get_unread(self, obj) -> int:
        return self._unread_info(obj)[0]

    def get_unread_count(self, obj) -> int:
        return self._unread_info(obj)[0]

    def get_first_unread_message_id(self, obj):
        return self._unread_info(obj)[1]

    def get_is_pinned(self, obj) -> bool:
        read = self._my_read(obj)
        return bool(read and read.is_pinned)

    def get_is_muted(self, obj) -> bool:
        read = self._my_read(obj)
        if not read or not read.muted:
            return False
        return read.muted_until is None or read.muted_until > timezone.now()

    def get_pinned_message(self, obj):
        message = obj.pinned_message
        if message is None or message.deleted_at is not None:
            return None
        return {
            'id': str(message.id), 'sender_name': _sender_name(message.sender),
            'text': _preview_text(message), 'message_type': message.message_type,
        }

    def get_online_count(self, obj) -> int:
        return len(presence.online_ids(selectors.member_ids(obj)))


def member_row(user, online: set, request=None) -> dict:
    """A'zolar ro'yxati qatori (guruh ma'lumotlari ekrani)."""
    avatar = None
    if user.avatar:
        avatar = request.build_absolute_uri(user.avatar.url) if request else user.avatar.url
    return {
        'id': str(user.id), 'name': _sender_name(user), 'role': user.role,
        'is_online': str(user.id) in online, 'avatar_url': avatar,
    }
