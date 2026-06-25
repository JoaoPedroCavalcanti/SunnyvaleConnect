"""Unit tests for EmployeeDashboardService."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from employee_dashboard.services.employee_dashboard_service import (
    EmployeeDashboardService,
)
from service_requests.models import ServiceRequestModel
from shared.exceptions import BusinessRuleError, PermissionDeniedError
from users.models import EmployeeType, UserRole
from visitor_access.models import VisitorAccessModel


pytestmark = pytest.mark.unit


class FakeDeliveryRepo:
    def __init__(self, count=0):
        self.count = count

    def count_created_between(self, start, end):
        return self.count


class FakeVisitorRepo:
    def __init__(self, *, today=0, scheduled=0, upcoming=None):
        self.today = today
        self.scheduled = scheduled
        self.upcoming = upcoming or []

    def count_scheduled_between(self, start, end, *, exclude_statuses=None):
        return self.today

    def count_with_scheduled_after(
        self, after, *, status_in=None, exclude_statuses=None
    ):
        return self.scheduled

    def list_upcoming(
        self, after, *, limit=10, status_in=None, exclude_statuses=None
    ):
        return self.upcoming[:limit]


class FakeRequestRepo:
    def __init__(self, pending=0):
        self.pending = pending

    def count_by_status(self, status=None):
        if status == ServiceRequestModel.Status.PENDING:
            return self.pending
        return 0


def _user(*, role=UserRole.EMPLOYEE, employee_types=None, is_staff=False):
    return SimpleNamespace(
        id=1,
        is_authenticated=True,
        is_staff=is_staff,
        role=role,
        employee_types=list(employee_types or []),
    )


@pytest.fixture
def service():
    return EmployeeDashboardService(
        delivery_repository=FakeDeliveryRepo(count=8),
        visitor_repository=FakeVisitorRepo(today=12, scheduled=3, upcoming=[1, 2]),
        service_request_repository=FakeRequestRepo(pending=5),
    )


def test_resident_forbidden(service):
    with pytest.raises(PermissionDeniedError):
        service.day_summary(_user(role=UserRole.RESIDENT))


def test_doorman_summary_only_portaria_fields(service):
    summary = service.day_summary(
        _user(employee_types=[EmployeeType.DOORMAN])
    )
    assert summary.deliveries_today == 8
    assert summary.visits_today == 12
    assert summary.scheduled_visits == 3
    assert summary.pending_service_requests is None


def test_cleaning_summary_only_requests(service):
    summary = service.day_summary(
        _user(employee_types=[EmployeeType.CLEANING])
    )
    assert summary.deliveries_today is None
    assert summary.visits_today is None
    assert summary.scheduled_visits is None
    assert summary.pending_service_requests == 5


def test_both_types_get_full_summary(service):
    summary = service.day_summary(
        _user(employee_types=[EmployeeType.DOORMAN, EmployeeType.CLEANING])
    )
    assert summary.deliveries_today == 8
    assert summary.pending_service_requests == 5


def test_admin_gets_full_summary(service):
    summary = service.day_summary(
        _user(role=UserRole.ADMIN, is_staff=True)
    )
    assert summary.deliveries_today == 8
    assert summary.pending_service_requests == 5


def test_upcoming_visits_for_doorman(service):
    visit = SimpleNamespace(
        id=1,
        visitor_name="Maria",
        scheduled_date=timezone.now() + timedelta(hours=1),
        status=VisitorAccessModel.Status.SCHEDULED,
        description="Manutenção",
        visitor_group_id=None,
        host_user=SimpleNamespace(
            id=2, full_name="Host", apartment="101", block="A"
        ),
    )
    service._visitors.upcoming = [visit]
    result = service.upcoming_visits(
        _user(employee_types=[EmployeeType.DOORMAN]), limit=5
    )
    assert len(result) == 1


def test_upcoming_visits_forbidden_for_cleaning_only(service):
    with pytest.raises(PermissionDeniedError):
        service.upcoming_visits(
            _user(employee_types=[EmployeeType.CLEANING]), limit=5
        )


def test_upcoming_visits_invalid_limit(service):
    with pytest.raises(BusinessRuleError):
        service.upcoming_visits(
            _user(employee_types=[EmployeeType.DOORMAN]), limit=0
        )
