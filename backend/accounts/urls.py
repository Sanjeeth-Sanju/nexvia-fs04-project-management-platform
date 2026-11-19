
from django.urls import path

from .csrf import csrf_token_view
from .views import (
    RegisterView,
    LoginView,
    RefreshView,
    LogoutView,
    CurrentUserView,
    ProfileView,
    PasswordChangeRequestView,
    PasswordChangeVerifyView,
    PasswordChangeConfirmView,
    AccountDeletionImpactView,
    AccountDeletionConfirmView,
    WorkspaceDataExportView,
)


urlpatterns = [
    path("csrf/", csrf_token_view, name="csrf"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("password-change/request/", PasswordChangeRequestView.as_view(), name="password-change-request"),
    path("password-change/verify/", PasswordChangeVerifyView.as_view(), name="password-change-verify"),
    path("password-change/confirm/", PasswordChangeConfirmView.as_view(), name="password-change-confirm"),
    path("account-deletion/impact/", AccountDeletionImpactView.as_view(), name="account-deletion-impact"),
    path("account-deletion/confirm/", AccountDeletionConfirmView.as_view(), name="account-deletion-confirm"),
    path("data-export/", WorkspaceDataExportView.as_view(), name="workspace-data-export"),
]
