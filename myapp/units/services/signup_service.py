"""Orchestrates signup with an optional unit join request."""

from abc import ABC, abstractmethod

from django.db import transaction

from condominiums.services.condominium_service import ICondominiumService
from units.services.unit_membership_service import IUnitMembershipService
from shared.exceptions import BusinessRuleError
from users.models import UserRole
from users.services.user_service import IUserService


class ISignupService(ABC):
    @abstractmethod
    def signup(
        self,
        requester,
        user_payload: dict,
        unit_request: dict | None,
    ): ...


class SignupService(ISignupService):
    def __init__(
        self,
        user_service: IUserService,
        membership_service: IUnitMembershipService,
        condominium_service: ICondominiumService,
    ):
        self._users = user_service
        self._memberships = membership_service
        self._condominiums = condominium_service

    def signup(self, requester, user_payload, unit_request):
        role = user_payload.get("role", UserRole.RESIDENT)
        if role != UserRole.RESIDENT and unit_request is not None:
            raise BusinessRuleError(
                "Non-resident users cannot have a unit_request.",
                field="unit_request",
            )

        data = dict(user_payload)
        is_anonymous = requester is None or not getattr(
            requester, "is_authenticated", False
        )
        if (
            not is_anonymous
            and getattr(requester, "is_staff", False)
            and role == UserRole.RESIDENT
            and unit_request is None
        ):
            raise BusinessRuleError(
                "unit_request is required when an admin creates a resident.",
                field="unit_request",
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

        normalized = self._normalize_request(unit_request)
        is_staff_provision = (
            not is_anonymous
            and getattr(requester, "is_staff", False)
            and role == UserRole.RESIDENT
            and normalized is not None
        )

        with transaction.atomic():
            user = self._users.create(
                requester,
                data,
                is_active=normalized is None or is_staff_provision,
            )

            if normalized is None:
                return user

            if is_staff_provision:
                self._memberships.provision_join(
                    requester, user, normalized["unit_id"]
                )
            else:
                self._memberships.request_join(user, normalized["unit_id"])
                self._memberships.send_verification_code(user)

            return user

    def _normalize_request(self, unit_request: dict | None) -> dict | None:
        if unit_request is None:
            return None

        unit_id = unit_request.get("unit_id")
        if unit_id:
            return {"unit_id": unit_id}

        raise BusinessRuleError(
            "unit_request must provide unit_id.",
            field="unit_request",
        )
