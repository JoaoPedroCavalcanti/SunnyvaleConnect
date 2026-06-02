"""Dumb repository for HouseholdMembership. Pure ORM access."""

from abc import ABC, abstractmethod
from typing import Iterable

from django.utils import timezone

from households.models import HouseholdMembership


class IMembershipRepository(ABC):
    @abstractmethod
    def get_by_id(self, pk: int) -> HouseholdMembership | None: ...

    @abstractmethod
    def list_for_household(self, household_id: int) -> Iterable[HouseholdMembership]: ...

    @abstractmethod
    def list_active_for_household(
        self, household_id: int
    ) -> Iterable[HouseholdMembership]: ...

    @abstractmethod
    def list_active_holders(
        self, household_id: int
    ) -> Iterable[HouseholdMembership]: ...

    @abstractmethod
    def list_active_for_user(self, user_id: int) -> Iterable[HouseholdMembership]: ...

    @abstractmethod
    def list_pending_for_user(self, user_id: int) -> Iterable[HouseholdMembership]: ...

    @abstractmethod
    def list_pending_admin(self) -> Iterable[HouseholdMembership]: ...

    @abstractmethod
    def list_pending_holder_for_houses_of(
        self, holder_user_id: int
    ) -> Iterable[HouseholdMembership]: ...

    @abstractmethod
    def get_for_user_and_household(
        self, user_id: int, household_id: int
    ) -> HouseholdMembership | None: ...

    @abstractmethod
    def create(self, data: dict) -> HouseholdMembership: ...

    @abstractmethod
    def update(
        self, instance: HouseholdMembership, data: dict
    ) -> HouseholdMembership: ...

    @abstractmethod
    def soft_leave(self, instance: HouseholdMembership) -> HouseholdMembership: ...

    @abstractmethod
    def delete(self, instance: HouseholdMembership) -> None: ...


class DjangoMembershipRepository(IMembershipRepository):
    _ACTIVE = HouseholdMembership.Status.ACTIVE

    def get_by_id(self, pk):
        return HouseholdMembership.objects.filter(pk=pk).first()

    def list_for_household(self, household_id):
        return HouseholdMembership.objects.filter(
            household_id=household_id
        ).order_by("status", "role", "id")

    def list_active_for_household(self, household_id):
        return HouseholdMembership.objects.filter(
            household_id=household_id, status=self._ACTIVE
        ).order_by("role", "id")

    def list_active_holders(self, household_id):
        return HouseholdMembership.objects.filter(
            household_id=household_id,
            status=self._ACTIVE,
            role=HouseholdMembership.Role.HOLDER,
        )

    def list_active_for_user(self, user_id):
        return HouseholdMembership.objects.filter(
            user_id=user_id, status=self._ACTIVE
        )

    def list_pending_for_user(self, user_id):
        return HouseholdMembership.objects.filter(
            user_id=user_id,
            status__in=[
                HouseholdMembership.Status.PENDING_HOLDER,
                HouseholdMembership.Status.PENDING_ADMIN,
            ],
        )

    def list_pending_admin(self):
        return (
            HouseholdMembership.objects.filter(
                status=HouseholdMembership.Status.PENDING_ADMIN
            )
            .select_related("household", "user")
            .order_by("id")
        )

    def list_pending_holder_for_houses_of(self, holder_user_id):
        holder_household_ids = HouseholdMembership.objects.filter(
            user_id=holder_user_id,
            status=self._ACTIVE,
            role=HouseholdMembership.Role.HOLDER,
        ).values_list("household_id", flat=True)
        return (
            HouseholdMembership.objects.filter(
                household_id__in=list(holder_household_ids),
                status=HouseholdMembership.Status.PENDING_HOLDER,
            )
            .select_related("household", "user")
            .order_by("id")
        )

    def get_for_user_and_household(self, user_id, household_id):
        return HouseholdMembership.objects.filter(
            user_id=user_id, household_id=household_id
        ).first()

    def create(self, data):
        return HouseholdMembership.objects.create(**data)

    def update(self, instance, data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def soft_leave(self, instance):
        instance.status = HouseholdMembership.Status.LEFT
        instance.left_at = timezone.now()
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()
