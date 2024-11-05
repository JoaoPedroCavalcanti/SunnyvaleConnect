from django.urls import path
from rest_framework.routers import SimpleRouter
from users.views import UserViewSet

userRouter = SimpleRouter()
userRouter.register(
    '',
    UserViewSet,
    basename='users-api'
)
urlpatterns = userRouter.urls
