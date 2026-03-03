"""
Webhook dispatch system.

Sends HMAC-signed payloads to subscriber URLs when events occur.
Uses Celery for async dispatch with retry logic.
"""

import logging

logger = logging.getLogger(__name__)


def dispatch_webhook_event(event: str, payload: dict):
    """
    Find matching subscriptions and dispatch webhooks via Celery.

    Called from ingestion pipeline when laws/versions are created or updated.
    """
    from .models import WebhookSubscription
    from .tasks import deliver_webhook

    # Fetch active subscriptions and filter by event in Python
    # (events__contains requires PostgreSQL; this works on all backends)
    all_subs = WebhookSubscription.objects.filter(
        is_active=True,
    ).select_related("api_key")
    subscriptions = [s for s in all_subs if event in (s.events or [])]

    for sub in subscriptions:
        # Check domain filter
        if sub.domain_filter:
            event_category = payload.get("category", "")
            if event_category and event_category not in sub.domain_filter:
                continue

        deliver_webhook.delay(sub.pk, event, payload)
