"""Chat views — yupqa qatlam: HTTP <-> chat services/selectors."""
import json
import re
from urllib.parse import quote

from django.db.models import Prefetch
from django.http import FileResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RequirePerm

from . import attachments, selectors, services
from .models import ChatRoom, Message, RoomRead
from .serializers import ChatRoomSerializer, MessageSerializer

DEFAULT_PAGE = 30
MAX_PAGE = 100


def _waveform(raw):
    """Multipart'da to'lqin JSON matn sifatida keladi: "[3,7,12]"."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return []
    return raw


class ChatRoomViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChatRoomSerializer

    def get_permissions(self):
        return [RequirePerm('chat.use')()]

    def get_queryset(self):
        user = self.request.user
        qs = selectors.rooms_for(user)
        if self.action == 'list':
            hidden = selectors.hidden_filter(user).values('room_id')
            qs = qs.exclude(pk__in=hidden)
        return qs.select_related('course', 'pinned_message', 'pinned_message__sender').prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.objects.filter(deleted_at__isnull=True).select_related('sender').order_by('-created_at')[:1],
                to_attr='last_message_list',
            ),
            Prefetch('reads', queryset=RoomRead.objects.filter(user=user), to_attr='my_reads'),
        )

    def _room_response(self, pk, http_status=status.HTTP_200_OK):
        room = self.get_queryset().get(pk=pk)
        return Response(self.get_serializer(room).data, status=http_status)

    def _message_context(self, request, room):
        return {
            'request': request, 'viewer': request.user,
            'peer_read_at': services.peer_read_at(room, request.user),
        }

    @action(detail=True)
    def messages(self, request, pk=None):
        """Xabarlar. Polling: `?after=<ISO vaqt>` — faqat yangilari. Eski xabarlarni yuklash:
        `?before=<xabar id>&limit=30` (yoki faqat `?limit=`) -> {"items": [...], "has_more": bool}.
        Odatiy holda xonani o'qilgan deb belgilaydi (`?mark_read=0` — belgilamaydi)."""
        room = self.get_object()
        if not selectors.can_read(request.user, room):
            self.permission_denied(request)
        qs = selectors.visible_messages(room, request.user)
        params = request.query_params
        after, before, limit = params.get('after'), params.get('before'), params.get('limit')
        paginated = bool(before or limit)
        if after:
            qs = qs.filter(created_at__gt=after)
            items = list(qs)
            has_more = False
        elif paginated:
            try:
                size = max(1, min(int(limit or DEFAULT_PAGE), MAX_PAGE))
            except ValueError:
                raise ValidationError({'limit': _("Son bo'lishi kerak.")}) from None
            if before:
                try:
                    anchor = Message.objects.get(pk=before, room=room)
                except (Message.DoesNotExist, *services.BAD_ID):
                    raise ValidationError({'before': _('Xabar bu chatda topilmadi.')}) from None
                qs = qs.filter(created_at__lt=anchor.created_at)
            page = list(qs.order_by('-created_at')[:size + 1])
            has_more = len(page) > size
            items = sorted(page[:size], key=lambda m: m.created_at)
        else:
            items = sorted(qs.order_by('-created_at')[:100], key=lambda m: m.created_at)
            has_more = False
        if params.get('mark_read') != '0':
            services.mark_read(user=request.user, room=room)
        data = MessageSerializer(items, many=True, context=self._message_context(request, room)).data
        if paginated and not after:
            return Response({'items': data, 'has_more': has_more})
        return Response(data)

    @action(detail=True, url_path='messages/search')
    def search(self, request, pk=None):
        """Xabarlar ichidan qidirish: {"total": n, "items": [{id, text, created_at}]} (yangilari birinchi)."""
        return Response(services.search_messages(user=request.user, room_id=pk, q=request.query_params.get('q')))

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Xabar yuborish — JSON yoki multipart. Maydonlar: `text`, `file`, `reply_to_id`, `client_message_id`,
        ovozli xabar uchun `message_type=voice` + `duration` (+ `waveform`)."""
        data = request.data
        message, created = services.send_message_ex(
            user=request.user, room_id=pk, text=data.get('text'),
            reply_to_id=data.get('reply_to_id'), client_message_id=data.get('client_message_id'),
            upload=request.FILES.get('file'), message_type=str(data.get('message_type') or ''),
            duration=data.get('duration'), waveform=_waveform(data.get('waveform')),
        )
        room = message.room
        payload = MessageSerializer(message, context=self._message_context(request, room)).data
        return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Xonani `last_message_id` gacha (bo'lmasa hammasini) o'qilgan deb belgilaydi."""
        return Response(services.read_room(
            user=request.user, room_id=pk, last_message_id=request.data.get('last_message_id'),
        ))

    @action(detail=True, methods=['post', 'delete'])
    def pin(self, request, pk=None):
        """Chat tepasiga xabar qadash (POST {message_id}) / qadashni olish (DELETE)."""
        if request.method == 'DELETE':
            services.unpin_message(user=request.user, room_id=pk)
        else:
            services.pin_message(user=request.user, room_id=pk, message_id=request.data.get('message_id'))
        return self._room_response(pk)

    @action(detail=True, methods=['post', 'delete'], url_path='pin-room')
    def pin_room(self, request, pk=None):
        """Suhbatni ro'yxat tepasiga qadash / qadashni olish — faqat o'zim uchun."""
        services.set_room_pinned(user=request.user, room_id=pk, pinned=request.method == 'POST')
        return self._room_response(pk)

    @action(detail=True, methods=['post', 'delete'])
    def mute(self, request, pk=None):
        """Ovozsiz qilish (POST {"until": null | ISO vaqt}) / ovozni yoqish (DELETE) — faqat o'zim uchun."""
        services.set_room_muted(
            user=request.user, room_id=pk, muted=request.method == 'POST', until=request.data.get('until'),
        )
        return self._room_response(pk)

    @action(detail=True, methods=['delete'])
    def leave(self, request, pk=None):
        """Suhbatni ro'yxatdan o'chirish (yangi xabar kelsa qaytadi). Kurs a'zoligiga ta'sir qilmaydi."""
        services.hide_room(user=request.user, room_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def forward(self, request, pk=None):
        """Xabarlarni shu chatga uzatish: {"message_ids": [...]}."""
        created = services.forward_messages(
            user=request.user, room_id=pk, message_ids=request.data.get('message_ids'),
        )
        room = created[0].room
        data = MessageSerializer(created, many=True, context=self._message_context(request, room)).data
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True)
    def members(self, request, pk=None):
        """A'zolar ro'yxati va onlayn holati (guruh ma'lumotlari ekrani)."""
        return Response(services.room_members(user=request.user, room_id=pk, request=request))

    def partial_update(self, request, pk=None):
        """Guruh sozlamasi: {"announcement_only": bool} — faqat kurs o'qituvchisi."""
        if 'announcement_only' not in request.data:
            raise ValidationError({'announcement_only': _('Maydon kerak.')})
        value = request.data.get('announcement_only')
        flag = value if isinstance(value, bool) else str(value).lower() in ('1', 'true', 'yes')
        services.set_announcement_only(teacher=request.user, room_id=pk, value=flag)
        return self._room_response(pk)

    @action(detail=False, methods=['post'], url_path='direct/request')
    def direct_request(self, request):
        """O'quvchi -> o'qituvchi: direct chat so'rovi (teacher = id yoki username)."""
        room = services.request_direct(
            student=request.user, teacher_ref=request.data.get('teacher'), request=request,
        )
        return Response(
            ChatRoomSerializer(room, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='direct/respond')
    def direct_respond(self, request):
        """O'qituvchi: accept yoki block."""
        room = services.respond_direct(
            teacher=request.user,
            room_id=request.data.get('room_id'),
            action=request.data.get('action'),
            request=request,
        )
        return Response(ChatRoomSerializer(room, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='image')
    def set_image(self, request, pk=None):
        """Guruh (kurs) chat rasmini o'rnatadi — faqat kurs o'qituvchisi."""
        room = services.set_group_image(
            teacher=request.user, room_id=pk, image=request.FILES.get('image'), request=request,
        )
        return Response(ChatRoomSerializer(room, context={'request': request}).data)

    @action(detail=False)
    def teachers(self, request):
        """O'quvchining o'qituvchilari — yangi direct so'rov yuborish ro'yxati uchun."""
        from apps.accounts.models import User
        from apps.accounts.serializers import UserSerializer
        from apps.lessons.models import Enrollment

        teacher_ids = Enrollment.objects.filter(
            student=request.user, status=Enrollment.Status.APPROVED,
        ).values('course__teacher_id')
        teachers = User.objects.filter(pk__in=teacher_ids)
        existing = {
            r.teacher_id: r for r in
            ChatRoom.objects.filter(kind=ChatRoom.Kind.DIRECT, student=request.user)
        }
        data = []
        for t in teachers:
            room = existing.get(t.id)
            data.append({
                **UserSerializer(t).data,
                'direct_status': room.direct_status if room else None,
                'room_id': str(room.id) if room else None,
            })
        return Response(data)


class MessageDetailView(APIView):
    """PATCH — tahrirlash (faqat o'z xabari); DELETE `?scope=me|everyone` — o'chirish."""

    permission_classes = [RequirePerm('chat.use')]

    def patch(self, request, pk):
        message = services.edit_message(user=request.user, message_id=pk, text=request.data.get('text'))
        return Response(MessageSerializer(message, context={'request': request, 'viewer': request.user}).data)

    def delete(self, request, pk):
        services.delete_messages(user=request.user, ids=[pk], scope=request.query_params.get('scope', 'me'))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageBulkDeleteView(APIView):
    permission_classes = [RequirePerm('chat.use')]

    def post(self, request):
        ids = request.data.get('ids')
        if not isinstance(ids, list):
            raise ValidationError({'ids': _("Ro'yxat kerak.")})
        count = services.delete_messages(user=request.user, ids=ids, scope=str(request.data.get('scope') or 'me'))
        return Response({'deleted': count})


class MessageReactionView(APIView):
    """Reaksiya qo'shish; takror bosilsa olib tashlanadi."""

    permission_classes = [RequirePerm('chat.use')]

    def post(self, request, pk):
        reactions = services.toggle_reaction(user=request.user, message_id=pk, emoji=request.data.get('emoji'))
        return Response({'reactions': reactions})


def _content_disposition(kind: str, name: str) -> str:
    ascii_name = re.sub(r'[^A-Za-z0-9._-]+', '_', name) or 'fayl'
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"


class ChatFileView(APIView):
    """Chat xabariga biriktirilgan faylni himoyalangan holatda beradi (audio uchun Range qo'llab-quvvatlanadi)."""

    permission_classes = [RequirePerm('chat.use')]

    def get(self, request, message_id):
        try:
            msg = Message.objects.select_related('room').get(pk=message_id)
        except (Message.DoesNotExist, *services.BAD_ID):
            raise NotFound(_('Xabar topilmadi.'))
        if not selectors.can_read(request.user, msg.room):
            raise PermissionDenied(_('Ruxsat yo\'q.'))
        if not msg.file or msg.deleted_at is not None or msg.hides.filter(user=request.user).exists():
            raise NotFound(_('Fayl yo\'q.'))
        # eski xabarlarda tur saqlanmagan edi — avvalgidek PDF deb beriladi
        content_type = msg.file_type or 'application/pdf'
        name = msg.file_name or msg.file.name.split('/')[-1]
        disposition = _content_disposition('inline' if content_type in attachments.INLINE_TYPES else 'attachment', name)
        response = self._ranged(request, msg, content_type) or FileResponse(msg.file.open('rb'), content_type=content_type)
        response['Content-Disposition'] = disposition
        response['Cache-Control'] = 'no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Accept-Ranges'] = 'bytes'
        return response

    @staticmethod
    def _ranged(request, msg, content_type):
        match = re.match(r'bytes=(\d*)-(\d*)$', request.headers.get('Range', ''))
        size = msg.file.size
        if not match or not size or match.groups() == ('', ''):
            return None
        first, last = match.groups()
        if first == '':
            start, end = max(size - int(last), 0), size - 1
        else:
            start, end = int(first), int(last) if last else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            response = HttpResponse(status=416)
            response['Content-Range'] = f'bytes */{size}'
            return response
        with msg.file.open('rb') as handle:
            handle.seek(start)
            chunk = handle.read(end - start + 1)
        response = HttpResponse(chunk, status=206, content_type=content_type)
        response['Content-Range'] = f'bytes {start}-{end}/{size}'
        return response
