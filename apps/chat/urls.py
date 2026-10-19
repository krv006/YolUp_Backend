from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('rooms', views.ChatRoomViewSet, basename='chat-room')

urlpatterns = [
    path('files/<uuid:message_id>/', views.ChatFileView.as_view(), name='chat-file'),
    path('attachments/<uuid:attachment_id>/', views.ChatAttachmentView.as_view(), name='chat-attachment'),
    path('messages/forward/', views.MessageForwardView.as_view(), name='chat-message-forward'),
    path('messages/bulk-delete/', views.MessageBulkDeleteView.as_view(), name='chat-message-bulk-delete'),
    path('messages/<uuid:pk>/', views.MessageDetailView.as_view(), name='chat-message'),
    path('messages/<uuid:pk>/reactions/', views.MessageReactionView.as_view(), name='chat-message-reactions'),
    *router.urls,
]
