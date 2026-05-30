"""Dumb repository for VisitorAccessModel."""

from abc import ABC, abstractmethod

from visitor_access.models import VisitorAccessModel


class IVisitorAccessRepository(ABC):
    @abstractmethod
    def list_all(self): ...

    @abstractmethod
    def list_for_user(self, user_id: int): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> VisitorAccessModel | None: ...

    @abstractmethod
    def create(self, data: dict) -> VisitorAccessModel: ...

    @abstractmethod
    def save(self, instance: VisitorAccessModel) -> VisitorAccessModel: ...

    @abstractmethod
    def update(self, instance: VisitorAccessModel, data: dict) -> VisitorAccessModel: ...

    @abstractmethod
    def delete(self, instance: VisitorAccessModel) -> None: ...


class DjangoVisitorAccessRepository(IVisitorAccessRepository):
    def list_all(self):
        return VisitorAccessModel.objects.all().order_by("-scheduled_date")

    def list_for_user(self, user_id):
        return VisitorAccessModel.objects.filter(host_user_id=user_id).order_by(
            "-scheduled_date"
        )

    def get_by_id(self, pk):
        return VisitorAccessModel.objects.filter(pk=pk).first()

    def create(self, data):
        return VisitorAccessModel.objects.create(**data)

    def save(self, instance):
        instance.save()
        return instance

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()
