from django.urls import path

from . import views

urlpatterns = [
    path('assignments/', views.AssignmentListCreateView.as_view(), name='hw-assignments'),
    path('assignments/ai-stats/', views.AiStatsView.as_view(), name='hw-ai-stats'),
    path('assignments/<uuid:assignment_id>/', views.AssignmentDetailView.as_view(), name='hw-assignment'),
    path('assignments/<uuid:assignment_id>/file/', views.AssignmentFileView.as_view(), name='hw-assignment-file'),
    path('assignments/<uuid:assignment_id>/submit/', views.SubmitView.as_view(), name='hw-submit'),
    path('assignments/<uuid:assignment_id>/board/', views.HomeworkBoardView.as_view(), name='hw-board'),
    path('assignments/<uuid:assignment_id>/board/submit/', views.HomeworkBoardSubmitView.as_view(), name='hw-board-submit'),
    path('submissions/<uuid:submission_id>/', views.SubmissionDetailView.as_view(), name='hw-submission'),
    path('submissions/<uuid:submission_id>/file/', views.SubmissionFileView.as_view(), name='hw-submission-file'),
    path('submissions/<uuid:submission_id>/recheck/', views.RecheckView.as_view(), name='hw-recheck'),
    path('submissions/<uuid:submission_id>/review/', views.SubmissionReviewView.as_view(), name='hw-review'),
    path('submissions/<uuid:submission_id>/request-resubmit/', views.RequestResubmitView.as_view(), name='hw-request-resubmit'),
    path('assignments/<uuid:assignment_id>/remind/', views.RemindView.as_view(), name='hw-remind'),
    path('assignments/<uuid:assignment_id>/ai-summary/', views.AiSummaryView.as_view(), name='hw-ai-summary'),
    path('assignments/<uuid:assignment_id>/focus/', views.AssignmentFocusView.as_view(), name='hw-focus'),
    path('report/', views.ProgressReportView.as_view(), name='hw-report'),
]
