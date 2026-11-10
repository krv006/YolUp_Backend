from django.urls import path

from . import views

# /api/v1/admin/... — admin uchun tekshiruv endpointlari
urlpatterns = [
    path('users/<uuid:pk>/test-access/', views.AdminTestAccessView.as_view(), name='admin-test-access'),
    path('certificates/', views.AdminCertificateListView.as_view(), name='admin-certificate-list'),
    path('certificates/<uuid:pk>/verify/', views.AdminCertificateVerifyView.as_view(), name='admin-certificate-verify'),
    path('certificates/<uuid:pk>/reject/', views.AdminCertificateRejectView.as_view(), name='admin-certificate-reject'),
]
