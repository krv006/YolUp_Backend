from django.urls import path

from . import views

urlpatterns = [
    path('', views.QuizListCreateView.as_view(), name='quiz-list-create'),
    path('import/', views.QuizImportView.as_view(), name='quiz-import'),
    path('template/', views.QuizTemplateView.as_view(), name='quiz-template'),
    path('<uuid:pk>/', views.QuizDetailView.as_view(), name='quiz-detail'),
    path('<uuid:pk>/attempts/', views.QuizAttemptListCreateView.as_view(), name='quiz-attempts'),
    path('mock-tests/', views.MockTestListCreateView.as_view(), name='mock-test-list-create'),
    path('mock-tests/<uuid:pk>/', views.MockTestDetailView.as_view(), name='mock-test-detail'),
    path('mock-tests/<uuid:pk>/start/', views.MockTestStartView.as_view(), name='mock-test-start'),
    path('mock-tests/<uuid:pk>/attempts/', views.MockTestAttemptListView.as_view(), name='mock-test-attempts'),
    path(
        'mock-tests/<uuid:pk>/attempts/<uuid:attempt_id>/submit/',
        views.MockTestAttemptSubmitView.as_view(), name='mock-test-attempt-submit',
    ),
]
