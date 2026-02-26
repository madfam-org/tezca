"""
Webhook management endpoints.

Requires API key authentication.
"""

import logging
import secrets

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import APIKey, WebhookSubscription
from .webhooks import _send_webhook

logger = logging.getLogger(__name__)

VALID_EVENTS = ["law.updated", "law.created", "version.created"]


def _get_api_key(request):
    """Get the APIKey model instance for the current request."""
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None, Response(
            {"error": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    prefix = getattr(user, "api_key_prefix", "")
    if not prefix:
        return None, Response(
            {"error": "Webhooks require API key authentication (not JWT)."},
            status=status.HTTP_403_FORBIDDEN,
        )
    try:
        return APIKey.objects.get(prefix=prefix, is_active=True), None
    except APIKey.DoesNotExist:
        return None, Response(
            {"error": "API key not found."}, status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=["Bulk"],
    summary="Create webhook subscription",
    description="Subscribe to events (law.updated, law.created, version.created).",
)
@api_view(["POST"])
def create_webhook(request):
    """Create a new webhook subscription."""
    api_key, error = _get_api_key(request)
    if error:
        return error

    data = request.data
    url = data.get("url", "").strip()
    events = data.get("events", [])
    domain_filter = data.get("domain_filter", [])

    if not url:
        return Response(
            {"error": "url is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not events:
        return Response(
            {"error": "events is required (list of event types)"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    invalid_events = [e for e in events if e not in VALID_EVENTS]
    if invalid_events:
        return Response(
            {
                "error": f"Invalid events: {invalid_events}",
                "valid_events": VALID_EVENTS,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Generate signing secret
    secret = secrets.token_hex(32)

    sub = WebhookSubscription.objects.create(
        api_key=api_key,
        url=url,
        events=events,
        domain_filter=domain_filter,
        secret=secret,
    )

    logger.info("Webhook created: id=%d url=%s key=%s", sub.pk, url, api_key.prefix)

    return Response(
        {
            "id": sub.pk,
            "url": sub.url,
            "events": sub.events,
            "domain_filter": sub.domain_filter,
            "secret": secret,  # Shown once
            "is_active": sub.is_active,
            "created_at": sub.created_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=["Bulk"],
    summary="List webhook subscriptions",
    description="List all webhook subscriptions for the current API key.",
)
@api_view(["GET"])
def list_webhooks(request):
    """List webhook subscriptions for the current API key."""
    api_key, error = _get_api_key(request)
    if error:
        return error

    subs = WebhookSubscription.objects.filter(api_key=api_key).order_by("-created_at")

    data = [
        {
            "id": s.pk,
            "url": s.url,
            "events": s.events,
            "domain_filter": s.domain_filter,
            "is_active": s.is_active,
            "failure_count": s.failure_count,
            "created_at": s.created_at.isoformat(),
            "last_triggered_at": (
                s.last_triggered_at.isoformat() if s.last_triggered_at else None
            ),
        }
        for s in subs
    ]

    return Response({"count": len(data), "webhooks": data})


@extend_schema(
    tags=["Bulk"],
    summary="Delete webhook subscription",
    description="Remove a webhook subscription.",
)
@api_view(["DELETE"])
def delete_webhook(request, webhook_id):
    """Delete a webhook subscription."""
    api_key, error = _get_api_key(request)
    if error:
        return error

    try:
        sub = WebhookSubscription.objects.get(pk=webhook_id, api_key=api_key)
    except WebhookSubscription.DoesNotExist:
        return Response(
            {"error": "Webhook not found"}, status=status.HTTP_404_NOT_FOUND
        )

    sub.delete()
    logger.info("Webhook deleted: id=%d key=%s", webhook_id, api_key.prefix)
    return Response({"status": "deleted", "id": webhook_id})


@extend_schema(
    tags=["Bulk"],
    summary="Test webhook",
    description="Send a test event to a webhook subscription.",
)
@api_view(["POST"])
def test_webhook(request, webhook_id):
    """Send a test event to a webhook subscription."""
    api_key, error = _get_api_key(request)
    if error:
        return error

    try:
        sub = WebhookSubscription.objects.get(pk=webhook_id, api_key=api_key)
    except WebhookSubscription.DoesNotExist:
        return Response(
            {"error": "Webhook not found"}, status=status.HTTP_404_NOT_FOUND
        )

    test_payload = {
        "law_id": "test",
        "law_name": "Test Law (webhook ping)",
        "category": "fiscal",
        "tier": "federal",
        "test": True,
    }

    try:
        _send_webhook(sub, "test.ping", test_payload)
        return Response({"status": "sent", "id": webhook_id})
    except Exception as exc:
        return Response(
            {"status": "failed", "error": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )
