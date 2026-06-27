"""Business rules for service requests.

Workflow:
  • Residents and admins open requests (always PENDING). Employees cannot.
  • Any authenticated user can list and read every request.
  • The owner can edit / delete only while PENDING.
  • Admins and cleaning employees respond (accept/decline) with a message.
  • Admins and cleaning employees may mark ACCEPTED requests COMPLETED.
  • Cleaning staff can filter list with ``mine=true`` (responded_by = caller).
  • Only the employee who accepted (or an admin) may complete a request.
"""

from abc import ABC, abstractmethod

from django.utils import timezone

from service_requests.models import ServiceRequestModel
from service_requests.repositories.service_request_repository import (
    IServiceRequestRepository,
)
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.infrastructure.email_sender import IEmailSender
from shared.roles import can_manage_service_requests, is_admin, is_employee


class IServiceRequestService(ABC):
    @abstractmethod
    def list(
        self,
        user,
        status: str | None = None,
        priority: str | None = None,
        service_type: str | None = None,
        mine: bool = False,
    ): ...

    @abstractmethod
    def get(self, user, pk: int) -> ServiceRequestModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> ServiceRequestModel: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> ServiceRequestModel: ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...

    @abstractmethod
    def respond(
        self, operator, pk: int, action: str, response: str
    ) -> ServiceRequestModel: ...

    @abstractmethod
    def complete(self, operator, pk: int) -> ServiceRequestModel: ...


class ServiceRequestService(IServiceRequestService):
    _VALID_ACTIONS = ("accept", "decline")

    def __init__(
        self,
        repository: IServiceRequestRepository,
        email_sender: IEmailSender,
    ):
        self._repo = repository
        self._email = email_sender

    def list(
        self,
        user,
        status: str | None = None,
        priority: str | None = None,
        service_type: str | None = None,
        mine: bool = False,
    ):
        status = self._normalize_choice(
            status, ServiceRequestModel.Status, "status"
        )
        priority = self._normalize_choice(
            priority, ServiceRequestModel.Priority, "priority"
        )
        service_type = self._normalize_choice(
            service_type, ServiceRequestModel.ServiceType, "service_type"
        )
        responded_by_id = None
        if mine:
            if not can_manage_service_requests(user):
                raise PermissionDeniedError(
                    "Only admins or cleaning staff can filter by mine."
                )
            responded_by_id = user.id
        return self._repo.list_all(
            status=status,
            priority=priority,
            service_type=service_type,
            responded_by_id=responded_by_id,
        )

    def get(self, user, pk):
        return self._fetch_or_404(pk)

    def create(self, user, payload: dict):
        if is_employee(user):
            raise PermissionDeniedError(
                "Employees cannot open service requests."
            )
        data = dict(payload or {})
        data["requester"] = user
        data["status"] = ServiceRequestModel.Status.PENDING
        for field in ("admin_response", "responded_by", "responded_at"):
            data.pop(field, None)
        return self._repo.create(data)

    def update(self, user, pk, payload):
        if not payload:
            raise BusinessRuleError("Empty payload.")
        instance = self.get(user, pk)

        if not is_admin(user):
            if instance.requester_id != user.id:
                raise PermissionDeniedError(
                    "You can only edit your own service requests."
                )
            if instance.status != ServiceRequestModel.Status.PENDING:
                raise BusinessRuleError(
                    "You can only edit a request while it is pending."
                )
            forbidden = {
                "status",
                "admin_response",
                "responded_by",
                "responded_at",
                "requester",
            }
            for field in forbidden:
                payload.pop(field, None)

        return self._repo.update(instance, payload)

    def delete(self, user, pk):
        instance = self.get(user, pk)
        if not is_admin(user):
            if instance.requester_id != user.id:
                raise PermissionDeniedError(
                    "You can only delete your own service requests."
                )
            if instance.status != ServiceRequestModel.Status.PENDING:
                raise BusinessRuleError(
                    "You can only delete a request while it is pending."
                )
        self._repo.delete(instance)

    def respond(self, operator, pk, action, response):
        if not can_manage_service_requests(operator):
            raise PermissionDeniedError(
                "Only admins or cleaning staff can respond to a service request."
            )
        if action not in self._VALID_ACTIONS:
            raise BusinessRuleError(
                f"Invalid action. Expected one of {list(self._VALID_ACTIONS)}.",
                field="action",
            )
        message = (response or "").strip()
        if action == "decline" and not message:
            raise BusinessRuleError(
                "A justification is required when declining.",
                field="response",
            )

        instance = self._fetch_or_404(pk)
        if instance.status != ServiceRequestModel.Status.PENDING:
            raise BusinessRuleError(
                "This request has already been answered.", field="status"
            )

        new_status = (
            ServiceRequestModel.Status.ACCEPTED
            if action == "accept"
            else ServiceRequestModel.Status.DECLINED
        )
        updated = self._repo.update(
            instance,
            {
                "status": new_status,
                "admin_response": message,
                "responded_by": operator,
                "responded_at": timezone.now(),
            },
        )
        self._notify_requester(updated, action, operator)
        return updated

    def complete(self, operator, pk):
        if not can_manage_service_requests(operator):
            raise PermissionDeniedError(
                "Only admins or cleaning staff can complete a service request."
            )
        instance = self._fetch_or_404(pk)
        if instance.status != ServiceRequestModel.Status.ACCEPTED:
            raise BusinessRuleError(
                "Only accepted requests can be marked completed.",
                field="status",
            )
        if not is_admin(operator) and instance.responded_by_id != operator.id:
            raise PermissionDeniedError(
                "You can only complete service requests you accepted."
            )
        return self._repo.update(
            instance, {"status": ServiceRequestModel.Status.COMPLETED}
        )

    def _notify_requester(self, instance, action: str, operator) -> None:
        requester = instance.requester
        if not requester or not getattr(requester, "email", ""):
            return
        self._email.send_service_request_responded(
            to_email=requester.email,
            requester_name=getattr(requester, "full_name", "") or requester.username,
            title=instance.title,
            action=action,
            response=instance.admin_response,
            responder_name=getattr(operator, "full_name", "") or operator.username,
        )

    def _fetch_or_404(self, pk: int) -> ServiceRequestModel:
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No service request matches the given query.")
        return instance

    @staticmethod
    def _normalize_choice(value, enum_cls, field_name: str) -> str | None:
        if not value:
            return None
        upper = str(value).upper()
        valid = {c.value for c in enum_cls}
        if upper not in valid:
            raise BusinessRuleError(
                f"Invalid {field_name}: {value!r}. Expected one of {sorted(valid)}.",
                field=field_name,
            )
        return upper
