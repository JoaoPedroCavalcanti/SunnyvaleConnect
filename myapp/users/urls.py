from django.urls import path

from users.views import UserDetailView, UserListCreateView, UserMeView

app_name = "users"

urlpatterns = [
    path("", UserListCreateView.as_view(), name="users-api-list"),
    path("me/", UserMeView.as_view(), name="users-api-me"),
    path("<int:pk>/", UserDetailView.as_view(), name="users-api-detail"),
]
