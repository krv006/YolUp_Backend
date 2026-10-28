from django.urls import path

from . import views

urlpatterns = [
    path('token/', views.RoomTokenView.as_view(), name='room-token'),
    path('leave/', views.RoomLeaveView.as_view(), name='room-leave'),
    path('attention/', views.AttentionView.as_view(), name='room-attention'),
    path('focus/', views.FocusEventView.as_view(), name='room-focus'),
    path('allow-share/', views.AllowShareView.as_view(), name='room-allow-share'),
    path('request-mic/', views.RequestMicView.as_view(), name='room-request-mic'),
    path('mute-all/', views.MuteAllView.as_view(), name='room-mute-all'),
    path('lesson/<uuid:lesson_id>/presence/', views.LessonPresenceView.as_view(), name='lesson-presence'),
    path('lesson/<uuid:lesson_id>/signals/', views.LessonSignalsView.as_view(), name='lesson-signals'),
    path('lesson/<uuid:lesson_id>/mic-request/', views.CancelMicRequestView.as_view(), name='lesson-mic-request-cancel'),
    path('lesson/<uuid:lesson_id>/camera-request/', views.CancelCameraRequestView.as_view(), name='lesson-camera-request-cancel'),
    path('grant-mic/', views.GrantMicView.as_view(), name='room-grant-mic'),
    path('deny-mic/', views.DenyMicView.as_view(), name='room-deny-mic'),
    path('request-camera/', views.RequestCameraView.as_view(), name='room-request-camera'),
    path('grant-camera/', views.GrantCameraView.as_view(), name='room-grant-camera'),
    path('deny-camera/', views.DenyCameraView.as_view(), name='room-deny-camera'),
    path('invite/', views.InviteView.as_view(), name='room-invite'),
    path('ban/', views.BanView.as_view(), name='room-ban'),
    path('unban/', views.UnbanView.as_view(), name='room-unban'),
]
