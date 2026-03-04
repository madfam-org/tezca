"""
Dhanam billing webhook receiver.

POST /api/v1/billing/webhook/ — HMAC-SHA256 verified, no auth classes.
Updates API key tiers when subscriptions change via Dhanam.
"""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response

from .models import APIKey

logger = logging.getLogger(__name__)

# Map Dhanam plan IDs to Tezca tier names
PLAN_TO_TIER = {
    "tezca_community": "community",
    "tezca_pro": "pro",
    "tezca_madfam": "internal",
}

# Events that trigger an upgrade
UPGRADE_EVENTS = {"subscription.activated", "subscription.upgraded"}
# Events that trigger a downgrade
DOWNGRADE_EVENTS = {"subscription.cancelled", "subscription.downgraded"}


def _verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from Dhanam."""
    if not signature_header or not secret:
        return False
    # Expected format: "sha256=<hex digest>"
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header[7:]
    computed = hmac.new(
        secret.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, expected)


@api_view(["POST"])
@authentication_classes([])  # Server-to-server, no auth
@permission_classes([])  # No DRF permissions
def billing_webhook(request):
    """
    Receive billing events from Dhanam and update API key tiers.

    Expected payload:
        {
            "event": "subscription.activated",
            "plan": "tezca_pro",
            "user_id": "janua_user_id_here"
        }
    """
    secret = getattr(settings, "DHANAM_WEBHOOK_SECRET", "")
    if not secret:
        logger.error("DHANAM_WEBHOOK_SECRET not configured — rejecting webhook")
        return Response(
            {"error": "Webhook not configured"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Verify HMAC signature
    signature = request.META.get("HTTP_X_DHANAM_SIGNATURE", "")
    if not _verify_signature(request.body, signature, secret):
        return Response(
            {"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN
        )

    # Parse payload
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return Response(
            {"error": "Invalid JSON payload"}, status=status.HTTP_400_BAD_REQUEST
        )

    event = data.get("event", "")
    plan = data.get("plan", "")
    user_id = data.get("user_id", "")

    if not event or not user_id:
        return Response(
            {"error": "Missing required fields: event, user_id"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if event in UPGRADE_EVENTS:
        new_tier = PLAN_TO_TIER.get(plan)
        if not new_tier:
            return Response(
                {"error": f"Unknown plan: {plan}", "valid_plans": list(PLAN_TO_TIER)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = APIKey.objects.filter(janua_user_id=user_id, is_active=True).update(
            tier=new_tier
        )
        logger.info(
            "Billing upgrade: user=%s plan=%s tier=%s keys_updated=%d",
            user_id,
            plan,
            new_tier,
            updated,
        )
        return Response({"status": "ok", "tier": new_tier, "keys_updated": updated})

    elif event in DOWNGRADE_EVENTS:
        updated = APIKey.objects.filter(janua_user_id=user_id, is_active=True).update(
            tier="free"
        )
        logger.info("Billing downgrade: user=%s keys_updated=%d", user_id, updated)
        return Response({"status": "ok", "tier": "free", "keys_updated": updated})

    else:
        # Unrecognized event — acknowledge but no-op
        logger.debug("Billing webhook ignored event: %s", event)
        return Response({"status": "ignored", "event": event})
