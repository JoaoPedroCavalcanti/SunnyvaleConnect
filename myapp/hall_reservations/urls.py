from django.urls import path

from hall_reservations.views import (
    HallReservationDetailView,
    HallReservationListCreateView,
)

app_name = "hall_reservations"

urlpatterns = [
    path("", HallReservationListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", HallReservationDetailView.as_view(), name="detail"),
]
