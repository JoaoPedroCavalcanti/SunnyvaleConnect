from django.urls import path

from users.views import (
    ResendVerificationView,
    UserDetailView,
    UserListCreateView,
    UserMeView,
    VerifyEmailView,
)

app_name = "users"

urlpatterns = [
    path("", UserListCreateView.as_view(), name="users-api-list"),
    path("me/", UserMeView.as_view(), name="users-api-me"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path(
        "resend-verification/",
        ResendVerificationView.as_view(),
        name="resend-verification",
    ),
    path("<int:pk>/", UserDetailView.as_view(), name="users-api-detail"),
]
