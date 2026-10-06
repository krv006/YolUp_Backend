from django.urls import path

from . import views

urlpatterns = [
    path('', views.ExamListCreateView.as_view(), name='exam-list-create'),
    path('templates/', views.TemplateListCreateView.as_view(), name='exam-templates'),
    path('templates/<uuid:pk>/', views.TemplateDeleteView.as_view(), name='exam-template-delete'),
    path('<uuid:pk>/', views.ExamDetailView.as_view(), name='exam-detail'),
    path('<uuid:pk>/current/', views.ExamCurrentView.as_view(), name='exam-current'),
    path('<uuid:pk>/answers/', views.ExamAnswersView.as_view(), name='exam-answers'),
    path('<uuid:pk>/finish/', views.ExamFinishView.as_view(), name='exam-finish'),
    path('<uuid:pk>/results/', views.ExamResultsView.as_view(), name='exam-results'),
    path('<uuid:pk>/results/<uuid:student_id>/', views.ExamResultDetailView.as_view(), name='exam-result-detail'),
    path('<uuid:pk>/results/<uuid:student_id>/manual/', views.ExamManualScoreView.as_view(), name='exam-manual-score'),
]
