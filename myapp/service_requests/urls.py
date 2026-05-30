from django.urls import path

from service_requests.views import (
    AcceptOrDeclineServiceRequestView,
    ServiceRequestDetailView,
    ServiceRequestListCreateView,
)

app_name = "service_requests"

urlpatterns = [
    path(
        "",
        ServiceRequestListCreateView.as_view(),
        name="service_requests_list_and_create",
    ),
    path(
        "<int:pk>/",
        ServiceRequestDetailView.as_view(),
        name="service_request_detail_retrieve_and_delete",
    ),
    path(
        "accept_or_decline/<int:pk>/<str:accept_or_decline>/",
        AcceptOrDeclineServiceRequestView.as_view(),
        name="accept_request",
    ),
]
