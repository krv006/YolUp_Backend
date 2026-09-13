"""Bildirishnoma views — yupqa qatlam: HTTP <-> service/selector."""
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import RequirePerm

from . import selectors, services
from .models import Notification
from .serializers import (
    InboxItemSerializer,
    NotificationSerializer,
    PushSubscribeSerializer,
    PushUnsubscribeSerializer,
    RecipientStatusSerializer,
    SendNotificationSerializer,
    SentNotificationSerializer,
)


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """GET /notifications/ — mening inbox'im. Admin uchun qo'shimcha action'lar."""

    def get_permissions(self):
        if self.action in ('send', 'sent', 'recipients'):
            return [RequirePerm('notification.send')()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'send':
            return SendNotificationSerializer
        if self.action == 'sent':
            return SentNotificationSerializer
        if self.action == 'recipients':
            return RecipientStatusSerializer
        return InboxItemSerializer

    def get_queryset(self):
        if self.action == 'sent':
            return selectors.sent_by(self.request.user)
        return selectors.inbox_for(self.request.user)

    @action(detail=False, methods=['post'])
    def send(self, request):
        """Admin: bitta userga (`target_type=user` + `user_id`) yoki hammaga (`target_type=all`)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification = services.send_notification(
            sender=request.user, request=request, **serializer.validated_data,
        )
        return Response(NotificationSerializer(notification).data, status=status.HTTP_201_CREATED)

    @action(detail=False)
    def sent(self, request):
        """Admin: o'zi yuborganlari — har birida o'qildi/jami soni."""
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @action(detail=True)
    def recipients(self, request, pk=None):
        """Admin: aniq shu xabarni kim o'qidi, kim o'qimadi."""
        notification = get_object_or_404(Notification, pk=pk, sender=request.user)
        qs = notification.recipients.select_related('user').order_by('user__first_name')
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        services.mark_read(user=request.user, notification_id=pk)
        return Response({'ok': True})

    @action(detail=False, url_path='unread-count')
    def unread_count(self, request):
        return Response({'count': selectors.unread_count(request.user)})

    @action(detail=False, url_path='push/vapid-key')
    def vapid_key(self, request):
        """Frontend `PushManager.subscribe()` chaqirishdan oldin shu ochiq
        kalitni so'raydi (`applicationServerKey`)."""
        return Response({'public_key': settings.VAPID_PUBLIC_KEY})

    @action(detail=False, methods=['post'], url_path='push/subscribe')
    def push_subscribe(self, request):
        """Brauzer `subscription.toJSON()` natijasini shu yerga yuboradi —
        {"endpoint": "...", "keys": {"p256dh": "...", "auth": "..."}}."""
        serializer = PushSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.save_push_subscription(
            user=request.user,
            endpoint=serializer.validated_data['endpoint'],
            p256dh=serializer.validated_data['keys']['p256dh'],
            auth=serializer.validated_data['keys']['auth'],
        )
        return Response({'ok': True}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='push/unsubscribe')
    def push_unsubscribe(self, request):
        serializer = PushUnsubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        removed = services.remove_push_subscription(
            user=request.user, endpoint=serializer.validated_data['endpoint'],
        )
        return Response({'removed': removed})
