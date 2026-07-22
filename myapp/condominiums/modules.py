"""Optional product modules that can be enabled per condominium.

These flags are metadata for the frontend (menus, feature gates).
They do not change backend authorization or endpoint availability.
"""

from __future__ import annotations

# Stable keys — keep in sync with frontend feature map.
VISITOR_ACCESS = "visitor_access"
RESERVATIONS = "reservations"
SUNNY_VALE_NEWS = "sunny_vale_news"
SERVICE_REQUESTS = "service_requests"
CONDO_PAYMENTS = "condo_payments"
DELIVERY_NOTIFICATION = "delivery_notification"

MODULE_CHOICES: tuple[tuple[str, str], ...] = (
    (VISITOR_ACCESS, "Visitantes"),
    (RESERVATIONS, "Reservas"),
    (SUNNY_VALE_NEWS, "Avisos / notícias"),
    (SERVICE_REQUESTS, "Solicitações de serviço"),
    (CONDO_PAYMENTS, "Pagamentos"),
    (DELIVERY_NOTIFICATION, "Encomendas"),
)

ALL_MODULE_KEYS: tuple[str, ...] = tuple(key for key, _ in MODULE_CHOICES)
MODULE_KEY_SET: frozenset[str] = frozenset(ALL_MODULE_KEYS)


def default_enabled_modules() -> list[str]:
    return list(ALL_MODULE_KEYS)


def normalize_enabled_modules(raw) -> list[str]:
    """Return a de-duplicated list of known module keys, preserving catalog order."""
    if raw is None:
        return default_enabled_modules()
    if not isinstance(raw, (list, tuple, set)):
        raise ValueError("enabled_modules must be a list of module keys.")
    selected = {str(item).strip() for item in raw if str(item).strip()}
    unknown = selected - MODULE_KEY_SET
    if unknown:
        raise ValueError(
            "Unknown module keys: "
            + ", ".join(sorted(unknown))
            + f". Expected one of: {', '.join(ALL_MODULE_KEYS)}."
        )
    return [key for key in ALL_MODULE_KEYS if key in selected]
