from rest_framework.response import Response


def api_response(message, status_code, *, data=None, details=None, code=None):
    """
    Standard JSON envelope: message, status_code, and optional data / details / code.
    HTTP status matches status_code in the body.
    """
    payload = {"message": message, "status_code": status_code}
    if code is not None:
        payload["code"] = code
    if data is not None:
        payload["data"] = data
    if details is not None:
        payload["details"] = details
    return Response(payload, status=status_code)
