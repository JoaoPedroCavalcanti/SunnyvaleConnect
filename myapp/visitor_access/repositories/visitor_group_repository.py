"""Dumb repository for VisitorGroupModel and its members."""

from abc import ABC, abstractmethod

from visitor_access.models import VisitorGroupMemberModel, VisitorGroupModel


class IVisitorGroupRepository(ABC):
    @abstractmethod
    def list_for_user(self, user_id: int): ...

    @abstractmethod
    def list_all(self): ...

    @abstractmethod
    def get_by_id(self, pk: int) -> VisitorGroupModel | None: ...

    @abstractmethod
    def exists_with_name_for_user(
        self, user_id: int, name: str, exclude_pk: int | None = None
    ) -> bool: ...

    @abstractmethod
    def create(self, data: dict) -> VisitorGroupModel: ...

    @abstractmethod
    def update(
        self, instance: VisitorGroupModel, data: dict
    ) -> VisitorGroupModel: ...

    @abstractmethod
    def delete(self, instance: VisitorGroupModel) -> None: ...

    @abstractmethod
    def list_members(self, group_id: int): ...

    @abstractmethod
    def replace_members(
        self, group: VisitorGroupModel, members: list[dict]
    ) -> list[VisitorGroupMemberModel]: ...

    @abstractmethod
    def add_members(
        self, group: VisitorGroupModel, members: list[dict]
    ) -> list[VisitorGroupMemberModel]: ...


class DjangoVisitorGroupRepository(IVisitorGroupRepository):
    def list_for_user(self, user_id):
        return (
            VisitorGroupModel.objects.filter(host_user_id=user_id)
            .prefetch_related("members")
            .order_by("-created_at")
        )

    def list_all(self):
        return VisitorGroupModel.objects.all().prefetch_related("members").order_by(
            "-created_at"
        )

    def get_by_id(self, pk):
        return (
            VisitorGroupModel.objects.filter(pk=pk)
            .prefetch_related("members")
            .first()
        )

    def exists_with_name_for_user(self, user_id, name, exclude_pk=None):
        qs = VisitorGroupModel.objects.filter(host_user_id=user_id, name=name)
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        return qs.exists()

    def create(self, data):
        return VisitorGroupModel.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()

    def list_members(self, group_id):
        return VisitorGroupMemberModel.objects.filter(group_id=group_id).order_by("id")

    def replace_members(self, group, members):
        VisitorGroupMemberModel.objects.filter(group=group).delete()
        return self.add_members(group, members)

    def add_members(self, group, members):
        objs = [VisitorGroupMemberModel(group=group, **m) for m in members]
        VisitorGroupMemberModel.objects.bulk_create(objs)
        return list(VisitorGroupMemberModel.objects.filter(group=group).order_by("id"))
