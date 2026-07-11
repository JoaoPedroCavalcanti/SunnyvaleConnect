from django.urls import path

from hall_reservations.views import (
    HallAvailabilityView,
    HallReservationApproveView,
    HallReservationDetailView,
    HallReservationListCreateView,
    HallReservationRejectView,
)

app_name = "hall_reservations"

urlpatterns = [
    path(
        "availability/",
        HallAvailabilityView.as_view(),
        name="availability",
    ),
    path("", HallReservationListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", HallReservationDetailView.as_view(), name="detail"),
    path(
        "<int:pk>/approve/",
        HallReservationApproveView.as_view(),
        name="approve",
    ),
    path(
        "<int:pk>/reject/",
        HallReservationRejectView.as_view(),
        name="reject",
    ),
]
