from django.urls import path

from admin_dashboard.views import AdminDashboardOverviewView

app_name = "admin_dashboard"

urlpatterns = [
    path("overview/", AdminDashboardOverviewView.as_view(), name="overview"),
]
