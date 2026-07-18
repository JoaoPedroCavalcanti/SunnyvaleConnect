"""Business rules for visitor access."""

import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from django.utils import timezone

from shared.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from shared.infrastructure.code_generator import ICodeGenerator
from shared.infrastructure.email_sender import IEmailSender
from shared.infrastructure.qr_encoder import IQRCodeEncoder
from shared.roles import can_doorman_ops, can_see_all_visits, ensure_not_employee, is_admin
from shared.tenant import assert_same_condominium, require_condominium_id
from visitor_access.models import VisitorAccessModel
from visitor_access.repositories.visitor_access_repository import (
    IVisitorAccessRepository,
)
from visitor_access.repositories.visitor_group_repository import (
    IVisitorGroupRepository,
)


# Periods accepted on the listing endpoint, compared against
# ``scheduled_date`` vs ``timezone.now()``.
_PERIOD_FUTURE = "future"
_PERIOD_PAST = "past"
_VALID_PERIODS = (_PERIOD_FUTURE, _PERIOD_PAST)
_ACCESS_CODE_LENGTH = 5
_QR_PAYLOAD_PREFIX = "svconnect:visitor:"


class IVisitorAccessService(ABC):
    @abstractmethod
    def list_for(
        self,
        user,
        period: str | None = None,
        status: str | None = None,
        is_group: bool | None = None,
    ): ...

    @abstractmethod
    def get_for(self, user, pk: int) -> VisitorAccessModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> VisitorAccessModel: ...

    @abstractmethod
    def update(
        self, user, pk: int, payload: dict
    ) -> VisitorAccessModel: ...

    @abstractmethod
    def create_group_visits(self, user, payload: dict) -> list[VisitorAccessModel]: ...

    @abstractmethod
    def delete(self, user, pk: int) -> VisitorAccessModel: ...

    @abstractmethod
    def validate_access(self, user, credential: str) -> VisitorAccessModel: ...

    @abstractmethod
    def notify_arrival(self, user, pk: int) -> VisitorAccessModel: ...


class VisitorAccessService(IVisitorAccessService):
    DEFAULT_VISIT_DURATION = timedelta(hours=3)

    Status = VisitorAccessModel.Status

    def __init__(
        self,
        repository: IVisitorAccessRepository,
        group_repository: IVisitorGroupRepository,
        email_sender: IEmailSender,
        code_generator: ICodeGenerator,
        qr_encoder: IQRCodeEncoder,
    ):
        self._repo = repository
        self._group_repo = group_repository
        self._email = email_sender
        self._codes = code_generator
        self._qr = qr_encoder

    # ------------------------------------------------------------------ #
    # listing                                                            #
    # ------------------------------------------------------------------ #
    def list_for(
        self,
        user,
        period: str | None = None,
        status: str | None = None,
        is_group: bool | None = None,
    ):
        period = self._normalize_period(period)
        status = self._normalize_status(status)
        now = timezone.now()

        scheduled_after, scheduled_before, status_in = self._build_list_filters(
            now=now, period=period, status=status
        )

        if can_see_all_visits(user):
            return self._repo.list_all(
                status_in=status_in,
                scheduled_after=scheduled_after,
                scheduled_before=scheduled_before,
                is_group=is_group,
                condominium_id=require_condominium_id(user),
            )
        return self._repo.list_for_user(
            user.id,
            status_in=status_in,
            scheduled_after=scheduled_after,
            scheduled_before=scheduled_before,
            is_group=is_group,
        )

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No visitor access matches the given query.")
        assert_same_condominium(user, instance.host_user.condominium_id)
        if not can_see_all_visits(user) and instance.host_user_id != user.id:
            raise NotFoundError("No visitor access matches the given query.")
        return instance

    def update(self, user, pk, payload):
        ensure_not_employee(user, action="edit visits")
        instance = self.get_for(user, pk)
        self._require_future_scheduled(instance, action="edited")

        data = dict(payload)
        scheduled_date = data.get(
            "scheduled_date", instance.scheduled_date
        )
        all_day = data.get("all_day", instance.all_day)
        validation_data = {
            "host_user": instance.host_user,
            "email": data.get("email", instance.email),
            "scheduled_date": scheduled_date,
            "all_day": all_day,
        }
        self._validate_create_payload(
            user,
            validation_data,
            bool(instance.qr_access_enabled),
        )

        if "scheduled_date" in data or "all_day" in data:
            if all_day:
                local = timezone.localtime(scheduled_date)
                day_start = local.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                day_end = local.replace(
                    hour=23, minute=59, second=59, microsecond=0
                )
                data["scheduled_date"] = day_start
                data["checkin_date_time"] = day_start
                data["checkout_date_time"] = day_end
            else:
                data["scheduled_date"] = scheduled_date
                data["checkin_date_time"] = scheduled_date
                data.setdefault(
                    "checkout_date_time",
                    scheduled_date + self.DEFAULT_VISIT_DURATION,
                )

        effective_checkin = data.get(
            "checkin_date_time", instance.checkin_date_time
        )
        effective_checkout = data.get(
            "checkout_date_time", instance.checkout_date_time
        )
        if (
            effective_checkout is not None
            and effective_checkin is not None
            and effective_checkout <= effective_checkin
        ):
            raise BusinessRuleError(
                "checkout_date_time must be after scheduled_date.",
                field="checkout_date_time",
            )
        return self._repo.update(instance, data)

    # ------------------------------------------------------------------ #
    # create                                                             #
    # ------------------------------------------------------------------ #
    def create(self, user, payload: dict):
        ensure_not_employee(user, action="register visitors")
        data = dict(payload)
        qr_access_enabled = bool(data.pop("qr_access_enabled", False))
        self._validate_create_payload(user, data, qr_access_enabled)
        return self._persist_visit(user, data, qr_access_enabled)

    def create_group_visits(self, user, payload: dict) -> list[VisitorAccessModel]:
        ensure_not_employee(user, action="register visitors")
        data = dict(payload)
        qr_access_enabled = bool(data.pop("qr_access_enabled", False))
        group = data.get("visitor_group")
        if not group:
            raise BusinessRuleError(
                "visitor_group is required.", field="visitor_group"
            )

        members = self._group_repo.list_members(group.id)
        if not members:
            raise BusinessRuleError(
                "This group has no members. Add members before scheduling a visit."
            )

        self._validate_create_payload(
            user, data, qr_access_enabled, group_members=members
        )

        visits: list[VisitorAccessModel] = []
        for member in members:
            member_data = dict(data)
            member_data["visitor_name"] = member.name
            member_data["email"] = member.email or ""
            visits.append(self._persist_visit(user, member_data, qr_access_enabled))
        return visits

    def _validate_create_payload(
        self,
        user,
        data: dict,
        qr_access_enabled: bool,
        *,
        group_members=None,
    ) -> None:
        scheduled_date = data.get("scheduled_date")
        if scheduled_date and scheduled_date < timezone.now():
            if data.get("all_day"):
                if scheduled_date.date() < timezone.localdate():
                    raise BusinessRuleError(
                        "You can not create a visitor access with a past date.",
                        field="Scheduled_date",
                    )
            else:
                raise BusinessRuleError(
                    "You can not create a visitor access with a past date.",
                    field="Scheduled_date",
                )

        if is_admin(user):
            if not data.get("host_user"):
                raise BusinessRuleError(
                    "Selecione o morador anfitrião da visita.",
                    field="host_user",
                )
        else:
            passed = data.get("host_user")
            if passed and passed.id != user.id:
                raise BusinessRuleError(
                    "Você só pode cadastrar visitas em seu próprio nome.",
                    field="host_user",
                )
            data["host_user"] = user

        if qr_access_enabled:
            if group_members is not None:
                if any(not (m.email or "").strip() for m in group_members):
                    raise BusinessRuleError(
                        "QR access requires an email for every group member.",
                        field="email",
                    )
            elif not (data.get("email") or "").strip():
                raise BusinessRuleError(
                    "QR access requires a visitor email.",
                    field="email",
                )

    def _persist_visit(self, user, data: dict, qr_access_enabled: bool):
        scheduled_date = data.get("scheduled_date")
        all_day = bool(data.get("all_day"))
        if all_day:
            local = timezone.localtime(scheduled_date)
            day_start = local.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = local.replace(hour=23, minute=59, second=59, microsecond=0)
            data["scheduled_date"] = day_start
            data["checkin_date_time"] = day_start
            data["checkout_date_time"] = day_end
        else:
            data["checkin_date_time"] = scheduled_date

        data["status"] = self.Status.SCHEDULED
        data.setdefault("checkin_code", "")
        data.setdefault("checkout_code", "")
        data["qr_access_enabled"] = qr_access_enabled
        data["access_token"] = None
        data["access_code"] = None

        if qr_access_enabled:
            data["access_token"] = self._generate_unique_token()
            data["access_code"] = self._generate_unique_code()

        instance = self._repo.create(data)

        if instance.checkout_date_time is None:
            instance.checkout_date_time = (
                instance.checkin_date_time + self.DEFAULT_VISIT_DURATION
            )

        saved = self._repo.save(instance)

        if qr_access_enabled and saved.email:
            try:
                qr_png = self._qr.encode_png(self._qr_payload(saved.access_token))
                self._email.send_visitor_qr_access(
                    to_email=saved.email,
                    access_code=saved.access_code,
                    qr_png=qr_png,
                    user_name=saved.host_user,
                    datetime_checkin=saved.checkin_date_time,
                    datetime_checkout=saved.checkout_date_time,
                    visitor_name=saved.visitor_name,
                )
            except Exception as exc:
                self._repo.delete(saved)
                raise BusinessRuleError(
                    "Could not send the visitor QR access email.",
                    field="email",
                ) from exc

        return saved

    # ------------------------------------------------------------------ #
    # delete = soft cancel                                               #
    # ------------------------------------------------------------------ #
    def delete(self, user, pk):
        ensure_not_employee(user, action="cancel visits")
        instance = self.get_for(user, pk)
        self._require_future_scheduled(instance, action="cancelled")
        instance.status = self.Status.CANCELLED
        return self._repo.save(instance)

    def _require_future_scheduled(self, instance, *, action: str) -> None:
        if instance.status != self.Status.SCHEDULED:
            raise BusinessRuleError(
                f"Only scheduled visits can be {action}.",
                field="status",
            )
        if instance.scheduled_date <= timezone.now():
            raise BusinessRuleError(
                f"Past visits cannot be {action}.",
                field="scheduled_date",
            )

    # ------------------------------------------------------------------ #
    # doorman validation (QR or manual code)                             #
    # ------------------------------------------------------------------ #
    def validate_access(self, user, credential: str) -> VisitorAccessModel:
        if not can_doorman_ops(user):
            raise PermissionDeniedError(
                "Only admins or doorman staff can validate visitor access."
            )

        credential = (credential or "").strip()
        if not credential:
            raise BusinessRuleError("Credential is required.", field="credential")

        instance = self._resolve_credential(credential)
        if not instance:
            raise NotFoundError("No visitor access matches the given credential.")

        if not instance.qr_access_enabled:
            raise BusinessRuleError("This visit does not use QR access.")

        if instance.status == self.Status.CANCELLED:
            raise BusinessRuleError("This visitor access has been cancelled.")
        if instance.status == self.Status.CHECKED_IN:
            raise BusinessRuleError("This access has already been used.")
        if instance.status == self.Status.CHECKED_OUT:
            raise BusinessRuleError("This visit is already concluded.")

        now = timezone.now()
        if now < instance.checkin_date_time or now > instance.checkout_date_time:
            raise BusinessRuleError(
                "Visit is outside the allowed check-in window.",
                field="credential",
            )

        instance.status = self.Status.CHECKED_IN
        instance.checkin_code = instance.access_code or ""
        saved = self._repo.save(instance)

        for to_email, name in self._notification_recipients(saved):
            self._email.send_checkin_notification(
                to_email=to_email,
                user_name=saved.host_user,
                visitor_name=name,
            )
        return saved

    def notify_arrival(self, user, pk: int) -> VisitorAccessModel:
        if not can_doorman_ops(user):
            raise PermissionDeniedError(
                "Only admins or doorman staff can notify visitor arrival."
            )
        instance = self._fetch_or_404(pk)
        if instance.status == self.Status.CANCELLED:
            raise BusinessRuleError("This visitor access has been cancelled.")
        if instance.status == self.Status.CHECKED_OUT:
            raise BusinessRuleError("This visit is already concluded.")

        host = instance.host_user
        if not host or not getattr(host, "email", ""):
            raise BusinessRuleError(
                "The host has no email registered; cannot notify arrival.",
                field="host_user",
            )

        visitor_name = instance.visitor_name
        self._email.send_visitor_arrival_notification(
            to_email=host.email,
            user_name=getattr(host, "full_name", "") or host.username,
            visitor_name=visitor_name,
        )
        return instance

    def _fetch_or_404(self, pk: int) -> VisitorAccessModel:
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No visitor access matches the given query.")
        return instance

    def _resolve_credential(self, credential: str) -> VisitorAccessModel | None:
        if credential.startswith(_QR_PAYLOAD_PREFIX):
            token = credential[len(_QR_PAYLOAD_PREFIX) :]
            return self._repo.get_by_access_token(token)
        instance = self._repo.get_by_access_token(credential)
        if instance:
            return instance
        return self._repo.get_by_access_code(credential)

    def _generate_unique_token(self) -> str:
        for _ in range(10):
            token = secrets.token_urlsafe(24)
            if not self._repo.exists_with_access_token(token):
                return token
        raise BusinessRuleError("Could not generate a unique access token.")

    def _generate_unique_code(self) -> str:
        for _ in range(20):
            code = self._codes.alphanumeric(_ACCESS_CODE_LENGTH)
            if not self._repo.exists_with_access_code(code):
                return code
        raise BusinessRuleError("Could not generate a unique access code.")

    @staticmethod
    def _qr_payload(token: str) -> str:
        return f"{_QR_PAYLOAD_PREFIX}{token}"

    def _notification_recipients(self, instance) -> list[tuple[str, str]]:
        if instance.email:
            return [(instance.email, instance.visitor_name)]
        return []

    # ------------------------------------------------------------------ #
    # filter helpers                                                     #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_period(value: str | None) -> str | None:
        if not value:
            return None
        normalized = str(value).lower()
        if normalized not in _VALID_PERIODS:
            raise BusinessRuleError(
                f"Invalid period: {value!r}. Expected one of {list(_VALID_PERIODS)}.",
                field="period",
            )
        return normalized

    @classmethod
    def _normalize_status(cls, value: str | None) -> str | None:
        if not value:
            return None
        normalized = str(value).upper()
        valid = {c.value for c in cls.Status}
        if normalized not in valid:
            raise BusinessRuleError(
                f"Invalid status: {value!r}. Expected one of {sorted(valid)}.",
                field="status",
            )
        return normalized

    @classmethod
    def _build_list_filters(
        cls,
        now: datetime,
        period: str | None,
        status: str | None,
    ) -> tuple[datetime | None, datetime | None, list[str] | None]:
        scheduled_after: datetime | None = None
        scheduled_before: datetime | None = None
        status_in: list[str] | None = None

        if period == _PERIOD_FUTURE:
            scheduled_after = now
        elif period == _PERIOD_PAST:
            scheduled_before = now

        if status is None:
            return scheduled_after, scheduled_before, status_in

        Status = cls.Status
        if status == Status.SCHEDULED:
            status_in = [Status.SCHEDULED]
            scheduled_after = cls._tighten_after(scheduled_after, now)
        elif status == Status.NO_SHOW:
            status_in = [Status.SCHEDULED]
            scheduled_before = cls._tighten_before(scheduled_before, now)
        elif status == Status.CHECKED_IN:
            status_in = [Status.CHECKED_IN]
            scheduled_after = cls._tighten_after(scheduled_after, now)
        elif status == Status.EXPIRED:
            status_in = [Status.CHECKED_IN]
            scheduled_before = cls._tighten_before(scheduled_before, now)
        elif status == Status.CHECKED_OUT:
            status_in = [Status.CHECKED_OUT]
        elif status == Status.CANCELLED:
            status_in = [Status.CANCELLED]

        return scheduled_after, scheduled_before, status_in

    @staticmethod
    def _tighten_after(
        current: datetime | None, candidate: datetime
    ) -> datetime:
        return candidate if current is None else max(current, candidate)

    @staticmethod
    def _tighten_before(
        current: datetime | None, candidate: datetime
    ) -> datetime:
        return candidate if current is None else min(current, candidate)
