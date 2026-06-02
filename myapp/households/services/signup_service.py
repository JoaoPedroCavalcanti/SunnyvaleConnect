"""Orchestrates anonymous signup with an optional household request.

This is the only service that may compose multiple other services. All other
domain services stay focused on their own entity.
"""

from abc import ABC, abstractmethod

from django.db import transaction

from households.services.household_service import IHouseholdService
from households.services.membership_service import IMembershipService
from shared.exceptions import BusinessRuleError
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
    ):
        self._users = user_service
        self._households = household_service
        self._memberships = membership_service

    def signup(self, requester, user_payload, household_request):
        normalized = self._normalize_request(household_request)

        with transaction.atomic():
            user_data = self._merge_household_location(
                dict(user_payload), normalized
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

    # ---- internal helpers --------------------------------------------- #
    def _merge_household_location(
        self, user_data: dict, normalized: dict | None
    ) -> dict:
        """Denormalize household location into the User row.

        Keeps ``User.apartment`` / ``User.block`` aligned with the household
        the user is being attached to. Backwards-compat for code that still
        reads ``user.apartment`` directly (reservations, payments, etc).
        """
        if normalized is None:
            return user_data

        if normalized["kind"] == "create_new":
            user_data["apartment"] = normalized["apartment"]
            user_data["block"] = normalized["block"]
            return user_data

        # join_existing: peek the household to copy its location.
        # The membership_service will validate it again and raise if invalid.
        household = self._households.peek(normalized["household_id"])
        if household:
            user_data["apartment"] = household.apartment
            user_data["block"] = household.block
        return user_data

    # ---- internal helpers --------------------------------------------- #
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

    # Kept around so callers know which keys are valid. Not enforced at runtime
    # to avoid serializer-style validation inside the service.
    KINDS = _HOUSEHOLD_REQUEST_KINDS
