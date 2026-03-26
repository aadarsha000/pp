from rest_framework import status
from rest_framework.response import Response

def custom_response(data=None, message=None, success=None, status=status.HTTP_200_OK):
    response_data = {
        "data": data,
        "message": message,
        "status": status,
        "success": success if success is not None else True if status < 400 else False,
    }
    return Response(response_data, status=status)


def success_response(data=None, message=None, status=status.HTTP_200_OK):
    if message is None:
        message = "Success"
    return custom_response(data, message, status=status)


def error_response(data=None, message=None, status=status.HTTP_400_BAD_REQUEST):
    if message is None:
        message = "Error"
    return custom_response(data, message, status=status)

