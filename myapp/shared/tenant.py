"""Tenant-scoping helpers used across services."""

from shared.exceptions import NotFoundError, PermissionDeniedError


def get_condominium_id(user) -> int | None:
    return getattr(user, "condominium_id", None)


def is_platform_superuser(user) -> bool:
    return bool(getattr(user, "is_superuser", False))


def require_condominium_id(user) -> int:
    condominium_id = get_condominium_id(user)
    if condominium_id is None:
        raise PermissionDeniedError("This account is not linked to a condominium.")
    return condominium_id


def assert_same_condominium(user, resource_condominium_id: int | None) -> None:
    if resource_condominium_id is None:
        raise NotFoundError("Resource not found.")
    user_condominium_id = get_condominium_id(user)
    if user_condominium_id is None:
        if is_platform_superuser(user):
            return
        raise PermissionDeniedError("This account is not linked to a condominium.")
    if user_condominium_id != resource_condominium_id:
        raise NotFoundError("Resource not found.")


def normalize_condominium_code(code: str) -> str:
    return (code or "").strip().upper()


def build_tenant_username(condominium_code: str, username: str) -> str:
    return f"{normalize_condominium_code(condominium_code)}:{username}"


def display_username(user) -> str:
    raw = getattr(user, "username", "") or ""
    condominium = getattr(user, "condominium", None)
    if condominium and condominium.code:
        prefix = f"{condominium.code.upper()}:"
        if raw.startswith(prefix):
            return raw[len(prefix) :]
    if ":" in raw:
        return raw.split(":", 1)[1]
    return raw
