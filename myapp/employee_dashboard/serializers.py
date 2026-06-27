"""Type/shape-only serializers for the employee dashboard."""

from rest_framework import serializers


class EmployeeDaySummarySerializer(serializers.Serializer):
    deliveries_today = serializers.IntegerField(read_only=True, allow_null=True)
    visits_today = serializers.IntegerField(read_only=True, allow_null=True)
    scheduled_visits = serializers.IntegerField(read_only=True, allow_null=True)
    cleared_visits_today = serializers.IntegerField(read_only=True, allow_null=True)
    pending_service_requests = serializers.IntegerField(
        read_only=True, allow_null=True
    )


class EmployeeUpcomingVisitHostSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    apartment = serializers.CharField(read_only=True)
    block = serializers.CharField(read_only=True)


class EmployeeUpcomingVisitOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    visitor_name = serializers.CharField(read_only=True)
    scheduled_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True)
    is_group = serializers.BooleanField(read_only=True)
    host = EmployeeUpcomingVisitHostSerializer(read_only=True, allow_null=True)
