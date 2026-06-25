"""Plain APIViews for the employee dashboard."""

from dataclasses import asdict

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from employee_dashboard.serializers import (
    EmployeeDaySummarySerializer,
    EmployeeUpcomingVisitOutputSerializer,
)
from shared.container import container
from shared.permissions import IsAdminOrEmployee


def _serialize_upcoming_visit(instance) -> dict:
    host = instance.host_user
    return {
        "id": instance.id,
        "visitor_name": instance.visitor_name,
        "scheduled_date": instance.scheduled_date,
        "status": instance.display_status,
        "description": instance.description or "",
        "is_group": instance.visitor_group_id is not None,
        "host": (
            {
                "id": host.id,
                "full_name": host.full_name,
                "apartment": host.apartment,
                "block": host.block,
            }
            if host
            else None
        ),
    }


@extend_schema(tags=["employee_dashboard"])
class EmployeeDaySummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrEmployee]

    @extend_schema(responses={200: EmployeeDaySummarySerializer})
    def get(self, request):
        summary = container.employee_dashboard_service.day_summary(request.user)
        return Response(EmployeeDaySummarySerializer(asdict(summary)).data)


@extend_schema(tags=["employee_dashboard"])
class EmployeeUpcomingVisitsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrEmployee]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Max visits to return (1–50, default 10).",
            ),
        ],
        responses={200: EmployeeUpcomingVisitOutputSerializer(many=True)},
    )
    def get(self, request):
        raw_limit = request.query_params.get("limit")
        limit = int(raw_limit) if raw_limit else 10
        visits = container.employee_dashboard_service.upcoming_visits(
            request.user, limit=limit
        )
        payload = [_serialize_upcoming_visit(v) for v in visits]
        return Response(
            EmployeeUpcomingVisitOutputSerializer(payload, many=True).data
        )
