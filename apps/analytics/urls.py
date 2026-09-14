from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/summary/', views.DashboardSummaryView.as_view(), name='analytics-dashboard-summary'),
    path('dashboard/trends/', views.DashboardTrendsView.as_view(), name='analytics-dashboard-trends'),
    path('me/', views.MyAnalyticsView.as_view(), name='analytics-me'),
]
