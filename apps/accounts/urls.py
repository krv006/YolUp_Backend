from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('logins/', views.LoginHistoryView.as_view(), name='login-history'),
    path('token/refresh/', views.RefreshView.as_view(), name='token-refresh'),
    path('me/', views.MeView.as_view(), name='me'),
    path('switch/<uuid:pk>/', views.SwitchAccountView.as_view(), name='switch-account'),
    path('switch-role/', views.SwitchRoleView.as_view(), name='switch-role'),
    path('me/certificates/', views.CertificateListCreateView.as_view(), name='certificate-list-create'),
    path('me/certificates/<uuid:pk>/', views.CertificateDeleteView.as_view(), name='certificate-delete'),
    path('me/ratings/', views.MyRatingsListView.as_view(), name='my-ratings-list'),
    path('users/search/', views.UserSearchView.as_view(), name='user-search'),
    path('teachers/', views.TeacherStatsListView.as_view(), name='teacher-stats-list'),
    path('teachers/pending/', views.PendingTeachersListView.as_view(), name='teacher-pending-list'),
    path('teachers/video-stats/', views.TeacherVideoStatsView.as_view(), name='teacher-video-stats'),
    path('teachers/<uuid:pk>/approve/', views.ApproveTeacherView.as_view(), name='teacher-approve'),
    path('teachers/<uuid:pk>/stats/', views.TeacherStatsDetailView.as_view(), name='teacher-stats-detail'),
    path('teachers/<uuid:pk>/ratings/', views.TeacherRatingsListView.as_view(), name='teacher-ratings-list'),
    path('children/', views.ChildCreateView.as_view(), name='child-create'),
    path('links/', views.LinkListView.as_view(), name='link-list'),
    path('links/request/', views.LinkRequestView.as_view(), name='link-request'),
    path('links/<uuid:pk>/respond/', views.LinkRespondView.as_view(), name='link-respond'),
    path('consents/', views.ConsentListCreateView.as_view(), name='consents'),
]
