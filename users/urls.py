from rest_framework.routers import SimpleRouter
from users.views import UserViewSet
from django.urls import reverse


app_name = "users"


userRouter = SimpleRouter()
userRouter.register(
    '',
    UserViewSet,
    basename='users-api'
)
urlpatterns = userRouter.urls

