"""Aggregator for the employee home screen."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from delivery_notification.repositories.delivery_notification_repository import (
    IDeliveryNotificationRepository,
)
from service_requests.models import ServiceRequestModel
from service_requests.repositories.service_request_repository import (
    IServiceRequestRepository,
)
from shared.exceptions import BusinessRuleError, PermissionDeniedError
from shared.roles import (
    can_doorman_ops,
    can_manage_service_requests,
    is_admin,
    is_employee,
)
from shared.tenant import require_condominium_id
from visitor_access.models import VisitorAccessModel
from visitor_access.repositories.visitor_access_repository import (
    IVisitorAccessRepository,
)


@dataclass(frozen=True)
class EmployeeDaySummary:
    deliveries_today: int | None
    visits_today: int | None
    scheduled_visits: int | None
    cleared_visits_today: int | None
    pending_service_requests: int | None


class IEmployeeDashboardService(ABC):
    @abstractmethod
    def day_summary(self, user) -> EmployeeDaySummary: ...

    @abstractmethod
    def upcoming_visits(self, user, *, limit: int = 10): ...


class EmployeeDashboardService(IEmployeeDashboardService):
    _UPCOMING_STATUSES = (
        VisitorAccessModel.Status.SCHEDULED,
        VisitorAccessModel.Status.CHECKED_IN,
    )

    def __init__(
        self,
        delivery_repository: IDeliveryNotificationRepository,
        visitor_repository: IVisitorAccessRepository,
        service_request_repository: IServiceRequestRepository,
    ):
        self._deliveries = delivery_repository
        self._visitors = visitor_repository
        self._requests = service_request_repository

    def day_summary(self, user) -> EmployeeDaySummary:
        self._require_staff_user(user)
        condominium_id = require_condominium_id(user)

        deliveries_today = None
        visits_today = None
        scheduled_visits = None
        cleared_visits_today = None
        pending_service_requests = None

        if can_doorman_ops(user):
            day_start, day_end = self._local_day_bounds()
            now = timezone.now()
            deliveries_today = self._deliveries.count_created_between(
                day_start, day_end, condominium_id=condominium_id
            )
            visits_today = self._visitors.count_scheduled_between(
                day_start,
                day_end,
                condominium_id=condominium_id,
                exclude_statuses=[VisitorAccessModel.Status.CANCELLED],
            )
            scheduled_visits = self._visitors.count_with_scheduled_after(
                now,
                condominium_id=condominium_id,
                status_in=[VisitorAccessModel.Status.SCHEDULED],
            )
            cleared_visits_today = self._visitors.count_checked_in_between(
                day_start, day_end, condominium_id=condominium_id
            )

        if can_manage_service_requests(user):
            pending_service_requests = self._requests.count_by_status(
                ServiceRequestModel.Status.PENDING,
                condominium_id=condominium_id,
            )

        return EmployeeDaySummary(
            deliveries_today=deliveries_today,
            visits_today=visits_today,
            scheduled_visits=scheduled_visits,
            cleared_visits_today=cleared_visits_today,
            pending_service_requests=pending_service_requests,
        )

    def upcoming_visits(self, user, *, limit: int = 10):
        self._require_staff_user(user)
        if not can_doorman_ops(user):
            raise PermissionDeniedError(
                "Only doorman staff can list upcoming visits."
            )
        if limit < 1 or limit > 50:
            raise BusinessRuleError(
                "Limit must be between 1 and 50.", field="limit"
            )

        return self._visitors.list_upcoming(
            timezone.now(),
            condominium_id=require_condominium_id(user),
            limit=limit,
            status_in=self._UPCOMING_STATUSES,
            exclude_statuses=[VisitorAccessModel.Status.CANCELLED],
        )

    @staticmethod
    def _require_staff_user(user) -> None:
        if not is_admin(user) and not is_employee(user):
            raise PermissionDeniedError(
                "Only condo staff can access the employee dashboard."
            )

    @staticmethod
    def _local_day_bounds() -> tuple[datetime, datetime]:
        now = timezone.localtime(timezone.now())
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start, day_start + timedelta(days=1)
