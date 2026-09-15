from django.urls import path

from . import views

urlpatterns = [
    path('periodic-table/', views.PeriodicTableView.as_view(), name='board-periodic-table'),
    path('<uuid:lesson_id>/', views.BoardView.as_view(), name='board'),
    path('<uuid:lesson_id>/stroke/', views.StrokeView.as_view(), name='board-stroke'),
    path('<uuid:lesson_id>/sheet/', views.SheetView.as_view(), name='board-sheet'),
    path('<uuid:lesson_id>/erase/', views.EraseView.as_view(), name='board-erase'),
    path('<uuid:lesson_id>/grant/', views.GrantView.as_view(), name='board-grant'),
    path('<uuid:lesson_id>/solve/', views.SolveView.as_view(), name='board-solve'),
    path('<uuid:lesson_id>/pdf/', views.PdfView.as_view(), name='board-pdf'),
]
