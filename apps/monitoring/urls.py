from django.urls import path

from . import views

urlpatterns = [
    path('current/', views.ResourceCurrentView.as_view(), name='monitoring-current'),
    path('client-health/', views.ClientHealthSummaryView.as_view(), name='monitoring-client-health'),
    path('history/', views.ResourceHistoryView.as_view(), name='monitoring-history'),
]
