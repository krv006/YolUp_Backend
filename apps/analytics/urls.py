from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/summary/', views.DashboardSummaryView.as_view(), name='analytics-dashboard-summary'),
    path('dashboard/trends/', views.DashboardTrendsView.as_view(), name='analytics-dashboard-trends'),
    path('me/', views.MyAnalyticsView.as_view(), name='analytics-me'),
    path('child/<uuid:student_id>/summary/', views.ChildSummaryView.as_view(), name='analytics-child-summary'),
    path('child/<uuid:student_id>/rank/', views.ChildRankView.as_view(), name='analytics-child-rank'),
    path('children/summary/', views.ChildrenSummaryView.as_view(), name='analytics-children-summary'),
    path('me/trends/', views.MyTrendsView.as_view(), name='analytics-me-trends'),
]
