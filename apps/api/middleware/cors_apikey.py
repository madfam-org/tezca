"""
CORS middleware for API-key-authenticated browser requests.

Server-to-server API key requests don't need CORS. But browser-based
API consumers (e.g., SPAs using the SDK) need permissive CORS headers
when they present a valid X-API-Key.
"""


class APIKeyCORSMiddleware:
    """
    Adds permissive CORS headers if the request includes an X-API-Key header.

    This runs after CorsMiddleware and only adds headers for API-key requests
    that wouldn't be covered by the CORS_ALLOWED_ORIGINS setting.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only apply to API requests with an API key
        if not request.path.startswith("/api/"):
            return response
        if not request.META.get("HTTP_X_API_KEY"):
            return response

        origin = request.META.get("HTTP_ORIGIN")
        if not origin:
            return response

        # If CORS headers are already set by django-cors-headers, skip
        if response.get("Access-Control-Allow-Origin"):
            return response

        # Set permissive CORS for API key requests
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "X-API-Key, Content-Type, Accept, Authorization"
        )
        response["Access-Control-Max-Age"] = "86400"
        response["Vary"] = "Origin"

        return response

    def process_view(self, request, callback, callback_args, callback_kwargs):
        """Handle preflight OPTIONS requests for API key consumers."""
        if request.method != "OPTIONS":
            return None
        if not request.path.startswith("/api/"):
            return None
        if (
            not request.META.get("HTTP_ACCESS_CONTROL_REQUEST_HEADERS", "")
            .lower()
            .count("x-api-key")
        ):
            return None

        from django.http import HttpResponse

        origin = request.META.get("HTTP_ORIGIN", "*")
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "X-API-Key, Content-Type, Accept, Authorization"
        )
        response["Access-Control-Max-Age"] = "86400"
        response.status_code = 204
        return response
