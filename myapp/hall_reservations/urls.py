from rest_framework.routers import SimpleRouter
from hall_reservations.views import HallReservationViewSet

hall_reservation_router = SimpleRouter()
hall_reservation_router.register(
    '',
    HallReservationViewSet,
    basename='hall_reservation-router'
)

urlpatterns = hall_reservation_router.urls
