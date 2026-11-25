from django.urls import path
from rest_framework.routers import DefaultRouter

from . import club_views, schedule, views

router = DefaultRouter()
router.register('courses', views.CourseViewSet, basename='course')
router.register('lessons', views.LessonViewSet, basename='lesson')
router.register('attendance', views.AttendanceViewSet, basename='attendance')
router.register('clubs', club_views.ClubViewSet, basename='club')

urlpatterns = [path('schedule/', schedule.ScheduleView.as_view(), name='schedule'), *router.urls]
