"""Dumb repository for VisitorContactModel."""

from abc import ABC, abstractmethod

from visitor_access.models import VisitorContactModel


class IVisitorContactRepository(ABC):
    @abstractmethod
    def list_for_user(self, user_id: int): ...

    @abstractmethod
    def list_all(self, *, condominium_id: int): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> VisitorContactModel | None: ...

    @abstractmethod
    def exists_with_name_for_user(
        self, user_id: int, name: str, exclude_pk: int | None = None
    ) -> bool: ...

    @abstractmethod
    def create(self, data: dict) -> VisitorContactModel: ...

    @abstractmethod
    def update(
        self, instance: VisitorContactModel, data: dict
    ) -> VisitorContactModel: ...

    @abstractmethod
    def delete(self, instance: VisitorContactModel) -> None: ...


class DjangoVisitorContactRepository(IVisitorContactRepository):
    def list_for_user(self, user_id):
        return VisitorContactModel.objects.filter(host_user_id=user_id).order_by(
            "-created_at"
        )

    def list_all(self, *, condominium_id):
        return VisitorContactModel.objects.filter(
            host_user__condominium_id=condominium_id
        ).order_by("-created_at")

    def get_by_id(self, pk):
        return VisitorContactModel.objects.filter(pk=pk).first()

    def exists_with_name_for_user(self, user_id, name, exclude_pk=None):
        qs = VisitorContactModel.objects.filter(
            host_user_id=user_id, name__iexact=name.strip()
        )
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        return qs.exists()

    def create(self, data):
        return VisitorContactModel.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()
