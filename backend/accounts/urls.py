
from django.urls import path

from .csrf import csrf_token_view
from .views import (
    RegisterView,
    LoginView,
    RefreshView,
    LogoutView,
    CurrentUserView,
)


urlpatterns = [
    path("csrf/", csrf_token_view, name="csrf"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
]
