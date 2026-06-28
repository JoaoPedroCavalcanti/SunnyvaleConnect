"""Dumb repository for SunnyValeNewsModel. Only DB access, no business logic."""

from abc import ABC, abstractmethod
from typing import Iterable

from sunny_vale_news.models import SunnyValeNewsModel


class ISunnyValeNewsRepository(ABC):
    @abstractmethod
    def list_all(self, *, condominium_id: int) -> Iterable[SunnyValeNewsModel]: ...

    @abstractmethod
    def list_by_kind(
        self, kind: str, *, condominium_id: int
    ) -> Iterable[SunnyValeNewsModel]: ...

    @abstractmethod
    def get_by_id(self, news_id: int) -> SunnyValeNewsModel | None: ...

    @abstractmethod
    def create(self, data: dict) -> SunnyValeNewsModel: ...

    @abstractmethod
    def update(
        self, instance: SunnyValeNewsModel, data: dict
    ) -> SunnyValeNewsModel: ...

    @abstractmethod
    def delete(self, instance: SunnyValeNewsModel) -> None: ...

    @abstractmethod
    def count_all(self, *, condominium_id: int) -> int: ...


class DjangoSunnyValeNewsRepository(ISunnyValeNewsRepository):
    def list_all(self, *, condominium_id):
        return (
            SunnyValeNewsModel.objects.select_related("created_by")
            .filter(condominium_id=condominium_id)
            .order_by("-created_at")
        )

    def list_by_kind(self, kind, *, condominium_id):
        return (
            SunnyValeNewsModel.objects.select_related("created_by")
            .filter(condominium_id=condominium_id, kind=kind)
            .order_by("-created_at")
        )

    def get_by_id(self, news_id):
        return (
            SunnyValeNewsModel.objects.select_related("created_by")
            .filter(pk=news_id)
            .first()
        )

    def create(self, data):
        return SunnyValeNewsModel.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()

    def count_all(self, *, condominium_id):
        return SunnyValeNewsModel.objects.filter(
            condominium_id=condominium_id
        ).count()
