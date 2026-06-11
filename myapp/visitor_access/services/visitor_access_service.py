"""Business rules for visitor access."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from django.utils import timezone

from shared.exceptions import BusinessRuleError, NotFoundError
from shared.infrastructure.code_generator import ICodeGenerator
from shared.infrastructure.email_sender import IEmailSender
from shared.infrastructure.string_mixer import IStringMixer
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
    def delete(self, user, pk: int) -> VisitorAccessModel: ...

    @abstractmethod
    def checkin(self, mixed_link: str): ...

    @abstractmethod
    def checkout(self, mixed_link: str): ...


class VisitorAccessService(IVisitorAccessService):
    DEFAULT_VISIT_DURATION = timedelta(hours=3)
    CHECKOUT_WINDOW = timedelta(hours=10)

    Status = VisitorAccessModel.Status

    def __init__(
        self,
        repository: IVisitorAccessRepository,
        group_repository: IVisitorGroupRepository,
        email_sender: IEmailSender,
        code_generator: ICodeGenerator,
        string_mixer: IStringMixer,
        visitor_access_base_url: str,
    ):
        self._repo = repository
        self._group_repo = group_repository
        self._email = email_sender
        self._codes = code_generator
        self._mixer = string_mixer
        self._base_url = visitor_access_base_url

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

        if user.is_staff:
            return self._repo.list_all(
                status_in=status_in,
                scheduled_after=scheduled_after,
                scheduled_before=scheduled_before,
                is_group=is_group,
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
        if not user.is_staff and instance.host_user_id != user.id:
            raise NotFoundError("No visitor access matches the given query.")
        return instance

    # ------------------------------------------------------------------ #
    # create                                                             #
    # ------------------------------------------------------------------ #
    def create(self, user, payload: dict):
        data = dict(payload)
        scheduled_date = data.get("scheduled_date")
        if scheduled_date and scheduled_date < timezone.now():
            # all_day visits scheduled "today" are still allowed: the window is
            # the entire day, so the past-date check uses date granularity.
            if data.get("all_day"):
                if scheduled_date.date() < timezone.now().date():
                    raise BusinessRuleError(
                        "You can not create a visitor access with a past date.",
                        field="Scheduled_date",
                    )
            else:
                raise BusinessRuleError(
                    "You can not create a visitor access with a past date.",
                    field="Scheduled_date",
                )

        if user.is_staff:
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

        all_day = bool(data.get("all_day"))
        if all_day:
            # the day boundary is in the project's local timezone, so a visit
            # scheduled for "today" covers 00:00 → 23:59:59 local time.
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
        # placeholders, filled after insert (need id for the link)
        data.setdefault("link_checkin", "")
        data.setdefault("link_checkout", "")

        instance = self._repo.create(data)

        if instance.checkout_date_time is None:
            instance.checkout_date_time = (
                instance.checkin_date_time + self.DEFAULT_VISIT_DURATION
            )

        mixed = self._mixer.mix(str(instance.id))
        instance.link_checkin = f"{self._base_url}/checkin/{mixed}"

        for to_email, name in self._invite_recipients(instance):
            self._email.send_visitor_invite(
                to_email=to_email,
                link=instance.link_checkin,
                user_name=instance.host_user,
                datetime_checkin=instance.checkin_date_time,
                visitor_name=name,
            )

        return self._repo.save(instance)

    # ------------------------------------------------------------------ #
    # delete = soft cancel                                               #
    # ------------------------------------------------------------------ #
    def delete(self, user, pk):
        instance = self.get_for(user, pk)
        if instance.scheduled_date < timezone.now():
            raise BusinessRuleError("You can not cancel a past visitor access.")
        if instance.status == self.Status.CANCELLED:
            raise BusinessRuleError("This visitor access is already cancelled.")
        if instance.status == self.Status.CHECKED_OUT:
            raise BusinessRuleError(
                "You can not cancel a visit that is already concluded."
            )
        instance.status = self.Status.CANCELLED
        return self._repo.save(instance)

    # ------------------------------------------------------------------ #
    # check-in / check-out                                               #
    # ------------------------------------------------------------------ #
    def checkin(self, mixed_link: str):
        obj_id = self._mixer.unmix(mixed_link)
        instance = self._repo.get_by_id(obj_id)
        if not instance:
            raise NotFoundError("Visitor access not found.")

        if instance.status == self.Status.CANCELLED:
            raise BusinessRuleError("This visitor access has been cancelled.")
        if instance.status == self.Status.CHECKED_OUT:
            raise BusinessRuleError(f"You already {instance.status}")

        now = timezone.now()
        if instance.checkin_date_time < now < instance.checkout_date_time:
            if instance.checkin_code:
                return {"checkin_code": instance.checkin_code}

            code = self._codes.five_digits()
            instance.checkin_code = code
            instance.status = self.Status.CHECKED_IN
            self._repo.save(instance)

            for to_email, name in self._notification_recipients(instance):
                self._email.send_checkin_notification(
                    to_email=to_email,
                    user_name=instance.host_user,
                    visitor_name=name,
                )
            return {"checkin_code": code}

        return "Please checkin just in your scheduled time"

    def checkout(self, mixed_link: str):
        obj_id = self._mixer.unmix(mixed_link)
        instance = self._repo.get_by_id(obj_id)
        if not instance:
            raise NotFoundError("Visitor access not found.")

        if instance.status == self.Status.CANCELLED:
            raise BusinessRuleError("This visitor access has been cancelled.")
        if instance.status == self.Status.SCHEDULED:
            raise BusinessRuleError(
                "You can not check-out because you did not checked-in"
            )

        if (instance.scheduled_date - timezone.now()) < self.CHECKOUT_WINDOW:
            if instance.checkout_code:
                return {"checkout_code": instance.checkout_code}

            code = self._codes.five_digits()
            instance.checkout_code = code
            instance.status = self.Status.CHECKED_OUT
            self._repo.save(instance)

            for to_email, name in self._notification_recipients(instance):
                self._email.send_checkout_notification(
                    to_email=to_email,
                    user_name=instance.host_user,
                    visitor_name=name,
                )
            return {"checkout_code": code}

        return None

    # ------------------------------------------------------------------ #
    # recipients helpers                                                 #
    # ------------------------------------------------------------------ #
    def _invite_recipients(self, instance) -> list[tuple[str, str]]:
        """(email, visitor_name) tuples for the visitor invite email.

        Group visits send one personalized invite per member; solo visits
        send a single email to ``instance.email``.
        """
        if instance.visitor_group_id:
            members = self._group_repo.list_members(instance.visitor_group_id)
            return [(m.email, m.name) for m in members if m.email]
        if instance.email:
            return [(instance.email, instance.visitor_name)]
        return []

    def _notification_recipients(self, instance) -> list[tuple[str, str]]:
        """Same expansion rule as invites, used by check-in/check-out."""
        return self._invite_recipients(instance)

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
        """Translate the user-facing filters (period, status) into the
        primitive arguments the repository understands.

        Status is the tricky bit: NO_SHOW and EXPIRED are *derived* values
        — they live as ``SCHEDULED`` / ``CHECKED_IN`` rows that crossed
        their respective windows. So filtering by them adds an extra date
        bound on top of the persisted state.
        """
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
            # only rows whose scheduled date is still in the future
            scheduled_after = cls._tighten_after(scheduled_after, now)
        elif status == Status.NO_SHOW:
            status_in = [Status.SCHEDULED]
            scheduled_before = cls._tighten_before(scheduled_before, now)
        elif status == Status.CHECKED_IN:
            # CHECKED_IN persists during the visit; it 'becomes' EXPIRED
            # only after checkout_date_time. We approximate that on the
            # listing using scheduled_date, which is good enough for the
            # main happy path: CHECKED_IN visits whose scheduled_date is
            # still ahead are definitely active.
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
        """Keep the most restrictive ``scheduled_date >= X`` bound."""
        return candidate if current is None else max(current, candidate)

    @staticmethod
    def _tighten_before(
        current: datetime | None, candidate: datetime
    ) -> datetime:
        """Keep the most restrictive ``scheduled_date < X`` bound."""
        return candidate if current is None else min(current, candidate)
