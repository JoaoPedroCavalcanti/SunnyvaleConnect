"""Dumb repository for VisitorAccessModel."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable

from django.db.models import Q

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
    def get_by_access_token(self, token: str) -> VisitorAccessModel | None: ...

    @abstractmethod
    def get_by_access_code(self, code: str) -> VisitorAccessModel | None: ...

    @abstractmethod
    def exists_with_access_token(self, token: str) -> bool: ...

    @abstractmethod
    def exists_with_access_code(self, code: str) -> bool: ...

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
    def count_checked_in_between(self, start: datetime, end: datetime) -> int: ...

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
    @staticmethod
    def _list_queryset(qs):
        return qs.select_related("host_user", "visitor_group").prefetch_related(
            "visitor_group__members"
        )

    def list_all(
        self,
        status_in=None,
        scheduled_after=None,
        scheduled_before=None,
        is_group=None,
    ):
        qs = self._list_queryset(
            VisitorAccessModel.objects.all().order_by("-scheduled_date")
        )
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
        qs = self._list_queryset(
            VisitorAccessModel.objects.filter(host_user_id=user_id).order_by(
                "-scheduled_date"
            )
        )
        return self._apply_filters(
            qs, status_in, scheduled_after, scheduled_before, is_group
        )

    def get_by_id(self, pk):
        return VisitorAccessModel.objects.filter(pk=pk).first()

    def get_by_access_token(self, token):
        return VisitorAccessModel.objects.filter(access_token=token).first()

    def get_by_access_code(self, code):
        return VisitorAccessModel.objects.filter(access_code__iexact=code.strip()).first()

    def exists_with_access_token(self, token):
        return VisitorAccessModel.objects.filter(access_token=token).exists()

    def exists_with_access_code(self, code):
        return VisitorAccessModel.objects.filter(access_code__iexact=code.strip()).exists()

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
    def _visit_window_after(after: datetime):
        return Q(checkout_date_time__gte=after) | Q(
            checkout_date_time__isnull=True, scheduled_date__gte=after
        )

    @staticmethod
    def _visit_window_before(before: datetime):
        return Q(checkout_date_time__lt=before) | Q(
            checkout_date_time__isnull=True, scheduled_date__lt=before
        )

    @classmethod
    def _apply_filters(cls, qs, status_in, scheduled_after, scheduled_before, is_group):
        if status_in:
            qs = qs.filter(status__in=list(status_in))
        if scheduled_after is not None:
            qs = qs.filter(cls._visit_window_after(scheduled_after))
        if scheduled_before is not None:
            qs = qs.filter(cls._visit_window_before(scheduled_before))
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

    def count_checked_in_between(self, start: datetime, end: datetime) -> int:
        return VisitorAccessModel.objects.filter(
            status=VisitorAccessModel.Status.CHECKED_IN,
            updated_at__gte=start,
            updated_at__lt=end,
        ).count()

    def count_with_scheduled_after(
        self,
        after: datetime,
        *,
        status_in: Iterable[str] | None = None,
        exclude_statuses: Iterable[str] | None = None,
    ) -> int:
        qs = VisitorAccessModel.objects.filter(self._visit_window_after(after))
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
            .filter(self._visit_window_after(after))
            .order_by("scheduled_date")
        )
        if status_in:
            qs = qs.filter(status__in=list(status_in))
        if exclude_statuses:
            qs = qs.exclude(status__in=list(exclude_statuses))
        return qs[:limit]
