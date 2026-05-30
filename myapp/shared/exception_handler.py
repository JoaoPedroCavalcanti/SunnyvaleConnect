"""Global DRF exception handler.

Maps domain exceptions raised inside services to proper DRF responses.
"""

from rest_framework import exceptions as drf_exc
from rest_framework.views import exception_handler as drf_handler

from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)


def custom_exception_handler(exc, context):
    if isinstance(exc, BusinessRuleError):
        msg = exc.message if isinstance(exc.message, list) else [exc.message]
        if exc.field:
            exc = drf_exc.ValidationError({exc.field: msg})
        else:
            exc = drf_exc.ValidationError({"detail": msg})
    elif isinstance(exc, NotFoundError):
        exc = drf_exc.NotFound(exc.message)
    elif isinstance(exc, PermissionDeniedError):
        exc = drf_exc.PermissionDenied(exc.message)

    return drf_handler(exc, context)
