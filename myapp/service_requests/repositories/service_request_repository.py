"""Dumb repository for ServiceRequestModel."""

from abc import ABC, abstractmethod
from datetime import datetime

from service_requests.models import ServiceRequestModel


class IServiceRequestRepository(ABC):
    @abstractmethod
    def list_all(
        self,
        status: str | None = None,
        priority: str | None = None,
        service_type: str | None = None,
        responded_by_id: int | None = None,
        requester_id: int | None = None,
        period: str | None = None,
        reference: datetime | None = None,
        *,
        condominium_id: int,
    ): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> ServiceRequestModel | None: ...

    @abstractmethod
    def create(self, data: dict) -> ServiceRequestModel: ...

    @abstractmethod
    def update(
        self, instance: ServiceRequestModel, data: dict
    ) -> ServiceRequestModel: ...

    @abstractmethod
    def delete(self, instance: ServiceRequestModel) -> None: ...

    @abstractmethod
    def count_by_status(self, status: str | None = None, *, condominium_id: int) -> int: ...


class DjangoServiceRequestRepository(IServiceRequestRepository):
    def list_all(
        self,
        status=None,
        priority=None,
        service_type=None,
        responded_by_id=None,
        requester_id=None,
        period=None,
        reference=None,
        *,
        condominium_id,
    ):
        qs = ServiceRequestModel.objects.select_related(
            "requester", "responded_by"
        ).filter(requester__condominium_id=condominium_id)
        qs = self._apply_filters(
            qs,
            status,
            priority,
            service_type,
            responded_by_id,
            requester_id,
        )
        if period == "future" and reference is not None:
            qs = qs.filter(request_scheduled_date__gte=reference)
        elif period == "past" and reference is not None:
            qs = qs.filter(request_scheduled_date__lt=reference)
        return qs

    def get_by_id(self, pk):
        return (
            ServiceRequestModel.objects.select_related("requester", "responded_by")
            .filter(pk=pk)
            .first()
        )

    def create(self, data):
        return ServiceRequestModel.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()

    def count_by_status(self, status=None, *, condominium_id):
        qs = ServiceRequestModel.objects.filter(
            requester__condominium_id=condominium_id
        )
        if status:
            qs = qs.filter(status=status)
        return qs.count()

    @staticmethod
    def _apply_filters(
        qs,
        status,
        priority,
        service_type,
        responded_by_id=None,
        requester_id=None,
    ):
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if service_type:
            qs = qs.filter(service_type=service_type)
        if responded_by_id:
            qs = qs.filter(responded_by_id=responded_by_id)
        if requester_id:
            qs = qs.filter(requester_id=requester_id)
        return qs
