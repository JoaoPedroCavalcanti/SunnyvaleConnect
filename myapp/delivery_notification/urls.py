from django.urls import path

from delivery_notification.views import (
    DetailDeliveryNotificationView,
    ListDeliveryNotificationsView,
    SendDeliveryNotificationView,
)

app_name = "delivery_notification"

urlpatterns = [
    path("", SendDeliveryNotificationView.as_view(), name="send_delivery_notification"),
    path("list/", ListDeliveryNotificationsView.as_view(), name="list_notifications"),
    path("<int:pk>/", DetailDeliveryNotificationView.as_view(), name="detail_notification"),
]
