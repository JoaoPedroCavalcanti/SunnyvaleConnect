"""Orchestrates signup with an optional unit join request."""

from abc import ABC, abstractmethod
from datetime import date, datetime

from django.db import transaction

from condominiums.services.condominium_service import ICondominiumService
from units.models import Unit
from units.repositories.unit_repository import IUnitRepository
from units.services.unit_membership_service import IUnitMembershipService
from shared.exceptions import BusinessRuleError, NotFoundError
from shared.infrastructure.cache import ICache
from shared.infrastructure.code_generator import ICodeGenerator
from shared.infrastructure.email_sender import IEmailSender
from users.models import UserRole
from users.services.user_service import IUserService


_PENDING_SIGNUP_TTL_SECONDS = 15 * 60
_EMAIL_RESEND_TTL_SECONDS = 60

KIND_CREATED = "created"
KIND_PENDING_EMAIL = "pending_email_verification"


class ISignupService(ABC):
    @abstractmethod
    def signup(
        self,
        requester,
        user_payload: dict,
        unit_request: dict | None,
    ): ...

    @abstractmethod
    def confirm_email(self, email: str, code: str): ...

    @abstractmethod
    def resend_verification(self, email: str) -> None: ...


class SignupService(ISignupService):
    def __init__(
        self,
        user_service: IUserService,
        membership_service: IUnitMembershipService,
        condominium_service: ICondominiumService,
        unit_repository: IUnitRepository,
        cache: ICache,
        code_generator: ICodeGenerator,
        email_sender: IEmailSender,
    ):
        self._users = user_service
        self._memberships = membership_service
        self._condominiums = condominium_service
        self._units = unit_repository
        self._cache = cache
        self._codes = code_generator
        self._email = email_sender

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

        # Self-signup with unit: hold everything in cache until OTP is confirmed.
        if normalized is not None and not is_staff_provision:
            return self._begin_pending_signup(requester, data, normalized["unit_id"])

        with transaction.atomic():
            user = self._users.create(
                requester,
                data,
                is_active=normalized is None or is_staff_provision,
            )

            if normalized is None:
                return {"kind": KIND_CREATED, "user": user}

            self._memberships.provision_join(
                requester, user, normalized["unit_id"]
            )
            return {"kind": KIND_CREATED, "user": user}

    def confirm_email(self, email: str, code: str):
        pending = self._get_pending_or_404(email)
        if str(pending.get("code", "")) != str(code).strip():
            raise BusinessRuleError("Invalid or expired verification code.")

        fields = self._deserialize_user_fields(pending["user_fields"])
        unit_id = pending["unit_id"]

        with transaction.atomic():
            user = self._users.create_prepared(fields, is_active=False)
            membership = self._memberships.request_join(user, unit_id)

        self._cache.delete(self._pending_key(fields["email"]))
        return {"user": user, "membership": membership}

    def resend_verification(self, email: str) -> None:
        pending = self._get_pending_or_404(email)
        rate_key = self._resend_rate_key(email)
        if self._cache.get(rate_key) is not None:
            raise BusinessRuleError(
                "Please wait before requesting another verification code."
            )

        code = self._codes.six_digits()
        pending["code"] = code
        email_normalized = pending["email"]
        self._cache.set(
            self._pending_key(email_normalized),
            pending,
            _PENDING_SIGNUP_TTL_SECONDS,
        )
        fields = pending["user_fields"]
        self._email.send_email_verification_code(
            to_email=email_normalized,
            user_name=fields.get("full_name") or fields.get("username") or "",
            code=code,
        )
        self._cache.set(rate_key, "1", _EMAIL_RESEND_TTL_SECONDS)

    def _begin_pending_signup(self, requester, data: dict, unit_id: int) -> dict:
        if data.get("photo") is not None:
            raise BusinessRuleError(
                "Photo cannot be uploaded before email verification.",
                field="photo",
            )

        unit = self._units.get_by_id(unit_id)
        if not unit:
            raise NotFoundError("No unit matches the given query.")
        if unit.status != Unit.Status.ACTIVE:
            raise BusinessRuleError("This unit is not open for new members.")
        if unit.condominium_id != data.get("condominium_id"):
            raise BusinessRuleError(
                "Unit does not belong to this condominium.",
                field="unit_request",
            )

        fields = self._users.prepare_create(requester, data)
        email = fields["email"]
        if not email:
            raise BusinessRuleError(
                "Email is required for signup with a unit request.",
                field="email",
            )

        code = self._codes.six_digits()
        pending = {
            "email": email,
            "code": code,
            "unit_id": unit_id,
            "user_fields": self._serialize_user_fields(fields),
        }
        self._cache.set(
            self._pending_key(email), pending, _PENDING_SIGNUP_TTL_SECONDS
        )
        self._email.send_email_verification_code(
            to_email=email,
            user_name=fields.get("full_name") or fields.get("username") or "",
            code=code,
        )
        return {"kind": KIND_PENDING_EMAIL, "email": email}

    def _get_pending_or_404(self, email: str) -> dict:
        normalized = (email or "").lower().strip()
        pending = self._cache.get(self._pending_key(normalized))
        if not pending:
            raise NotFoundError("No pending signup matches the given query.")
        return pending

    def _pending_key(self, email: str) -> str:
        return f"pending_signup:{(email or '').lower().strip()}"

    def _resend_rate_key(self, email: str) -> str:
        return f"email_verify_resend:{(email or '').lower().strip()}"

    def _serialize_user_fields(self, fields: dict) -> dict:
        serialized = dict(fields)
        birth = serialized.get("birth_date")
        if isinstance(birth, date):
            serialized["birth_date"] = birth.isoformat()
        # Never cache uploaded files.
        serialized["photo"] = None
        return serialized

    def _deserialize_user_fields(self, fields: dict) -> dict:
        data = dict(fields)
        birth = data.get("birth_date")
        if isinstance(birth, str):
            data["birth_date"] = date.fromisoformat(birth)
        elif isinstance(birth, datetime):
            data["birth_date"] = birth.date()
        return data

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
