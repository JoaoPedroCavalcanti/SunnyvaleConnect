from django.urls import path

from employee_dashboard.views import EmployeeDaySummaryView, EmployeeUpcomingVisitsView

app_name = "employee_dashboard"

urlpatterns = [
    path("day_summary/", EmployeeDaySummaryView.as_view(), name="day-summary"),
    path(
        "upcoming_visits/",
        EmployeeUpcomingVisitsView.as_view(),
        name="upcoming-visits",
    ),
]
