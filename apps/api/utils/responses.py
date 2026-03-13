from rest_framework.response import Response


def error_response(message, status_code=400, details=None):
    """Standardized error response format for Tezca API."""
    body = {"error": message}
    if details:
        body["details"] = details
    return Response(body, status=status_code)
