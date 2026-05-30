from django.urls import path

from bbq_reservations.views import (
    BBQReservationDetailView,
    BBQReservationListCreateView,
)

app_name = "bbq_reservations"

urlpatterns = [
    path("", BBQReservationListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", BBQReservationDetailView.as_view(), name="detail"),
]
