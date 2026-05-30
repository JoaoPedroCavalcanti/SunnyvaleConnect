from django.urls import path

from condo_payments.views import (
    CondoPaymentDetailView,
    CondoPaymentListCreateView,
    SetPaidStatusView,
)

app_name = "condo_payments"

urlpatterns = [
    path("", CondoPaymentListCreateView.as_view(), name="list-create"),
    path("set_paid_status/", SetPaidStatusView.as_view(), name="set-paid-status"),
    path("<int:pk>/", CondoPaymentDetailView.as_view(), name="detail"),
]
