from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from users.views import LoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("user/", include(("users.urls"), namespace="users")),
    path("bbq/", include("bbq_reservations.urls")),
    path("hall/", include("hall_reservations.urls")),
    path("visitor_access/", include("visitor_access.urls")),
    path("service_requests/", include("service_requests.urls")),
    path("condo_payments/", include("condo_payments.urls")),
    path("delivery_notification/", include("delivery_notification.urls")),
    path("sunny_vale_news/", include("sunny_vale_news.urls")),
    path("units/", include(("units.urls"), namespace="units")),
    # Legacy alias — households was renamed to units; keep old paths working.
    path("households/", include(("units.urls"), namespace="households")),
    path("condominiums/", include(("condominiums.urls"), namespace="condominiums")),
    path(
        "admin_dashboard/",
        include(("admin_dashboard.urls"), namespace="admin_dashboard"),
    ),
    path(
        "employee_dashboard/",
        include(("employee_dashboard.urls"), namespace="employee_dashboard"),
    ),
    path("api/token/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
