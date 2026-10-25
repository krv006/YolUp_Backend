from django.urls import path

from . import views

urlpatterns = [
    path('teacher/', views.TeacherDashboardView.as_view(), name='dashboard-teacher'),
    path('activity/', views.ActivityView.as_view(), name='dashboard-activity'),
]
