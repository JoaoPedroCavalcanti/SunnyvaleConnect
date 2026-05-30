from django.urls import path

from sunny_vale_news.views import (
    SunnyValeNewsDetailView,
    SunnyValeNewsListCreateView,
)

app_name = "sunny_vale_news"

urlpatterns = [
    path("", SunnyValeNewsListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", SunnyValeNewsDetailView.as_view(), name="detail"),
]
