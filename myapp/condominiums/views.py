"""Plain APIViews for condominiums."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from condominiums.serializers import (
    CondominiumInputSerializer,
    CondominiumLookupOutputSerializer,
    CondominiumOutputSerializer,
)
from shared.container import container


@extend_schema(tags=["condominiums"])
class CondominiumLookupView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="code",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Condominium invite code.",
            ),
        ],
        responses={200: CondominiumLookupOutputSerializer},
    )
    def get(self, request):
        code = request.query_params.get("code", "")
        condominium = container.condominium_service.lookup_by_code(code)
        serializer = CondominiumLookupOutputSerializer(
            condominium, context={"request": request}
        )
        return Response(serializer.data)


@extend_schema(tags=["condominiums"])
class CondominiumListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [IsAdminUser()]

    @extend_schema(responses={200: CondominiumOutputSerializer(many=True)})
    def get(self, request):
        condominiums = container.condominium_service.list_for_platform(request.user)
        serializer = CondominiumOutputSerializer(
            condominiums, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        request=CondominiumInputSerializer,
        responses={201: CondominiumOutputSerializer},
    )
    def post(self, request):
        serializer = CondominiumInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        condominium = container.condominium_service.create(
            request.user, serializer.validated_data
        )
        return Response(
            CondominiumOutputSerializer(
                condominium, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )
