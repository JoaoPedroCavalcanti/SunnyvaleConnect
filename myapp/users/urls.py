from rest_framework.routers import SimpleRouter
from users.views import UserViewSet

app_name = "users"


userRouter = SimpleRouter()
userRouter.register("", UserViewSet, basename="users-api")

urlpatterns = userRouter.urls
