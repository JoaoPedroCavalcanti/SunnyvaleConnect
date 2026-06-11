from django.urls import path

from visitor_access.views import (
    VisitorAccessCheckinView,
    VisitorAccessCheckoutView,
    VisitorAccessDetailView,
    VisitorAccessListCreateView,
    VisitorGroupDetailView,
    VisitorGroupListCreateView,
    VisitorGroupScheduleView,
    VisitorGroupVisitsListView,
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
    path(
        "groups/",
        VisitorGroupListCreateView.as_view(),
        name="groups-list-create",
    ),
    path(
        "groups/visits/",
        VisitorGroupVisitsListView.as_view(),
        name="groups-visits-list",
    ),
    path(
        "groups/<int:pk>/",
        VisitorGroupDetailView.as_view(),
        name="groups-detail",
    ),
    path(
        "groups/<int:pk>/schedule/",
        VisitorGroupScheduleView.as_view(),
        name="groups-schedule",
    ),
    path("<int:pk>/", VisitorAccessDetailView.as_view(), name="detail"),
]
