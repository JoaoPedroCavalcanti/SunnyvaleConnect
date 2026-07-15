from django.urls import path

from reservations.views import (
    LocationAvailabilityView,
    ReservableLocationDetailView,
    ReservableLocationListCreateView,
    ReservationApproveView,
    ReservationDetailView,
    ReservationListCreateView,
    ReservationRejectView,
)


app_name = "reservations"

urlpatterns = [
    path(
        "reservation-locations/",
        ReservableLocationListCreateView.as_view(),
        name="location-list-create",
    ),
    path(
        "reservation-locations/<int:pk>/",
        ReservableLocationDetailView.as_view(),
        name="location-detail",
    ),
    path(
        "reservation-locations/<int:pk>/availability/",
        LocationAvailabilityView.as_view(),
        name="location-availability",
    ),
    path(
        "reservations/",
        ReservationListCreateView.as_view(),
        name="reservation-list-create",
    ),
    path(
        "reservations/<int:pk>/",
        ReservationDetailView.as_view(),
        name="reservation-detail",
    ),
    path(
        "reservations/<int:pk>/approve/",
        ReservationApproveView.as_view(),
        name="reservation-approve",
    ),
    path(
        "reservations/<int:pk>/reject/",
        ReservationRejectView.as_view(),
        name="reservation-reject",
    ),
]
