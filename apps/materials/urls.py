from django.urls import path

from . import views

urlpatterns = [
    path('', views.MaterialListCreateView.as_view(), name='material-list'),
    path('courses/', views.CourseFoldersView.as_view(), name='material-courses'),
    path('courses/<uuid:course_id>/lessons/', views.CourseLessonFoldersView.as_view(), name='material-course-lessons'),
    path('lessons/<uuid:lesson_id>/', views.LessonFolderView.as_view(), name='material-lesson-folder'),
    path('lessons/<uuid:lesson_id>/board.pdf', views.LessonBoardPdfView.as_view(), name='material-lesson-board'),
    path('<uuid:pk>/', views.MaterialDetailView.as_view(), name='material-detail'),
    path('<uuid:pk>/file/', views.MaterialFileView.as_view(), name='material-file'),
]
