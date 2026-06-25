"""Dumb repository for VisitorAccessModel."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable

from visitor_access.models import VisitorAccessModel


class IVisitorAccessRepository(ABC):
    @abstractmethod
    def list_all(
        self,
        status_in: Iterable[str] | None = None,
        scheduled_after: datetime | None = None,
        scheduled_before: datetime | None = None,
        is_group: bool | None = None,
    ): ...

    @abstractmethod
    def list_for_user(
        self,
        user_id: int,
        status_in: Iterable[str] | None = None,
        scheduled_after: datetime | None = None,
        scheduled_before: datetime | None = None,
        is_group: bool | None = None,
    ): ...

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

    @abstractmethod
    def count_scheduled_between(
        self,
        start: datetime,
        end: datetime,
        *,
        exclude_statuses: Iterable[str] | None = None,
    ) -> int: ...

    @abstractmethod
    def count_with_scheduled_after(
        self,
        after: datetime,
        *,
        status_in: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ) -> int: ...

    @abstractmethod
    def list_upcoming(
        self,
        after: datetime,
        *,
        limit: int = 10,
        status_in: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ): ...


class DjangoVisitorAccessRepository(IVisitorAccessRepository):
    def list_all(
        self,
        status_in=None,
        scheduled_after=None,
        scheduled_before=None,
        is_group=None,
    ):
        qs = VisitorAccessModel.objects.all().order_by("-scheduled_date")
        return self._apply_filters(
            qs, status_in, scheduled_after, scheduled_before, is_group
        )

    def list_for_user(
        self,
        user_id,
        status_in=None,
        scheduled_after=None,
        scheduled_before=None,
        is_group=None,
    ):
        qs = VisitorAccessModel.objects.filter(host_user_id=user_id).order_by(
            "-scheduled_date"
        )
        return self._apply_filters(
            qs, status_in, scheduled_after, scheduled_before, is_group
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

    @staticmethod
    def _apply_filters(qs, status_in, scheduled_after, scheduled_before, is_group):
        if status_in:
            qs = qs.filter(status__in=list(status_in))
        if scheduled_after is not None:
            qs = qs.filter(scheduled_date__gte=scheduled_after)
        if scheduled_before is not None:
            qs = qs.filter(scheduled_date__lt=scheduled_before)
        if is_group is True:
            qs = qs.filter(visitor_group__isnull=False)
        elif is_group is False:
            qs = qs.filter(visitor_group__isnull=True)
        return qs

    def count_scheduled_between(
        self,
        start: datetime,
        end: datetime,
        *,
        exclude_statuses: Iterable[str] | None = None,
    ) -> int:
        qs = VisitorAccessModel.objects.filter(
            scheduled_date__gte=start,
            scheduled_date__lt=end,
        )
        if exclude_statuses:
            qs = qs.exclude(status__in=list(exclude_statuses))
        return qs.count()

    def count_with_scheduled_after(
        self,
        after: datetime,
        *,
        status_in: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ) -> int:
        qs = VisitorAccessModel.objects.filter(scheduled_date__gte=after)
        if status_in:
            qs = qs.filter(status__in=list(status_in))
        if exclude_statuses:
            qs = qs.exclude(status__in=list(exclude_statuses))
        return qs.count()

    def list_upcoming(
        self,
        after: datetime,
        *,
        limit: int = 10,
        status_in: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ):
        qs = (
            VisitorAccessModel.objects.select_related("host_user", "visitor_group")
            .filter(scheduled_date__gte=after)
            .order_by("scheduled_date")
        )
        if status_in:
            qs = qs.filter(status__in=list(status_in))
        if exclude_statuses:
            qs = qs.exclude(status__in=list(exclude_statuses))
        return qs[:limit]
