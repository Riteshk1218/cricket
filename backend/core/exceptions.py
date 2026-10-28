from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ScoringConflict(Exception):
    """Raised when a scoring request is based on stale match state."""

    def __init__(self, message, current_sequence=None):
        super().__init__(message)
        self.message = message
        self.current_sequence = current_sequence


class ScoringError(Exception):
    """Raised when a scoring action breaks a cricket rule or match state."""

    def __init__(self, message, code="invalid"):
        super().__init__(message)
        self.message = message
        self.code = code


def api_exception_handler(exc, context):
    if isinstance(exc, ScoringConflict):
        return Response(
            {"detail": exc.message, "code": "stale_state", "current_sequence": exc.current_sequence},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, ScoringError):
        return Response({"detail": exc.message, "code": exc.code}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "error_dict") else {"detail": exc.messages}
        return Response(detail, status=status.HTTP_400_BAD_REQUEST)
    return exception_handler(exc, context)
