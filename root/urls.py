from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import HealthView

# Admin panel sarlavhalari
admin.site.site_header = 'Fokus — Boshqaruv paneli'
admin.site.site_title = 'Fokus admin'
admin.site.index_title = "Platforma ma'lumotlari"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', HealthView.as_view(), name='health'),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.lessons.urls')),
    path('api/v1/live/', include('apps.live.urls')),
    path('api/v1/chat/', include('apps.chat.urls')),
    path('api/v1/board/', include('apps.board.urls')),
    path('api/v1/homework/', include('apps.homework.urls')),
    path('api/v1/quizzes/', include('apps.quizzes.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/monitoring/', include('apps.monitoring.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
