from django.urls import path

from . import views

urlpatterns = [
    path('videos/', views.HelpVideoListView.as_view(), name='help-videos'),
    path('faq/', views.FaqListView.as_view(), name='help-faq'),
]
