from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import (
    APIException,
    ValidationError,
    NotFound,
    PermissionDenied,
    NotAuthenticated,
    Throttled,
)
from rest_framework import status as drf_status
from rest_framework.response import Response


def _normalize_details(data):
    """
    Normalize DRF error payload into:
      { field_name: [error detail, ...] }
    """
    if data is None:
        return {}

    # DRF commonly returns {"field": ["msg"]} or {"non_field_errors": ["msg"]}
    if isinstance(data, dict):
        normalized = {}
        for k, v in data.items():
            if isinstance(v, list):
                normalized[k] = [str(item) for item in v]
            else:
                normalized[k] = [str(v)]
        return normalized

    # DRF may return {"detail": "..."} for APIException
    if isinstance(data, str):
        return {"non_field_errors": [data]}

    if isinstance(data, list):
        return {"non_field_errors": [str(item) for item in data]}

    return {"non_field_errors": [str(data)]}


def _code_for_exception(exc, status_code):
    if isinstance(exc, ValidationError):
        return "VALIDATION_ERROR"
    if isinstance(exc, NotAuthenticated):
        return "NOT_AUTHENTICATED"
    if isinstance(exc, PermissionDenied):
        return "PERMISSION_DENIED"
    if isinstance(exc, NotFound):
        return "NOT_FOUND"
    if isinstance(exc, Throttled):
        return "THROTTLED"
    if isinstance(exc, APIException):
        # Includes our custom 409 conflict exception
        if status_code == 409:
            return "CONFLICT"
        return "API_ERROR"
    return "API_ERROR"


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        status_code = drf_status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response(
            {
                "message": "Internal server error",
                "status_code": status_code,
                "code": "INTERNAL_SERVER_ERROR",
                "details": {"non_field_errors": [str(exc)]},
            },
            status=status_code,
        )

    status_code = response.status_code
    code = _code_for_exception(exc, status_code)

    message = response.data.get("detail") if isinstance(response.data, dict) else None
    if not message:
        if isinstance(exc, ValidationError):
            message = "Validation failed"
        elif status_code == drf_status.HTTP_401_UNAUTHORIZED:
            message = "Authentication failed"
        elif status_code == drf_status.HTTP_403_FORBIDDEN:
            message = "Permission denied"
        elif status_code == drf_status.HTTP_404_NOT_FOUND:
            message = "Not found"
        elif status_code == drf_status.HTTP_409_CONFLICT:
            message = "Conflict"
        elif status_code == drf_status.HTTP_429_TOO_MANY_REQUESTS:
            message = "Request was throttled"
        else:
            message = "Request failed"

    # DRF already produced a good payload; we normalize it
    details_source = response.data
    # For {"detail": "..."} keep it as a non_field_errors detail.
    # If the detail itself is a dict, keep it as-is (we will normalize values).
    if isinstance(details_source, dict) and "detail" in details_source and len(details_source) == 1:
        if isinstance(details_source["detail"], dict):
            details_source = details_source["detail"]
        else:
            details_source = {"non_field_errors": [details_source["detail"]]}

    details = _normalize_details(details_source)
    return Response(
        {
            "message": message,
            "status_code": status_code,
            "code": code,
            "details": details,
        },
        status=status_code,
    )
