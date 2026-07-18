from django.urls import path

from users.views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetResendView,
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
    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "password-reset/resend/",
        PasswordResetResendView.as_view(),
        name="password-reset-resend",
    ),
    path("<int:pk>/", UserDetailView.as_view(), name="users-api-detail"),
]
