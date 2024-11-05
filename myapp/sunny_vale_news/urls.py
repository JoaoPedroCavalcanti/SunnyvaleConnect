from rest_framework.routers import SimpleRouter
from sunny_vale_news.views import SunnyValeNewsViewSet

sunny_vale_new_router = SimpleRouter()
sunny_vale_new_router.register(
    '',
    SunnyValeNewsViewSet,
    basename='sunny_vale_new'
)
urlpatterns = sunny_vale_new_router.urls
