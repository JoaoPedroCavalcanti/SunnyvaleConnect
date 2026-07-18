"""Dumb repository for UnitMembership. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from django.utils import timezone

from units.models import UnitMembership


class IUnitMembershipRepository(ABC):
    @abstractmethod
    def get_by_id(self, pk: int) -> UnitMembership | None: ...

    @abstractmethod
    def list_for_unit(self, unit_id: int) -> Iterable[UnitMembership]: ...

    @abstractmethod
    def list_active_for_unit(self, unit_id: int) -> Iterable[UnitMembership]: ...

    @abstractmethod
    def list_active_for_units(
        self, unit_ids: list[int]
    ) -> Iterable[UnitMembership]: ...

    @abstractmethod
    def list_active_owners(self, unit_id: int) -> Iterable[UnitMembership]: ...

    @abstractmethod
    def get_active_owner(self, unit_id: int) -> UnitMembership | None: ...

    @abstractmethod
    def list_active_for_user(self, user_id: int) -> Iterable[UnitMembership]: ...

    @abstractmethod
    def get_oldest_active_replacement(
        self, unit_id: int, excluded_user_id: int
    ) -> UnitMembership | None: ...

    @abstractmethod
    def list_pending_for_user(self, user_id: int) -> Iterable[UnitMembership]: ...

    @abstractmethod
    def list_pending_admin(
        self, *, condominium_id: int | None = None
    ) -> Iterable[UnitMembership]: ...

    @abstractmethod
    def list_pending_owner_for_units_of(
        self, owner_user_id: int
    ) -> Iterable[UnitMembership]: ...

    @abstractmethod
    def get_for_user_and_unit(
        self, user_id: int, unit_id: int
    ) -> UnitMembership | None: ...

    @abstractmethod
    def create(self, data: dict) -> UnitMembership: ...

    @abstractmethod
    def update(
        self, instance: UnitMembership, data: dict
    ) -> UnitMembership: ...

    @abstractmethod
    def soft_leave(self, instance: UnitMembership) -> UnitMembership: ...

    @abstractmethod
    def delete(self, instance: UnitMembership) -> None: ...


class DjangoUnitMembershipRepository(IUnitMembershipRepository):
    _ACTIVE = UnitMembership.Status.ACTIVE

    def get_by_id(self, pk):
        return UnitMembership.objects.filter(pk=pk).first()

    def list_for_unit(self, unit_id):
        return UnitMembership.objects.filter(unit_id=unit_id).order_by(
            "status", "role", "id"
        )

    def list_active_for_unit(self, unit_id):
        return (
            UnitMembership.objects.filter(unit_id=unit_id, status=self._ACTIVE)
            .select_related("user")
            .order_by("role", "id")
        )

    def list_active_for_units(self, unit_ids):
        if not unit_ids:
            return UnitMembership.objects.none()
        return (
            UnitMembership.objects.filter(
                unit_id__in=list(unit_ids), status=self._ACTIVE
            )
            .select_related("user")
            .order_by("unit_id", "role", "id")
        )

    def list_active_owners(self, unit_id):
        return UnitMembership.objects.filter(
            unit_id=unit_id,
            status=self._ACTIVE,
            role=UnitMembership.Role.OWNER,
        ).select_related("user")

    def get_active_owner(self, unit_id):
        return (
            UnitMembership.objects.filter(
                unit_id=unit_id,
                status=self._ACTIVE,
                role=UnitMembership.Role.OWNER,
            )
            .select_related("user")
            .first()
        )

    def list_active_for_user(self, user_id):
        return UnitMembership.objects.filter(
            user_id=user_id, status=self._ACTIVE
        ).select_related("unit")

    def get_oldest_active_replacement(self, unit_id, excluded_user_id):
        return (
            UnitMembership.objects.filter(
                unit_id=unit_id,
                status=self._ACTIVE,
                user__is_active=True,
            )
            .exclude(user_id=excluded_user_id)
            .order_by("joined_at", "id")
            .first()
        )

    def list_pending_for_user(self, user_id):
        return UnitMembership.objects.filter(
            user_id=user_id,
            status__in=[
                UnitMembership.Status.PENDING_EMAIL,
                UnitMembership.Status.PENDING_OWNER,
                UnitMembership.Status.PENDING_ADMIN,
            ],
        )

    def list_pending_admin(self, *, condominium_id=None):
        qs = UnitMembership.objects.filter(
            status=UnitMembership.Status.PENDING_ADMIN
        )
        if condominium_id is not None:
            qs = qs.filter(unit__condominium_id=condominium_id)
        return qs.select_related("unit", "user").order_by("id")

    def list_pending_owner_for_units_of(self, owner_user_id):
        owner_unit_ids = UnitMembership.objects.filter(
            user_id=owner_user_id,
            status=self._ACTIVE,
            role=UnitMembership.Role.OWNER,
        ).values_list("unit_id", flat=True)
        return (
            UnitMembership.objects.filter(
                unit_id__in=list(owner_unit_ids),
                status=UnitMembership.Status.PENDING_OWNER,
            )
            .select_related("unit", "user")
            .order_by("id")
        )

    def get_for_user_and_unit(self, user_id, unit_id):
        return UnitMembership.objects.filter(
            user_id=user_id, unit_id=unit_id
        ).first()

    def create(self, data):
        return UnitMembership.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def soft_leave(self, instance):
        instance.status = UnitMembership.Status.LEFT
        instance.left_at = timezone.now()
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()
