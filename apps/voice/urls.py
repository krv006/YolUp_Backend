from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('', views.VoiceRoomViewSet, basename='voice-room')

urlpatterns = router.urls
