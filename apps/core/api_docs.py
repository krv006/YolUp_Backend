"""API hujjati (`/api/docs/`, `/api/schema/`) kimga ochiq.

Prodda sukut bo'yicha YOPIQ: butun API xaritasi hamma uchun ochiq bo'lmasin (2026-10-29 audit). Xodim (admin) `/admin/`
orqali kirgach ochiladi; hamma uchun ochiq qoldirish kerak bo'lsa (masalan test server) — `.env` da `API_DOCS_PUBLIC=1`.
Sozlama so'rov paytida o'qiladi (testlarda `override_settings` ishlaydi).
"""
from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


class DocsAccess(BasePermission):
    def has_permission(self, request, view):
        return bool(settings.API_DOCS_PUBLIC or (request.user and request.user.is_authenticated and request.user.is_staff))


_access = {'permission_classes': [DocsAccess], 'authentication_classes': [SessionAuthentication]}

schema_view = SpectacularAPIView.as_view(**_access)
swagger_view = SpectacularSwaggerView.as_view(url_name='schema', **_access)
