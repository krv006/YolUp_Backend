from django.urls import path

from . import views

urlpatterns = [
    path('tickets/', views.TicketListCreateView.as_view(), name='support-tickets'),
    path('tickets/<uuid:pk>/', views.TicketDetailView.as_view(), name='support-ticket'),
    path('tickets/<uuid:pk>/reply/', views.TicketReplyView.as_view(), name='support-ticket-reply'),
    path('tickets/<uuid:pk>/close/', views.TicketCloseView.as_view(), name='support-ticket-close'),
]
