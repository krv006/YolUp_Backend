from django.urls import path

from . import views

urlpatterns = [
    path('explain/', views.StudentAiExplainView.as_view(), name='student-ai-explain'),
    path('practice/', views.StudentAiPracticeView.as_view(), name='student-ai-practice'),
]
