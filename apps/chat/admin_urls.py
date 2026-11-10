from django.urls import path

from . import views

urlpatterns = [
    path('reports/', views.AdminSpamReportView.as_view(), name='admin-spam-reports'),
    path('reports/<uuid:pk>/', views.AdminSpamReportDetailView.as_view(), name='admin-spam-report'),
    path('reports/<uuid:pk>/resolve/', views.AdminSpamReportActionView.as_view(action='resolve'), name='admin-spam-resolve'),
    path('reports/<uuid:pk>/dismiss/', views.AdminSpamReportActionView.as_view(action='dismiss'), name='admin-spam-dismiss'),
    path('reports/<uuid:pk>/unblock/', views.AdminSpamReportActionView.as_view(action='unblock'), name='admin-spam-unblock'),
]
