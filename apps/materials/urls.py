from django.urls import path

from . import views

urlpatterns = [
    path('', views.MaterialListCreateView.as_view(), name='material-list'),
    path('<uuid:pk>/', views.MaterialDetailView.as_view(), name='material-detail'),
    path('<uuid:pk>/file/', views.MaterialFileView.as_view(), name='material-file'),
]
