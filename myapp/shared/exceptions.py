"""Domain-level exceptions raised by services.

Services never import DRF / Django HTTP layer. They raise these and the
custom exception handler converts them to proper HTTP responses.
"""


class DomainError(Exception):
    """Base class for all service-layer errors."""


class BusinessRuleError(DomainError):
    """Business rule violation -> HTTP 400.

    `message` can be a string or a list of strings.

    If `field` is set, the response payload is ``{field: [..messages..]}``.
    Otherwise it's ``{"detail": message}``.
    """

    def __init__(self, message: str | list[str], field: str | None = None):
        super().__init__(str(message))
        self.message = message
        self.field = field


class NotFoundError(DomainError):
    """Entity not found -> HTTP 404."""

    def __init__(self, message: str = "Not found."):
        super().__init__(message)
        self.message = message


class PermissionDeniedError(DomainError):
    """Operation not permitted for current user -> HTTP 403."""

    def __init__(self, message: str = "Permission denied."):
        super().__init__(message)
        self.message = message
