"""Business rules for Dependent (no-login residents)."""

from abc import ABC, abstractmethod

from households.models import Dependent, HouseholdMembership
from households.repositories.dependent_repository import IDependentRepository
from households.repositories.household_repository import IHouseholdRepository
from households.repositories.membership_repository import IMembershipRepository
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.infrastructure.document_validators import ICPFValidator
from shared.tenant import require_condominium_id
from users.repositories.user_repository import IUserRepository


class IDependentService(ABC):
    @abstractmethod
    def list_for_household(self, user, household_id: int): ...

    @abstractmethod
    def list_residents(self, user, household_id: int) -> list[dict]: ...

    @abstractmethod
    def create(self, user, household_id: int, payload: dict) -> Dependent: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> Dependent: ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...


class DependentService(IDependentService):
    def __init__(
        self,
        dependent_repository: IDependentRepository,
        membership_repository: IMembershipRepository,
        household_repository: IHouseholdRepository,
        user_repository: IUserRepository,
        cpf_validator: ICPFValidator,
    ):
        self._repo = dependent_repository
        self._memberships = membership_repository
        self._households = household_repository
        self._users = user_repository
        self._cpf = cpf_validator

    def list_for_household(self, user, household_id):
        self._require_active_member(user, household_id)
        return list(self._repo.list_for_household(household_id))

    def list_residents(self, user, household_id):
        """Returns a polymorphic list with the active household members
        first (``type="household"``) and the active dependents after
        (``type="dependent"``). Each item is ``{"type", "obj"}``.

        Same permission as the rest of the dependents endpoints: active
        member of the household, or staff.
        """
        household = self._households.get_by_id(household_id)
        if not household:
            raise NotFoundError("No household matches the given query.")
        self._require_active_member(user, household.id)

        items: list[dict] = [
            {"type": "household", "obj": m}
            for m in self._memberships.list_active_for_household(household.id)
        ]
        items += [
            {"type": "dependent", "obj": d}
            for d in self._repo.list_for_household(household.id)
        ]
        return items

    def create(self, user, household_id, payload):
        household = self._households.get_by_id(household_id)
        if not household:
            raise NotFoundError("No household matches the given query.")
        self._require_active_member(user, household.id)

        data = dict(payload)
        condominium_id = require_condominium_id(user)
        cpf_raw = data.get("cpf", "") or ""
        if cpf_raw:
            cpf = self._cpf.normalize(cpf_raw)
            cpf_error = self._cpf.validate(cpf)
            if cpf_error:
                raise BusinessRuleError(message=cpf_error, field="cpf")
            if self._users.exists_with_cpf(cpf, condominium_id=condominium_id):
                raise BusinessRuleError(
                    "A user with this CPF already exists.", field="cpf"
                )
            if self._repo.exists_active_with_cpf(cpf):
                raise BusinessRuleError(
                    "An active dependent with this CPF already exists.",
                    field="cpf",
                )
            data["cpf"] = cpf

        return self._repo.create({"household": household, **data})

    def update(self, user, pk, payload):
        dependent = self._get_or_404(pk)
        self._require_active_member(user, dependent.household_id)

        data = dict(payload)
        condominium_id = require_condominium_id(user)
        if "cpf" in data and data["cpf"]:
            cpf = self._cpf.normalize(data["cpf"])
            cpf_error = self._cpf.validate(cpf)
            if cpf_error:
                raise BusinessRuleError(message=cpf_error, field="cpf")
            if cpf != dependent.cpf:
                if self._users.exists_with_cpf(cpf, condominium_id=condominium_id):
                    raise BusinessRuleError(
                        "A user with this CPF already exists.", field="cpf"
                    )
                if self._repo.exists_active_with_cpf(cpf):
                    raise BusinessRuleError(
                        "An active dependent with this CPF already exists.",
                        field="cpf",
                    )
            data["cpf"] = cpf

        return self._repo.update(dependent, data)

    def delete(self, user, pk):
        dependent = self._get_or_404(pk)
        self._require_active_member(user, dependent.household_id)
        self._repo.soft_delete(dependent)

    # ---- internal helpers --------------------------------------------- #
    def _get_or_404(self, pk) -> Dependent:
        instance = self._repo.get_by_id(pk)
        if not instance or not instance.is_active:
            raise NotFoundError("No dependent matches the given query.")
        return instance

    def _require_active_member(self, user, household_id) -> None:
        if getattr(user, "is_staff", False):
            return
        membership = self._memberships.get_for_user_and_household(
            user.id, household_id
        )
        if (
            not membership
            or membership.status != HouseholdMembership.Status.ACTIVE
        ):
            raise PermissionDeniedError(
                "You must be an active member of this household."
            )
