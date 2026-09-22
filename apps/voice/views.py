"""Voice views — yupqa qatlam: HTTP <-> service/selector."""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import RequirePerm

from . import selectors, services
from .serializers import (
    VoiceRoomCreateSerializer,
    VoiceRoomJoinRequestSerializer,
    VoiceRoomSerializer,
)


_UUID_RE = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


class VoiceRoomViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    # DRF router'ning standart pk regex'i ([^/.]+) har qanday satrni qabul
    # qiladi — noto'g'ri UUID (masalan "undefined") view'gacha yetib borib,
    # `.get(pk=...)` `django.core.exceptions.ValidationError` bilan
    # (`ValueError` EMAS!) yiqilib, ushlanmagan 500'ga aylanardi (production'da
    # 2026-09-22 topilgan). Qolgan app'lar `path('<uuid:pk>/', ...)` orqali
    # buni URL darajasida 404'ga aylantiradi — shu yerda ham xuddi shunday.
    lookup_value_regex = _UUID_RE

    def get_permissions(self):
        perm = 'voice.create' if self.action == 'create' else 'voice.join'
        return [RequirePerm(perm)()]

    def get_serializer_class(self):
        if self.action == 'create':
            return VoiceRoomCreateSerializer
        return VoiceRoomSerializer

    def get_queryset(self):
        return selectors.rooms_for(self.request.user, course_id=self.request.query_params.get('course'))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        room = services.create_room(
            user=request.user, course=data['course'], title=data.get('title', ''),
            access_mode=data.get('access_mode', 'open'), scheduled_at=data.get('scheduled_at'),
        )
        return Response(VoiceRoomSerializer(room).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        payload = services.join_room(user=request.user, room_id=pk, request=request)
        return Response(payload)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        updated = services.leave_room(user=request.user, room_id=pk, request=request)
        return Response({'updated': updated})

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        room = services.close_room(user=request.user, room_id=pk, request=request)
        return Response(VoiceRoomSerializer(room).data)

    @action(detail=True, methods=['post'], url_path='request-join')
    def request_join(self, request, pk=None):
        join_request = services.request_join(user=request.user, room_id=pk, request=request)
        return Response(VoiceRoomJoinRequestSerializer(join_request).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def requests(self, request, pk=None):
        qs = services.list_join_requests(user=request.user, room_id=pk)
        return Response(VoiceRoomJoinRequestSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path=fr'requests/(?P<request_id>{_UUID_RE})/approve')
    def approve_request(self, request, pk=None, request_id=None):
        join_request = services.approve_request(user=request.user, room_id=pk, request_id=request_id, request=request)
        return Response(VoiceRoomJoinRequestSerializer(join_request).data)

    @action(detail=True, methods=['post'], url_path=fr'requests/(?P<request_id>{_UUID_RE})/deny')
    def deny_request(self, request, pk=None, request_id=None):
        join_request = services.deny_request(user=request.user, room_id=pk, request_id=request_id, request=request)
        return Response(VoiceRoomJoinRequestSerializer(join_request).data)
