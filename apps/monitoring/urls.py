from django.urls import path

from . import views

urlpatterns = [
    path('current/', views.ResourceCurrentView.as_view(), name='monitoring-current'),
    path('history/', views.ResourceHistoryView.as_view(), name='monitoring-history'),
]
