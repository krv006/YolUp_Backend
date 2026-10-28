from django.urls import path

from . import views

urlpatterns = [
    path('', views.ExamListCreateView.as_view(), name='exam-list-create'),
    path('templates/', views.TemplateListCreateView.as_view(), name='exam-templates'),
    path('templates/<uuid:pk>/', views.TemplateDeleteView.as_view(), name='exam-template-delete'),
    path('<uuid:pk>/', views.ExamDetailView.as_view(), name='exam-detail'),
    path('<uuid:pk>/reminder/', views.ExamReminderView.as_view(), name='exam-reminder'),
    path('<uuid:pk>/current/', views.ExamCurrentView.as_view(), name='exam-current'),
    path('<uuid:pk>/answers/', views.ExamAnswersView.as_view(), name='exam-answers'),
    path('<uuid:pk>/next-section/', views.ExamNextSectionView.as_view(), name='exam-next-section'),
    path('<uuid:pk>/focus/', views.ExamFocusView.as_view(), name='exam-focus'),
    path('<uuid:pk>/finish/', views.ExamFinishView.as_view(), name='exam-finish'),
    path('<uuid:pk>/results/', views.ExamResultsView.as_view(), name='exam-results'),
    path('<uuid:pk>/share-results/', views.ExamShareResultsView.as_view(), name='exam-share-results'),
    path('<uuid:pk>/results/<uuid:student_id>/', views.ExamResultDetailView.as_view(), name='exam-result-detail'),
    path('<uuid:pk>/results/<uuid:student_id>/writing-ai/', views.ExamWritingAiView.as_view(), name='exam-writing-ai'),
    path('<uuid:pk>/results/<uuid:student_id>/manual/', views.ExamManualScoreView.as_view(), name='exam-manual-score'),
]
