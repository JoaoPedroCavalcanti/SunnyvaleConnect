from rest_framework.routers import SimpleRouter
from condo_payments.views import CondoPaymentViewSet

condo_payments_router = SimpleRouter()

condo_payments_router.register(
    '',
    CondoPaymentViewSet,
    basename='condo_payments_router'
)
urlpatterns = condo_payments_router.urls