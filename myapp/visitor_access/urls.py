from django.urls import path

from visitor_access.views import (
    VisitorAccessCheckinView,
    VisitorAccessCheckoutView,
    VisitorAccessDetailView,
    VisitorAccessListCreateView,
)

app_name = "visitor_access"

urlpatterns = [
    path("", VisitorAccessListCreateView.as_view(), name="list-create"),
    path(
        "checkin/<str:visitor_access_link_checkin>/",
        VisitorAccessCheckinView.as_view(),
        name="checkin",
    ),
    path(
        "checkout/<str:visitor_access_link_checkout>/",
        VisitorAccessCheckoutView.as_view(),
        name="checkout",
    ),
    path("<int:pk>/", VisitorAccessDetailView.as_view(), name="detail"),
]
