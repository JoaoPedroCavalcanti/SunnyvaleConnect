"""Plain APIViews for SunnyVale news. All logic in the service."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.container import container
from sunny_vale_news.models import SunnyValeNewsModel
from sunny_vale_news.serializers import (
    PaginatedSunnyValeNewsOutputSerializer,
    SunnyValeNewsInputSerializer,
    SunnyValeNewsOutputSerializer,
    SunnyValeNewsPatchSerializer,
)


@extend_schema(tags=["sunny_vale_news"])
class SunnyValeNewsListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="kind",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[c for c, _ in SunnyValeNewsModel.Kind.choices],
                description="Filter by announcement kind.",
            ),
        ],
        responses={200: PaginatedSunnyValeNewsOutputSerializer},
    )
    def get(self, request):
        kind = request.query_params.get("kind") or None
        queryset = container.sunny_vale_news_service.list(
            request.user, kind=kind
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = SunnyValeNewsOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=SunnyValeNewsInputSerializer,
        responses={201: SunnyValeNewsOutputSerializer},
    )
    def post(self, request):
        serializer = SunnyValeNewsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        news = container.sunny_vale_news_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            SunnyValeNewsOutputSerializer(news).data, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["sunny_vale_news"])
class SunnyValeNewsDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: SunnyValeNewsOutputSerializer})
    def get(self, request, pk: int):
        news = container.sunny_vale_news_service.get(request.user, pk)
        return Response(SunnyValeNewsOutputSerializer(news).data)

    @extend_schema(
        request=SunnyValeNewsInputSerializer,
        responses={200: SunnyValeNewsOutputSerializer},
    )
    def put(self, request, pk: int):
        serializer = SunnyValeNewsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        news = container.sunny_vale_news_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(SunnyValeNewsOutputSerializer(news).data)

    @extend_schema(
        request=SunnyValeNewsPatchSerializer,
        responses={200: SunnyValeNewsOutputSerializer},
    )
    def patch(self, request, pk: int):
        serializer = SunnyValeNewsPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        news = container.sunny_vale_news_service.update(
            request.user, pk, serializer.validated_data
        )
        return Response(SunnyValeNewsOutputSerializer(news).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int):
        container.sunny_vale_news_service.delete(request.user, pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
