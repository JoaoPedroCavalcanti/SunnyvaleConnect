"""Plain APIView for the admin dashboard. All logic lives in the service."""

from dataclasses import asdict

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_dashboard.serializers import AdminDashboardOverviewSerializer
from shared.container import container
from shared.permissions import IsAdmin


@extend_schema(tags=["admin_dashboard"])
class AdminDashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(responses={200: AdminDashboardOverviewSerializer})
    def get(self, request):
        overview = container.admin_dashboard_service.overview(request.user)
        return Response(AdminDashboardOverviewSerializer(asdict(overview)).data)
