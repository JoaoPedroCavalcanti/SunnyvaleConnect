"""Role and employee-type helpers for business rules."""

from users.models import EmployeeType, UserRole


def get_employee_types(user) -> list[str]:
    if not user or not getattr(user, "is_authenticated", False):
        return []
    raw = getattr(user, "employee_types", None) or []
    return list(raw)


def is_admin(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "role", None) == UserRole.ADMIN:
        return True
    return getattr(user, "is_staff", False)


def is_employee(user) -> bool:
    return (
        bool(user)
        and getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) == UserRole.EMPLOYEE
    )


def has_employee_type(user, *types: str) -> bool:
    """True when user is admin or employee with at least one of ``types``."""
    if is_admin(user):
        return True
    if not is_employee(user):
        return False
    user_types = set(get_employee_types(user))
    return bool(user_types & set(types))


def can_doorman_ops(user) -> bool:
    return has_employee_type(user, EmployeeType.DOORMAN)


def can_manage_service_requests(user) -> bool:
    return has_employee_type(user, EmployeeType.CLEANING)


def can_see_all_visits(user) -> bool:
    return can_doorman_ops(user)
