"""Dumb repository for ServiceRequestModel."""

from abc import ABC, abstractmethod

from service_requests.models import ServiceRequestModel


class IServiceRequestRepository(ABC):
    @abstractmethod
    def list_all(
        self,
        status: str | None = None,
        priority: str | None = None,
        service_type: str | None = None,
        responded_by_id: int | None = None,
        *,
        condominium_id: int,
    ): ...

    @abstractmethod
    def list_for_user(
        self,
        user_id: int,
        status: str | None = None,
        priority: str | None = None,
        service_type: str | None = None,
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
        *,
        condominium_id,
    ):
        qs = ServiceRequestModel.objects.select_related(
            "requester", "responded_by"
        ).filter(requester__condominium_id=condominium_id)
        return self._apply_filters(
            qs, status, priority, service_type, responded_by_id
        )

    def list_for_user(
        self, user_id, status=None, priority=None, service_type=None, *, condominium_id
    ):
        qs = ServiceRequestModel.objects.select_related(
            "requester", "responded_by"
        ).filter(
            requester_id=user_id,
            requester__condominium_id=condominium_id,
        )
        return self._apply_filters(qs, status, priority, service_type)

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
    def _apply_filters(qs, status, priority, service_type, responded_by_id=None):
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if service_type:
            qs = qs.filter(service_type=service_type)
        if responded_by_id:
            qs = qs.filter(responded_by_id=responded_by_id)
        return qs
