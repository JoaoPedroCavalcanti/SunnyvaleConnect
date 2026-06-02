"""Business rules for service requests.

Workflow:
  • Any authenticated user opens a request (always PENDING, scoped to
    ``request.user``).
  • The owner can edit / delete *only while it is still PENDING*. Once
    an admin responds the request becomes immutable from the owner's
    perspective.
  • An admin lists every request, can apply filters (status / priority
    / service_type) and must ``respond`` with a non-empty justification
    when accepting or declining.
  • An admin may later mark an ACCEPTED request as COMPLETED.
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


class IServiceRequestService(ABC):
    @abstractmethod
    def list(
        self,
        user,
        status: str | None = None,
        priority: str | None = None,
        service_type: str | None = None,
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
        self, admin, pk: int, action: str, response: str
    ) -> ServiceRequestModel: ...

    @abstractmethod
    def complete(self, admin, pk: int) -> ServiceRequestModel: ...


class ServiceRequestService(IServiceRequestService):
    _VALID_ACTIONS = ("accept", "decline")

    def __init__(self, repository: IServiceRequestRepository):
        self._repo = repository

    # ------------------------------------------------------------------ #
    # read                                                               #
    # ------------------------------------------------------------------ #
    def list(self, user, status=None, priority=None, service_type=None):
        status = self._normalize_choice(
            status, ServiceRequestModel.Status, "status"
        )
        priority = self._normalize_choice(
            priority, ServiceRequestModel.Priority, "priority"
        )
        service_type = self._normalize_choice(
            service_type, ServiceRequestModel.ServiceType, "service_type"
        )

        if user.is_staff:
            return self._repo.list_all(
                status=status,
                priority=priority,
                service_type=service_type,
            )
        return self._repo.list_for_user(
            user.id,
            status=status,
            priority=priority,
            service_type=service_type,
        )

    def get(self, user, pk):
        instance = self._fetch_or_404(pk)
        if not user.is_staff and instance.requester_id != user.id:
            # Hide existence from non-owners just like BBQ does.
            raise NotFoundError("No service request matches the given query.")
        return instance

    # ------------------------------------------------------------------ #
    # write                                                              #
    # ------------------------------------------------------------------ #
    def create(self, user, payload: dict):
        data = dict(payload or {})
        # Requester is always the caller — never trust the client.
        data["requester"] = user
        data["status"] = ServiceRequestModel.Status.PENDING
        # Admin-only fields never leak in via create.
        for field in ("admin_response", "responded_by", "responded_at"):
            data.pop(field, None)
        return self._repo.create(data)

    def update(self, user, pk, payload):
        if not payload:
            raise BusinessRuleError("Empty payload.")
        instance = self.get(user, pk)

        if not user.is_staff:
            if instance.status != ServiceRequestModel.Status.PENDING:
                raise BusinessRuleError(
                    "You can only edit a request while it is pending."
                )
            # Owner is not allowed to touch admin / status fields.
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
        if not user.is_staff and instance.status != ServiceRequestModel.Status.PENDING:
            raise BusinessRuleError(
                "You can only delete a request while it is pending."
            )
        self._repo.delete(instance)

    # ------------------------------------------------------------------ #
    # admin actions                                                      #
    # ------------------------------------------------------------------ #
    def respond(self, admin, pk, action, response):
        if not admin.is_staff:
            raise PermissionDeniedError(
                "Only admins can respond to a service request."
            )
        if action not in self._VALID_ACTIONS:
            raise BusinessRuleError(
                f"Invalid action. Expected one of {list(self._VALID_ACTIONS)}.",
                field="action",
            )
        message = (response or "").strip()
        if not message:
            raise BusinessRuleError(
                "A response message is required.", field="response"
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
        return self._repo.update(
            instance,
            {
                "status": new_status,
                "admin_response": message,
                "responded_by": admin,
                "responded_at": timezone.now(),
            },
        )

    def complete(self, admin, pk):
        if not admin.is_staff:
            raise PermissionDeniedError(
                "Only admins can complete a service request."
            )
        instance = self._fetch_or_404(pk)
        if instance.status != ServiceRequestModel.Status.ACCEPTED:
            raise BusinessRuleError(
                "Only accepted requests can be marked completed.",
                field="status",
            )
        return self._repo.update(
            instance, {"status": ServiceRequestModel.Status.COMPLETED}
        )

    # ------------------------------------------------------------------ #
    # internals                                                          #
    # ------------------------------------------------------------------ #
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
