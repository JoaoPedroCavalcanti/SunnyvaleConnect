"""Dumb repository for ServiceRequestModel."""

from abc import ABC, abstractmethod

from service_requests.models import ServiceRequestModel


class IServiceRequestRepository(ABC):
    @abstractmethod
    def list_all(self): ...

    @abstractmethod
    def list_for_user(self, user_id: int): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> ServiceRequestModel | None: ...

    @abstractmethod
    def create(self, data: dict) -> ServiceRequestModel: ...

    @abstractmethod
    def update(self, instance: ServiceRequestModel, data: dict) -> ServiceRequestModel: ...

    @abstractmethod
    def delete(self, instance: ServiceRequestModel) -> None: ...


class DjangoServiceRequestRepository(IServiceRequestRepository):
    def list_all(self):
        return ServiceRequestModel.objects.all().order_by("-request_scheduled_date")

    def list_for_user(self, user_id):
        return ServiceRequestModel.objects.filter(
            requester_user_id=user_id
        ).order_by("-request_scheduled_date")

    def get_by_id(self, pk):
        return ServiceRequestModel.objects.filter(pk=pk).first()

    def create(self, data):
        return ServiceRequestModel.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()
