from django.urls import path

from . import views

urlpatterns = [
    path('', views.QuizListCreateView.as_view(), name='quiz-list-create'),
    path('import/', views.QuizImportView.as_view(), name='quiz-import'),
    path('import-google-doc/', views.QuizGoogleDocImportView.as_view(), name='quiz-import-google-doc'),
    path('import-google-form/', views.QuizGoogleFormImportView.as_view(), name='quiz-import-google-form'),
    path('template/', views.QuizTemplateView.as_view(), name='quiz-template'),
    path('<uuid:pk>/', views.QuizDetailView.as_view(), name='quiz-detail'),
    path('<uuid:pk>/publish/', views.QuizPublishView.as_view(), name='quiz-publish'),
    path('<uuid:pk>/attempts/', views.QuizAttemptListCreateView.as_view(), name='quiz-attempts'),
]
