"""Orchestrates anonymous signup with an optional household request."""

from abc import ABC, abstractmethod

from django.db import transaction

from condominiums.services.condominium_service import ICondominiumService
from households.services.household_service import IHouseholdService
from households.services.membership_service import IMembershipService
from shared.exceptions import BusinessRuleError
from users.models import UserRole
from users.services.user_service import IUserService


_HOUSEHOLD_REQUEST_KINDS = {"join_existing", "create_new"}


class ISignupService(ABC):
    @abstractmethod
    def signup(
        self,
        requester,
        user_payload: dict,
        household_request: dict | None,
    ): ...


class SignupService(ISignupService):
    def __init__(
        self,
        user_service: IUserService,
        household_service: IHouseholdService,
        membership_service: IMembershipService,
        condominium_service: ICondominiumService,
    ):
        self._users = user_service
        self._households = household_service
        self._memberships = membership_service
        self._condominiums = condominium_service

    def signup(self, requester, user_payload, household_request):
        role = user_payload.get("role", UserRole.RESIDENT)
        if role != UserRole.RESIDENT and household_request is not None:
            raise BusinessRuleError(
                "Non-resident users cannot have a household_request.",
                field="household_request",
            )

        data = dict(user_payload)
        is_anonymous = requester is None or not getattr(
            requester, "is_authenticated", False
        )
        if is_anonymous:
            condominium_code = data.pop("condominium_code", None)
            if not condominium_code:
                raise BusinessRuleError(
                    "condominium_code is required for signup.",
                    field="condominium_code",
                )
            condominium = self._condominiums.resolve_for_signup(condominium_code)
            data["condominium_id"] = condominium.id
            data["condominium_code"] = condominium.code
        elif getattr(requester, "is_superuser", False):
            if "condominium_id" not in data and "condominium_code" in data:
                condominium = self._condominiums.resolve_for_signup(
                    data.pop("condominium_code")
                )
                data["condominium_id"] = condominium.id
                data["condominium_code"] = condominium.code
        else:
            data["condominium_id"] = requester.condominium_id
            data["condominium_code"] = requester.condominium.code

        normalized = self._normalize_request(household_request)

        with transaction.atomic():
            user_data = self._merge_household_location(
                data, normalized, data["condominium_id"]
            )

            user = self._users.create(
                requester,
                user_data,
                is_active=normalized is None,
            )

            if normalized is None:
                return user

            kind = normalized["kind"]
            if kind == "join_existing":
                self._memberships.request_join(user, normalized["household_id"])
            else:
                self._households.request_create(
                    user,
                    apartment=normalized["apartment"],
                    block=normalized["block"],
                )

            return user

    def _merge_household_location(
        self, user_data: dict, normalized: dict | None, condominium_id: int
    ) -> dict:
        if normalized is None:
            return user_data

        if normalized["kind"] == "create_new":
            user_data["apartment"] = normalized["apartment"]
            user_data["block"] = normalized["block"]
            return user_data

        household = self._households.peek(
            normalized["household_id"], condominium_id=condominium_id
        )
        if household:
            user_data["apartment"] = household.apartment
            user_data["block"] = household.block
        return user_data

    def _normalize_request(self, household_request: dict | None) -> dict | None:
        if household_request is None:
            return None

        if "household_id" in household_request and household_request["household_id"]:
            return {
                "kind": "join_existing",
                "household_id": household_request["household_id"],
            }

        apartment = (household_request.get("apartment") or "").strip()
        block = (household_request.get("block") or "").strip()
        if apartment:
            return {
                "kind": "create_new",
                "apartment": apartment,
                "block": block,
            }

        raise BusinessRuleError(
            "household_request must provide either household_id or apartment.",
            field="household_request",
        )

    KINDS = _HOUSEHOLD_REQUEST_KINDS
