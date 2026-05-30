"""Business rules for visitor access."""

from abc import ABC, abstractmethod
from datetime import timedelta

from django.utils import timezone

from shared.exceptions import BusinessRuleError, NotFoundError
from shared.infrastructure.code_generator import ICodeGenerator
from shared.infrastructure.email_sender import IEmailSender
from shared.infrastructure.string_mixer import IStringMixer
from visitor_access.models import VisitorAccessModel
from visitor_access.repositories.visitor_access_repository import (
    IVisitorAccessRepository,
)


class IVisitorAccessService(ABC):
    @abstractmethod
    def list_for(self, user): ...

    @abstractmethod
    def get_for(self, user, pk: int) -> VisitorAccessModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> VisitorAccessModel: ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...

    @abstractmethod
    def checkin(self, mixed_link: str): ...

    @abstractmethod
    def checkout(self, mixed_link: str): ...


class VisitorAccessService(IVisitorAccessService):
    DEFAULT_VISIT_DURATION = timedelta(hours=3)
    CHECKOUT_WINDOW = timedelta(hours=10)

    def __init__(
        self,
        repository: IVisitorAccessRepository,
        email_sender: IEmailSender,
        code_generator: ICodeGenerator,
        string_mixer: IStringMixer,
        visitor_access_base_url: str,
    ):
        self._repo = repository
        self._email = email_sender
        self._codes = code_generator
        self._mixer = string_mixer
        self._base_url = visitor_access_base_url

    # ------------------------------------------------------------------ #
    # listing                                                            #
    # ------------------------------------------------------------------ #
    def list_for(self, user):
        if user.is_staff:
            return self._repo.list_all()
        return self._repo.list_for_user(user.id)

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
            raise BusinessRuleError(
                "You can not create a visitor access with a past date.",
                field="Scheduled_date",
            )

        if user.is_staff:
            if not data.get("host_user"):
                raise BusinessRuleError(
                    "This field is required for staff users.", field="host_user"
                )
        else:
            if data.get("host_user"):
                raise BusinessRuleError(
                    "This field is automatically set to the current user.",
                    field="host_user",
                )
            data["host_user"] = user

        data["checkin_date_time"] = scheduled_date
        data["status"] = "Scheduled"
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

        self._email.send_visitor_invite(
            to_email=instance.email,
            link=instance.link_checkin,
            user_name=instance.host_user,
            datetime_checkin=instance.checkin_date_time,
            visitor_name=instance.visitor_name,
        )

        return self._repo.save(instance)

    # ------------------------------------------------------------------ #
    # delete                                                             #
    # ------------------------------------------------------------------ #
    def delete(self, user, pk):
        instance = self.get_for(user, pk)
        if instance.scheduled_date < timezone.now():
            raise BusinessRuleError("You can not delete a past visitor access.")
        self._repo.delete(instance)

    # ------------------------------------------------------------------ #
    # check-in / check-out                                               #
    # ------------------------------------------------------------------ #
    def checkin(self, mixed_link: str):
        obj_id = self._mixer.unmix(mixed_link)
        instance = self._repo.get_by_id(obj_id)
        if not instance:
            raise NotFoundError("Visitor access not found.")

        if instance.status == "Checked-out":
            raise BusinessRuleError(f"You already {instance.status}")

        now = timezone.now()
        if instance.checkin_date_time < now < instance.checkout_date_time:
            if instance.checkin_code:
                return {"checkin_code": instance.checkin_code}

            code = self._codes.five_digits()
            instance.checkin_code = code
            instance.status = "Checked-in"
            self._repo.save(instance)

            self._email.send_checkin_notification(
                to_email=instance.email,
                user_name=instance.host_user,
                visitor_name=instance.visitor_name,
            )
            return {"checkin_code": code}

        return "Please checkin just in your scheduled time"

    def checkout(self, mixed_link: str):
        obj_id = self._mixer.unmix(mixed_link)
        instance = self._repo.get_by_id(obj_id)
        if not instance:
            raise NotFoundError("Visitor access not found.")

        if instance.status == "Scheduled":
            raise BusinessRuleError(
                "You can not check-out because you did not checked-in"
            )

        if (instance.scheduled_date - timezone.now()) < self.CHECKOUT_WINDOW:
            if instance.checkout_code:
                return {"checkout_code": instance.checkout_code}

            code = self._codes.five_digits()
            instance.checkout_code = code
            instance.status = "Checked-out"
            self._repo.save(instance)

            self._email.send_checkout_notification(
                to_email=instance.email,
                user_name=instance.host_user,
                visitor_name=instance.visitor_name,
            )
            return {"checkout_code": code}

        return None
