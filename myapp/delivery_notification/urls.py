from django.urls import path

from delivery_notification.views import (
    DeliveryApartmentListView,
    DetailDeliveryNotificationView,
    ListDeliveryNotificationsView,
    SendDeliveryNotificationView,
)

app_name = "delivery_notification"

urlpatterns = [
    path(
        "apartments/",
        DeliveryApartmentListView.as_view(),
        name="list_apartments",
    ),
    path("", SendDeliveryNotificationView.as_view(), name="send_delivery_notification"),
    path("list/", ListDeliveryNotificationsView.as_view(), name="list_notifications"),
    path("<int:pk>/", DetailDeliveryNotificationView.as_view(), name="detail_notification"),
]
