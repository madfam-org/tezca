"""
Webhook dispatch system.

Sends HMAC-signed payloads to subscriber URLs when events occur.
Uses Celery for async dispatch with retry logic.
"""

import hashlib
import hmac
import json
import logging
import time

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_FAILURES = 10
WEBHOOK_TIMEOUT = 10  # seconds
MAX_RETRIES = 3


def dispatch_webhook_event(event: str, payload: dict):
    """
    Find matching subscriptions and dispatch webhooks.

    Called from ingestion pipeline when laws/versions are created or updated.
    """
    from .models import WebhookSubscription

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

        try:
            _send_webhook(sub, event, payload)
        except Exception:
            logger.warning(
                "Webhook dispatch failed for sub=%d url=%s",
                sub.pk,
                sub.url,
                exc_info=True,
            )


def _send_webhook(subscription, event: str, payload: dict):
    """Send a single webhook with HMAC signature and retry logic."""
    body = json.dumps(
        {
            "event": event,
            "timestamp": timezone.now().isoformat(),
            "data": payload,
        },
        ensure_ascii=False,
    )

    signature = hmac.new(
        subscription.secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Tezca-Event": event,
        "X-Tezca-Signature": f"sha256={signature}",
        "User-Agent": "Tezca-Webhooks/1.0",
    }

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                subscription.url,
                data=body,
                headers=headers,
                timeout=WEBHOOK_TIMEOUT,
            )
            if resp.status_code < 400:
                # Success — reset failure count
                WebhookSubscription = type(subscription)
                WebhookSubscription.objects.filter(pk=subscription.pk).update(
                    last_triggered_at=timezone.now(),
                    failure_count=0,
                )
                return
            last_error = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)

        # Exponential backoff
        if attempt < MAX_RETRIES - 1:
            time.sleep(2**attempt)

    # All retries failed
    from .models import WebhookSubscription as WSModel

    new_count = subscription.failure_count + 1
    updates = {"failure_count": new_count}
    if new_count >= MAX_FAILURES:
        updates["is_active"] = False
        logger.warning(
            "Webhook auto-disabled after %d failures: sub=%d url=%s",
            new_count,
            subscription.pk,
            subscription.url,
        )

    WSModel.objects.filter(pk=subscription.pk).update(**updates)
    logger.warning(
        "Webhook failed (attempt %d/%d): sub=%d error=%s",
        MAX_RETRIES,
        MAX_RETRIES,
        subscription.pk,
        last_error,
    )
