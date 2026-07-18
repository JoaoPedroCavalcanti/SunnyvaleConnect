from django.urls import path

from visitor_access.views import (
    VisitorAccessDetailView,
    VisitorAccessListCreateView,
    VisitorAccessNotifyArrivalView,
    VisitorAccessValidateView,
    VisitorContactDetailView,
    VisitorContactListCreateView,
    VisitorContactScheduleView,
    VisitorGroupDetailView,
    VisitorGroupListCreateView,
    VisitorGroupScheduleView,
    VisitorGroupVisitsListView,
)

app_name = "visitor_access"

urlpatterns = [
    path("", VisitorAccessListCreateView.as_view(), name="list-create"),
    path(
        "validate/",
        VisitorAccessValidateView.as_view(),
        name="validate",
    ),
    path(
        "contacts/",
        VisitorContactListCreateView.as_view(),
        name="contacts-list-create",
    ),
    path(
        "contacts/<int:pk>/",
        VisitorContactDetailView.as_view(),
        name="contacts-detail",
    ),
    path(
        "contacts/<int:pk>/schedule/",
        VisitorContactScheduleView.as_view(),
        name="contacts-schedule",
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
    path(
        "<int:pk>/notify-arrival/",
        VisitorAccessNotifyArrivalView.as_view(),
        name="notify-arrival",
    ),
    path("<int:pk>/", VisitorAccessDetailView.as_view(), name="detail"),
]
