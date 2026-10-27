"""Chat views — yupqa qatlam: HTTP <-> chat services/selectors."""
import json
import re
from urllib.parse import quote

from django.db.models import Prefetch, Q
from django.http import FileResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import RequirePerm
from apps.lessons.models import Lesson

from . import attachments, selectors, services
from .models import ChatRoom, Message, MessageAttachment, PinnedMessage, RoomRead
from .serializers import ChatRoomSerializer, MessageSerializer

DEFAULT_PAGE = 30
MAX_PAGE = 100


def _mentions(data):
    """`mentions`: JSON'da ro'yxat, multipart'da takroriy maydon yoki JSON matn."""
    if hasattr(data, 'getlist'):
        values = data.getlist('mentions')
        return values if len(values) != 1 else values[0]
    return data.get('mentions')


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
        return qs.select_related('course').prefetch_related(
            Prefetch(
                'pins',
                queryset=PinnedMessage.objects.filter(message__deleted_at__isnull=True)
                .select_related('message', 'message__sender').order_by('-created_at'),
                to_attr='pin_list',
            ),
            Prefetch(
                'messages',
                queryset=Message.objects.filter(deleted_at__isnull=True).select_related('sender').order_by('-created_at')[:1],
                to_attr='last_message_list',
            ),
            Prefetch('reads', queryset=RoomRead.objects.filter(user=user), to_attr='my_reads'),
            Prefetch('course__lessons', queryset=Lesson.objects.filter(status=Lesson.Status.LIVE), to_attr='live_lessons'),
        )

    def _room_response(self, pk, http_status=status.HTTP_200_OK):
        room = self.get_queryset().get(pk=pk)
        return Response(self.get_serializer(room).data, status=http_status)

    def _message_context(self, request, room):
        return {
            'request': request, 'viewer': request.user, 'room': room,
            'peer_read_at': services.peer_read_at(room, request.user),
            'peer_delivered_at': services.peer_delivered_at(room, request.user),
        }

    @action(detail=True, methods=['get', 'post'])
    def messages(self, request, pk=None):
        """GET — xabarlar; POST — xabar yuborish (`send/` bilan bir xil, qo'shimcha: `type=homework` + `assignment_id`, `files[]`).
        Xabarlar. Polling: `?after=<ISO vaqt>` — faqat yangilari. Eski xabarlarni yuklash:
        `?before=<xabar id>&limit=30` (yoki faqat `?limit=`) -> {"items": [...], "has_more": bool}.
        Odatiy holda xonani o'qilgan deb belgilaydi (`?mark_read=0` — belgilamaydi)."""
        if request.method == 'POST':
            return self._post_message(request, pk)
        room = self.get_object()
        if not selectors.can_read(request.user, room):
            self.permission_denied(request)
        qs = selectors.visible_messages(room, request.user)
        params = request.query_params
        if params.get('around'):
            return self._messages_around(request, room, qs, params)
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

    def _messages_around(self, request, room, qs, params):
        """`?around=<xabar id>&limit=30` — shu xabar va uning atrofidagilar (qidiruv natijasiga o'tish uchun).
        `{"items": [...eskidan yangiga...], "has_more_before": bool, "has_more_after": bool}`. Xonani o'qilgan deb belgilamaydi."""
        try:
            half = max(1, min(int(params.get('limit') or DEFAULT_PAGE), MAX_PAGE) // 2)
        except ValueError:
            raise ValidationError({'limit': _("Son bo'lishi kerak.")}) from None
        try:
            target = qs.get(pk=params['around'])
        except (Message.DoesNotExist, *services.BAD_ID):
            raise ValidationError({'around': _('Xabar bu chatda topilmadi.')}) from None
        older = list(qs.filter(created_at__lt=target.created_at).order_by('-created_at')[:half + 1])
        newer = list(qs.filter(created_at__gt=target.created_at).order_by('created_at')[:half + 1])
        items = [*reversed(older[:half]), target, *newer[:half]]
        return Response({
            'items': MessageSerializer(items, many=True, context=self._message_context(request, room)).data,
            'has_more_before': len(older) > half, 'has_more_after': len(newer) > half,
        })

    @action(detail=True, url_path='messages/search')
    def search(self, request, pk=None):
        """Xabarlar ichidan qidirish: `?q=&limit=&cursor=` -> `{total, items:[{id, message_id, cursor, text, created_at,
        sender_name}], next_cursor}` (yangilari birinchi)."""
        params = request.query_params
        return Response(services.search_messages(
            user=request.user, room_id=pk, q=params.get('q'), limit=params.get('limit'), cursor=params.get('cursor'),
        ))

    @action(detail=True)
    def attachments(self, request, pk=None):
        """Guruh ma'lumotlaridagi "Fayllar" / "Media": `?kind=file|media&page=` (sahifalangan).
        `media` — rasm va videolar, `file` — hujjatlar (ovozli xabarlar kirmaydi). Yangilari birinchi."""
        room = self.get_object()
        if not selectors.can_read(request.user, room):
            self.permission_denied(request)
        kind = request.query_params.get('kind', 'file')
        if kind not in ('file', 'media'):
            raise ValidationError({'kind': _("file yoki media bo'lishi kerak.")})
        rows = (
            MessageAttachment.objects.filter(message__room=room, message__deleted_at__isnull=True)
            .exclude(message__hides__user=request.user).exclude(message__message_type=Message.Type.VOICE)
            .select_related('message', 'message__sender').order_by('-message__created_at', 'order')
        )
        media = Q(mime__startswith='image/') | Q(mime__startswith='video/')
        rows = rows.filter(media) if kind == 'media' else rows.exclude(media)
        params = request.query_params
        if params.get('cursor') or params.get('limit'):
            return self._attachments_by_cursor(rows, params)
        page = self.paginate_queryset(rows)
        data = [_attachment_row(row) for row in page]
        return self.get_paginated_response(data)

    def _attachments_by_cursor(self, rows, params):
        """`?limit=&cursor=` — cursor (oldingi sahifadagi oxirgi biriktirma id'si) bilan: `{count, results, next_cursor}`."""
        try:
            size = max(1, min(int(params.get('limit') or DEFAULT_PAGE), MAX_PAGE))
        except ValueError:
            raise ValidationError({'limit': _("Son bo'lishi kerak.")}) from None
        total = rows.count()
        cursor = params.get('cursor')
        if cursor:
            try:
                anchor = rows.get(pk=cursor)
            except (MessageAttachment.DoesNotExist, *services.BAD_ID):
                raise ValidationError({'cursor': _('Biriktirma topilmadi.')}) from None
            older = Q(message__created_at__lt=anchor.message.created_at)
            same_message_later = Q(message=anchor.message, order__gt=anchor.order)
            rows = rows.filter(older | same_message_later)
        page = list(rows[:size + 1])
        more = len(page) > size
        page = page[:size]
        return Response({
            'count': total, 'results': [_attachment_row(row) for row in page],
            'next_cursor': str(page[-1].id) if more and page else None,
        })

    def _send(self, request, pk):
        data = request.data
        uploads = [*request.FILES.getlist('files'), *request.FILES.getlist('files[]')]
        message, created = services.send_message_ex(
            user=request.user, room_id=pk, text=data.get('text'),
            reply_to_id=data.get('reply_to_id'), client_message_id=data.get('client_message_id'),
            upload=request.FILES.get('file'), uploads=uploads, message_type=str(data.get('message_type') or ''),
            duration=data.get('duration'), waveform=_waveform(data.get('waveform')), mentions=_mentions(data),
        )
        payload = MessageSerializer(message, context=self._message_context(request, message.room)).data
        return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def _post_message(self, request, pk):
        if str(request.data.get('type') or '') == 'homework':
            message = services.post_homework_message(
                user=request.user, room_id=pk, assignment_id=request.data.get('assignment_id'),
            )
            payload = MessageSerializer(message, context=self._message_context(request, message.room)).data
            return Response(payload, status=status.HTTP_201_CREATED)
        return self._send(request, pk)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Xabar yuborish — JSON yoki multipart. Maydonlar: `text`, `file` yoki `files[]` (10 tagacha), `reply_to_id`,
        `client_message_id`, `mentions`, ovozli xabar uchun `message_type=voice` + `duration` (+ `waveform`)."""
        return self._send(request, pk)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Xonani `last_message_id` gacha (bo'lmasa hammasini) o'qilgan deb belgilaydi."""
        return Response(services.read_room(
            user=request.user, room_id=pk,
            last_message_id=request.data.get('last_read_message_id') or request.data.get('last_message_id'),
        ))

    @action(detail=True, methods=['post', 'delete'])
    def pin(self, request, pk=None):
        """Chat tepasiga xabar qadash (POST {message_id}) / qadashni olish (DELETE)."""
        if request.method == 'DELETE':
            services.unpin_message(user=request.user, room_id=pk)
        else:
            services.pin_message(user=request.user, room_id=pk, message_id=request.data.get('message_id'))
        return self._room_response(pk)

    @action(detail=True, methods=['get', 'post'], url_path='pinned')
    def pinned(self, request, pk=None):
        """Qadalgan xabarlar: GET — ro'yxat; POST `{message_id}` — qo'shish (bir nechtasi mumkin) -> yangilangan ro'yxat."""
        if request.method == 'POST':
            services.pin_message(user=request.user, room_id=pk, message_id=request.data.get('message_id'))
        return Response(services.list_pins(user=request.user, room_id=pk))

    @action(detail=True, methods=['delete'], url_path=r'pinned/(?P<message_id>[^/.]+)')
    def unpin(self, request, pk=None, message_id=None):
        """Bitta xabarning qadalganini olish -> qolgan qadalganlar ro'yxati."""
        services.unpin_message(user=request.user, room_id=pk, message_id=message_id)
        return Response(services.list_pins(user=request.user, room_id=pk))

    @action(detail=True, methods=['post'], url_path='voice')
    def voice(self, request, pk=None):
        """Ovozli xabar: multipart `file` (audio/webm, audio/mp4, m4a, ogg…), `duration_ms` (1 soniya … 5 daqiqa, ≤10 MB),
        ixtiyoriy `waveform`, `reply_to_id`, `client_message_id`. `send/` dagi `message_type=voice` bilan bir xil."""
        data = request.data
        try:
            millis = float(data.get('duration_ms'))
        except (TypeError, ValueError):
            millis = float(data.get('duration') or 0) * 1000
        message, created = services.send_message_ex(
            user=request.user, room_id=pk, text=data.get('text'), reply_to_id=data.get('reply_to_id'),
            client_message_id=data.get('client_message_id'), upload=request.FILES.get('file'),
            message_type='voice', duration=-(-int(millis) // 1000) if millis > 0 else 0,
            waveform=_waveform(data.get('waveform')),
        )
        payload = MessageSerializer(message, context=self._message_context(request, message.room)).data
        return Response(payload, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

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
        return Response(services.room_members(
            user=request.user, room_id=pk, request=request, query=request.query_params.get('query', ''),
        ))

    def partial_update(self, request, pk=None):
        """Guruh sozlamasi: {"announcement_mode": bool} (eski nomi `announcement_only`) — faqat kurs o'qituvchisi."""
        key = 'announcement_mode' if 'announcement_mode' in request.data else 'announcement_only'
        if key not in request.data:
            raise ValidationError({'announcement_mode': _('Maydon kerak.')})
        value = request.data.get(key)
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
        ids = request.data.get('message_ids', request.data.get('ids'))
        if not isinstance(ids, list):
            raise ValidationError({'ids': _("Ro'yxat kerak.")})
        count = services.delete_messages(user=request.user, ids=ids, scope=str(request.data.get('scope') or 'me'))
        return Response({'deleted': count})


class MessageReactionView(APIView):
    """Reaksiya qo'shish; takror bosilsa olib tashlanadi."""

    permission_classes = [RequirePerm('chat.use')]

    def post(self, request, pk):
        """Reaksiya qo'yadi. Takroriy POST xato emas va bekor qilmaydi (idempotent). Eski xatti-harakat (bosib
        olib tashlash) kerak bo'lsa `{"toggle": true}` yuboring."""
        toggle = str(request.data.get('toggle', '')).lower() in ('1', 'true', 'yes')
        reactions = services.toggle_reaction(
            user=request.user, message_id=pk, emoji=request.data.get('emoji'), mode='toggle' if toggle else 'add',
        )
        return Response({'reactions': reactions})

    def delete(self, request, pk):
        """Reaksiyani olib tashlaydi (yo'q bo'lsa ham xato emas). `emoji` — tanada yoki `?emoji=`."""
        emoji = request.data.get('emoji') or request.query_params.get('emoji')
        reactions = services.toggle_reaction(user=request.user, message_id=pk, emoji=emoji, mode='remove')
        return Response({'reactions': reactions})


class MessageForwardView(APIView):
    """Xabarlarni bir yoki bir nechta chatga uzatish: `{message_ids, target_room_ids}` -> yaratilgan xabarlar ro'yxati."""

    permission_classes = [RequirePerm('chat.use')]

    def post(self, request):
        created = services.forward_to_rooms(
            user=request.user, message_ids=request.data.get('message_ids'),
            room_ids=request.data.get('target_room_ids'),
        )
        data = [
            MessageSerializer(m, context={'request': request, 'viewer': request.user, 'room': m.room}).data
            for m in created
        ]
        return Response(data, status=status.HTTP_201_CREATED)


def _content_disposition(kind: str, name: str) -> str:
    ascii_name = re.sub(r'[^A-Za-z0-9._-]+', '_', name) or 'fayl'
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"


def _attachment_row(row) -> dict:
    message = row.message
    url = f'/api/v1/chat/attachments/{row.id}/'
    is_image = row.mime.startswith('image/')
    return {
        'id': str(row.id), 'message_id': str(message.id), 'name': row.name, 'mime_type': row.mime, 'mime': row.mime, 'size': row.size,
        'url': url, 'thumbnail_url': f'{url}?thumb=1' if is_image else None, 'page_count': row.page_count,
        'created_at': message.created_at,
        'sender': {'id': str(message.sender_id), 'name': message.sender.get_full_name() or message.sender.username},
    }


def _thumbnail(field_file):
    """Rasm eskizi (320 px, JPEG) — Media ro'yxati va xabar ichida tez ochilishi uchun."""
    from io import BytesIO

    from PIL import Image

    with field_file.open('rb') as handle:
        image = Image.open(handle)
        image.thumbnail((320, 320))
        buffer = BytesIO()
        image.convert('RGB').save(buffer, format='JPEG', quality=80)
    return buffer.getvalue()


MAX_RANGE_BYTES = 4 * 1024 * 1024


def _ranged(request, field_file, content_type):
    match = re.match(r'bytes=(\d*)-(\d*)$', request.headers.get('Range', ''))
    size = field_file.size
    if not match or not size or match.groups() == ('', ''):
        return None
    first, last = match.groups()
    if first == '':
        start, end = max(size - int(last), 0), size - 1
    else:
        start, end = int(first), int(last) if last else size - 1
    end = min(end, size - 1, start + MAX_RANGE_BYTES - 1)  # katta videoda bir so'rov xotirani to'ldirmasin
    if start > end or start >= size:
        response = HttpResponse(status=416)
        response['Content-Range'] = f'bytes */{size}'
        return response
    with field_file.open('rb') as handle:
        handle.seek(start)
        chunk = handle.read(end - start + 1)
    response = HttpResponse(chunk, status=206, content_type=content_type)
    response['Content-Range'] = f'bytes {start}-{end}/{size}'
    return response


def _serve(request, message, field_file, content_type, name):
    """Faylni himoyalangan holda beradi (audio uchun Range, rasm uchun `?thumb=1` eskiz)."""
    if not selectors.can_read(request.user, message.room):
        raise PermissionDenied(_('Ruxsat yo\'q.'))
    if not field_file or message.deleted_at is not None or message.hides.filter(user=request.user).exists():
        raise NotFound(_('Fayl yo\'q.'))
    if request.query_params.get('thumb') and content_type.startswith('image/'):
        try:
            response = HttpResponse(_thumbnail(field_file), content_type='image/jpeg')
            disposition = _content_disposition('inline', name)
        except Exception:  # noqa: BLE001 — eskiz chiqmasa asl rasm beriladi
            response = None
    else:
        response = None
    if response is None:
        disposition = _content_disposition('inline' if content_type in attachments.INLINE_TYPES else 'attachment', name)
        response = _ranged(request, field_file, content_type) or FileResponse(field_file.open('rb'), content_type=content_type)
    response['Content-Disposition'] = disposition
    response['Cache-Control'] = 'no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Accept-Ranges'] = 'bytes'
    return response


class ChatFileView(APIView):
    """Xabarning (birinchi) faylini beradi — eski manzil. Hamma biriktirmalar: `attachments/{id}/`."""

    permission_classes = [RequirePerm('chat.use')]

    def get(self, request, message_id):
        try:
            msg = Message.objects.select_related('room').get(pk=message_id)
        except (Message.DoesNotExist, *services.BAD_ID):
            raise NotFound(_('Xabar topilmadi.'))
        # eski xabarlarda tur saqlanmagan edi — avvalgidek PDF deb beriladi
        content_type = msg.file_type or 'application/pdf'
        return _serve(request, msg, msg.file, content_type, msg.file_name or msg.file.name.split('/')[-1])


class ChatAttachmentView(APIView):
    """Bitta biriktirmani beradi (`GET attachments/{id}/`, rasm uchun `?thumb=1`)."""

    permission_classes = [RequirePerm('chat.use')]

    def get(self, request, attachment_id):
        try:
            row = MessageAttachment.objects.select_related('message', 'message__room').get(pk=attachment_id)
        except (MessageAttachment.DoesNotExist, *services.BAD_ID):
            raise NotFound(_('Fayl topilmadi.'))
        return _serve(request, row.message, row.file, row.mime or 'application/octet-stream', row.name or row.file.name.split('/')[-1])
