from rest_framework.routers import SimpleRouter
from visitor_access.views import VisitorAccessViewSet

visitor_access_router = SimpleRouter()
visitor_access_router.register(
    "", VisitorAccessViewSet, basename="visitor_access-router"
)
urlpatterns = visitor_access_router.urls
