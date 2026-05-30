"""Business rules for service requests."""

from abc import ABC, abstractmethod

from service_requests.models import ServiceRequestModel
from service_requests.repositories.service_request_repository import (
    IServiceRequestRepository,
)
from shared.exceptions import BusinessRuleError, NotFoundError


class IServiceRequestService(ABC):
    @abstractmethod
    def list_for(self, user): ...

    @abstractmethod
    def get_for(self, user, pk: int) -> ServiceRequestModel: ...

    @abstractmethod
    def create(self, payload: dict) -> ServiceRequestModel: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> ServiceRequestModel: ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...

    @abstractmethod
    def set_status(self, pk: int, accept_or_decline: str, extra: dict) -> ServiceRequestModel: ...


class ServiceRequestService(IServiceRequestService):
    def __init__(self, repository: IServiceRequestRepository):
        self._repo = repository

    def list_for(self, user):
        if user.is_staff:
            return self._repo.list_all()
        return self._repo.list_for_user(user.id)

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No Service Request matches the given query.")
        if not user.is_staff and instance.requester_user_id != user.id:
            raise NotFoundError("No Service Request matches the given query.")
        return instance

    def create(self, payload):
        return self._repo.create(payload)

    def update(self, user, pk, payload):
        if not payload:
            raise BusinessRuleError("Invalid JSON")
        instance = self.get_for(user, pk)
        return self._repo.update(instance, payload)

    def delete(self, user, pk):
        instance = self.get_for(user, pk)
        self._repo.delete(instance)

    def set_status(self, pk, accept_or_decline, extra):
        if accept_or_decline not in ("accept", "decline"):
            raise BusinessRuleError("Invalid action.", field="accept_or_decline")

        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No Service Request matches the given query.")

        new_status = "accepted" if accept_or_decline == "accept" else "declined"
        data = dict(extra or {})
        data["status"] = new_status
        return self._repo.update(instance, data)
