from django.urls import path

from bbq_reservations.views import (
    BBQReservationApproveView,
    BBQReservationDetailView,
    BBQReservationListCreateView,
    BBQReservationRejectView,
)

app_name = "bbq_reservations"

urlpatterns = [
    path("", BBQReservationListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", BBQReservationDetailView.as_view(), name="detail"),
    path(
        "<int:pk>/approve/",
        BBQReservationApproveView.as_view(),
        name="approve",
    ),
    path(
        "<int:pk>/reject/",
        BBQReservationRejectView.as_view(),
        name="reject",
    ),
]
