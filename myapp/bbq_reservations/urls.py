from rest_framework.routers import SimpleRouter
from bbq_reservations.views import BBQReservationViewSet

bbq_reservations_router = SimpleRouter()
bbq_reservations_router.register(
    "", BBQReservationViewSet, basename="bbq_reservations-router"
)

urlpatterns = bbq_reservations_router.urls
