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
    forwarded_from = serializers.SerializerMethodField()
    mentions = serializers.SerializerMethodField()
    mentioned_users = serializers.SerializerMethodField()
    attachment = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    my_submission = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'room', 'sender', 'text', 'file_url', 'created_at',
            'kind', 'system_key', 'system_params',
            'message_type', 'reply_to', 'client_message_id', 'status', 'edited_at', 'forwarded_from_name',
            'file_name', 'file_type', 'file_size', 'page_count', 'duration', 'waveform',
            'reactions', 'assignment', 'forwarded_from', 'mentions', 'mentioned_users', 'attachment', 'attachments', 'capabilities',
            'type', 'my_submission',
        ]
        read_only_fields = ['room', 'sender']

    def get_file_url(self, obj) -> str | None:
        if not obj.file:
            return None
        return f'/api/v1/chat/files/{obj.id}/'

    def get_reply_to(self, obj):
        return reply_snippet(obj.reply_to)

    def get_forwarded_from(self, obj):
        """Uzatilgan xabarning asl manbasi (eski xabarlarda faqat ism bo'lishi mumkin)."""
        if not obj.forwarded_from_name and not obj.forwarded_from_message:
            return None
        author = obj.forwarded_from_author
        return {
            'message_id': str(obj.forwarded_from_message) if obj.forwarded_from_message else None,
            'author_id': str(obj.forwarded_from_author_id) if obj.forwarded_from_author_id else None,
            'author_name': (author.get_full_name() or author.username) if author else obj.forwarded_from_name,
            'room_id': str(obj.forwarded_from_room) if obj.forwarded_from_room else None,
        }

    def get_mentions(self, obj) -> list:
        return [str(user.id) for user in obj.mentions.all()]

    def get_mentioned_users(self, obj) -> list:
        return [{'id': str(user.id), 'name': _sender_name(user)} for user in obj.mentions.all()]

    def get_attachment(self, obj):
        """Biriktirilgan fayl bitta obyektda: `{type: voice|image|file, url, name, size, mime, page_count,
        duration_ms, waveform}`. `file_url`/`file_name`/... eski maydonlari ham joyida."""
        if not obj.file:
            return None
        kind = obj.message_type if obj.message_type in (Message.Type.VOICE, Message.Type.IMAGE, Message.Type.VIDEO) else 'file'
        data = {
            'type': kind, 'url': f'/api/v1/chat/files/{obj.id}/', 'name': obj.file_name, 'size': obj.file_size,
            'mime': obj.file_type, 'page_count': obj.page_count,
        }
        if kind == Message.Type.VOICE:
            data['duration_ms'] = (obj.duration or 0) * 1000
            data['waveform'] = obj.waveform or []
        return data

    def get_attachments(self, obj) -> list:
        """Hamma biriktirmalar: `[{id, type, name, mime_type, size, url, thumbnail_url, page_count, (ovoz: duration_ms, waveform)}]`.
        Eski bitta-fayl xabarlari ham shu shaklda (bitta element) chiqadi."""
        rows = list(obj.files.all())
        if not rows:
            if not obj.file:
                return []
            items = [(str(obj.id), obj.file_name or obj.file.name.split('/')[-1], obj.file_type or 'application/pdf',
                      obj.file_size, f'/api/v1/chat/files/{obj.id}/', obj.page_count)]
        else:
            items = [(str(r.id), r.name, r.mime, r.size, f'/api/v1/chat/attachments/{r.id}/', r.page_count) for r in rows]
        result = []
        for index, (ident, name, mime, size, url, pages) in enumerate(items):
            kind = (
                'image' if mime.startswith('image/') else 'video' if mime.startswith('video/')
                else 'voice' if obj.message_type == Message.Type.VOICE else 'file'
            )
            data = {
                'id': ident, 'type': kind, 'name': name, 'mime_type': mime, 'size': size, 'url': url,
                'thumbnail_url': f'{url}?thumb=1' if kind == 'image' else None, 'page_count': pages,
            }
            if kind == 'voice' and index == 0:
                data['duration_ms'] = (obj.duration or 0) * 1000
                data['waveform'] = obj.waveform or []
            result.append(data)
        return result

    def get_type(self, obj) -> str:
        """Frontend uchun yagona tur: `text|file|image|voice|homework|system`."""
        if obj.kind == Message.Kind.SYSTEM:
            return 'system'
        return 'homework' if obj.message_type == Message.Type.ASSIGNMENT else obj.message_type

    def get_my_submission(self, obj):
        """O'quvchi uchun vazifa kartasida: o'zining oxirgi topshirig'i (karta "Topshirildi · sana" ga o'tishi uchun)."""
        viewer = self.context.get('viewer')
        if obj.assignment_id is None or viewer is None or viewer.role != 'student':
            return None
        from apps.homework.models import Submission

        row = Submission.objects.filter(assignment_id=obj.assignment_id, student=viewer).order_by('-created_at').first()
        return {'id': str(row.id), 'created_at': row.created_at, 'status': row.status} if row else None

    def get_capabilities(self, obj):
        viewer = self.context.get('viewer')
        if viewer is None:
            return None
        return selectors.capabilities(viewer, self.context.get('room') or obj.room, obj)

    def get_status(self, obj) -> str:
        peer = self.context.get('peer_read_at')
        if peer is not None and obj.created_at <= peer:
            return 'read'
        delivered = self.context.get('peer_delivered_at')
        if delivered is not None and obj.created_at <= delivered:
            return 'delivered'
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

        lesson = assignment.lesson
        return {
            'id': str(assignment.id), 'title': assignment.title, 'description': assignment.description,
            'due_at': assignment.due_at, 'files_count': 1 if assignment.attachment else 0,
            'lesson_id': str(lesson.id) if lesson else None,
            'lesson_title': (lesson.title or lesson.course.title) if lesson else None,
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
    pinned_messages = serializers.SerializerMethodField()
    last_read_message_id = serializers.SerializerMethodField()
    has_unread_mention = serializers.SerializerMethodField()
    online_count = serializers.SerializerMethodField()
    announcement_mode = serializers.BooleanField(source='announcement_only', read_only=True)
    can_write = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'kind', 'course', 'direct_status', 'image', 'announcement_only', 'announcement_mode', 'can_write', 'capabilities',
            'title', 'last_message', 'unread', 'unread_count', 'first_unread_message_id',
            'other_user', 'live_lesson', 'is_pinned', 'is_muted', 'pinned_message', 'pinned_messages', 'last_read_message_id', 'has_unread_mention',
            'online_count', 'updated_at',
        ]
        read_only_fields = ['image']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Guruh chatida o'z rasmi bo'lmasa — guruhning (kursning) rasmi ko'rinadi
        if not data.get('image') and instance.kind == ChatRoom.Kind.COURSE and instance.course_id and instance.course.avatar:
            request = self.context.get('request')
            url = instance.course.avatar.url
            data['image'] = request.build_absolute_uri(url) if request else url
        return data

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
        live = getattr(obj.course, 'live_lessons', None)  # view'da bitta so'rov bilan oldindan yuklangan
        lesson = (live[0] if live else None) if live is not None else obj.course.lessons.filter(status=Lesson.Status.LIVE).first()
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

    def _pins(self, obj) -> list:
        from .services import pin_dict, pin_rows

        cached = getattr(obj, 'pin_list', None)
        pins = cached if cached is not None else pin_rows(obj)
        return [pin_dict(pin) for pin in pins]

    def get_pinned_messages(self, obj) -> list:
        return self._pins(obj)

    def get_pinned_message(self, obj):
        """Eng oxirgi qadalgan xabar (eski mijozlar uchun; hammasi — `pinned_messages`)."""
        pins = self._pins(obj)
        return pins[0] if pins else None

    def get_last_read_message_id(self, obj):
        read = self._my_read(obj)
        if read is None:
            return None
        last = obj.messages.filter(
            deleted_at__isnull=True, created_at__lte=read.last_read_at,
        ).order_by('-created_at').values_list('id', flat=True).first()
        return str(last) if last else None

    def get_has_unread_mention(self, obj) -> bool:
        return self._unread_qs(obj).filter(mentions=self.context['request'].user).exists()

    def get_can_write(self, obj) -> bool:
        return selectors.can_write(self.context['request'].user, obj)

    def get_capabilities(self, obj) -> dict:
        """Xona darajasidagi huquqlar: yozish, qadash, e'lon rejimini o'zgartirish va boshqalarning xabarini hamma uchun o'chirish."""
        user = self.context['request'].user
        teacher = selectors.is_room_teacher(user, obj)
        return {
            'write': selectors.can_write(user, obj), 'pin': selectors.can_pin(user, obj),
            'announcement': teacher, 'delete': teacher,
        }

    def get_online_count(self, obj) -> int:
        return len(presence.online_ids(selectors.member_ids(obj)))


def member_row(user, online: set, request=None) -> dict:
    """A'zolar ro'yxati qatori (guruh ma'lumotlari ekrani)."""
    avatar = None
    if user.avatar:
        avatar = request.build_absolute_uri(user.avatar.url) if request else user.avatar.url
    return {
        'id': str(user.id), 'name': _sender_name(user), 'username': user.username, 'role': user.role,
        'is_online': str(user.id) in online, 'avatar_url': avatar, 'avatar': avatar,
        'last_seen_at': user.last_seen_at,
    }
