from django.urls import path

from service_requests.views import (
    ServiceRequestCompleteView,
    ServiceRequestDetailView,
    ServiceRequestListCreateView,
    ServiceRequestRespondView,
)

app_name = "service_requests"

urlpatterns = [
    path(
        "",
        ServiceRequestListCreateView.as_view(),
        name="list-create",
    ),
    path(
        "<int:pk>/",
        ServiceRequestDetailView.as_view(),
        name="detail",
    ),
    path(
        "<int:pk>/respond/",
        ServiceRequestRespondView.as_view(),
        name="respond",
    ),
    path(
        "<int:pk>/complete/",
        ServiceRequestCompleteView.as_view(),
        name="complete",
    ),
]
