"""Type/shape-only serializers for the admin dashboard."""

from rest_framework import serializers


class AdminDashboardOverviewSerializer(serializers.Serializer):
    active_residents = serializers.IntegerField(read_only=True)
    total_reservations = serializers.IntegerField(read_only=True)
    pending_reservations = serializers.IntegerField(read_only=True)
    published_news = serializers.IntegerField(read_only=True)
