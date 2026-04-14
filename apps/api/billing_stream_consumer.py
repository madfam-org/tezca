"""
Billing event stream consumer for the MADFAM ecosystem event bus.

Polls ``madfam:billing-events`` Redis Stream via XREADGROUP and
processes billing/KYC events to keep Tezca user tiers in sync.

Runs as a periodic Celery Beat task every 30 seconds.

Consumer group: ``tezca-consumers``
Stream key:     ``madfam:billing-events``

Events handled:
    billing.subscription.created   -- Upgrade user tier
    billing.subscription.cancelled -- Downgrade user tier to free_member
    billing.payment.succeeded      -- Log payment confirmation
    billing.payment.failed         -- Log payment failure
    kyc.verified                   -- Log KYC pass
    kyc.rejected                   -- Log KYC rejection

DLQ: ``tezca:billing-dlq`` after 3 failed processing attempts.
"""

import json
import logging
import os

import redis

logger = logging.getLogger(__name__)

STREAM_KEY = os.environ.get("BILLING_STREAM_KEY", "madfam:billing-events")
DLQ_KEY = "tezca:billing-dlq"
GROUP_NAME = "tezca-consumers"
CONSUMER_NAME = f"tezca-worker-{os.getpid()}"
MAX_RETRIES = 3
BATCH_SIZE = 50

# Dhanam plan ID -> Tezca tier mapping (mirrors billing_views.py)
PLAN_TO_TIER = {
    "tezca_free_member": "free_member",
    "tezca_community": "community",
    "tezca_essentials": "essentials",
    "tezca_academic": "academic",
    "tezca_institutional": "institutional",
    "tezca_madfam": "madfam",
    "tezca_pro": "academic",
    "tezca_essentials_promo": "essentials",
    "tezca_academic_promo": "academic",
    "tezca_institutional_promo": "institutional",
}


def _get_redis_client():
    """Create a synchronous Redis client from REDIS_URL."""
    url = os.environ.get("REDIS_URL", os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    return redis.Redis.from_url(url, decode_responses=True)


def _ensure_consumer_group(client):
    """Create the consumer group if it does not exist."""
    try:
        client.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
        logger.info("Created consumer group '%s' on '%s'", GROUP_NAME, STREAM_KEY)
    except redis.exceptions.ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            pass  # Group already exists
        else:
            raise


def _process_event(event_type, data):
    """Route and handle a single billing event.

    Returns True on success, raises on failure.
    """
    handlers = {
        "billing.subscription.created": _on_subscription_created,
        "billing.subscription.cancelled": _on_subscription_cancelled,
        "billing.payment.succeeded": _on_payment_succeeded,
        "billing.payment.failed": _on_payment_failed,
        "kyc.verified": _on_kyc_verified,
        "kyc.rejected": _on_kyc_rejected,
    }

    handler = handlers.get(event_type)
    if handler:
        handler(data)
        return True

    logger.debug("Billing consumer ignoring event_type=%s", event_type)
    return True


def _on_subscription_created(data):
    """Upgrade user tier when a subscription is created."""
    from .models import APIKey

    user_id = data.get("user_id", "")
    plan = data.get("plan", "")
    new_tier = PLAN_TO_TIER.get(plan)

    if not user_id:
        logger.warning("billing.subscription.created missing user_id")
        return

    if not new_tier:
        logger.warning(
            "billing.subscription.created unknown plan=%s for user=%s",
            plan,
            user_id,
        )
        return

    updated = APIKey.objects.filter(
        janua_user_id=user_id, is_active=True
    ).update(tier=new_tier)

    logger.info(
        "Billing stream: subscription created user=%s plan=%s tier=%s keys_updated=%d",
        user_id,
        plan,
        new_tier,
        updated,
    )


def _on_subscription_cancelled(data):
    """Downgrade user tier when a subscription is cancelled."""
    from .models import APIKey

    user_id = data.get("user_id", "")
    if not user_id:
        return

    updated = APIKey.objects.filter(
        janua_user_id=user_id, is_active=True
    ).update(tier="free_member")

    logger.info(
        "Billing stream: subscription cancelled user=%s reason=%s keys_updated=%d",
        user_id,
        data.get("reason"),
        updated,
    )


def _on_payment_succeeded(data):
    logger.info(
        "Billing stream: payment succeeded user=%s amount=%s %s invoice=%s",
        data.get("user_id"),
        data.get("amount"),
        data.get("currency"),
        data.get("invoice_id"),
    )


def _on_payment_failed(data):
    logger.warning(
        "Billing stream: payment failed user=%s amount=%s %s error=%s",
        data.get("user_id"),
        data.get("amount"),
        data.get("currency"),
        data.get("error_message"),
    )


def _on_kyc_verified(data):
    logger.info(
        "Billing stream: KYC verified user=%s email=%s verification_id=%s",
        data.get("user_id"),
        data.get("email"),
        data.get("verification_id"),
    )


def _on_kyc_rejected(data):
    logger.warning(
        "Billing stream: KYC rejected user=%s verification_id=%s reason=%s",
        data.get("user_id"),
        data.get("verification_id"),
        data.get("reason"),
    )


def _move_to_dlq(client, msg_id, event_data, error):
    """Move a failed message to the dead letter queue."""
    dlq_data = json.dumps(
        {**event_data, "error": error, "original_id": msg_id},
        default=str,
    )
    client.xadd(DLQ_KEY, {"data": dlq_data})
    client.xack(STREAM_KEY, GROUP_NAME, msg_id)
    logger.warning(
        "Billing event moved to DLQ: msg_id=%s event_type=%s",
        msg_id,
        event_data.get("event_type", event_data.get("type", "?")),
    )


def poll_billing_events():
    """
    Poll the billing event stream and process pending messages.

    This is the core function called by the Celery Beat task.
    It reads up to BATCH_SIZE messages per invocation, processes each,
    and handles DLQ routing for exhausted retries.

    Returns a dict summarizing what was processed.
    """
    client = _get_redis_client()
    _ensure_consumer_group(client)

    processed = 0
    errors = 0

    try:
        results = client.xreadgroup(
            GROUP_NAME,
            CONSUMER_NAME,
            {STREAM_KEY: ">"},
            count=BATCH_SIZE,
            block=1000,  # 1 second max block (Celery task context)
        )
    except Exception as exc:
        logger.error("Billing stream XREADGROUP failed: %s", exc)
        return {"processed": 0, "errors": 1, "error": str(exc)}

    if not results:
        return {"processed": 0, "errors": 0}

    for _stream_name, messages in results:
        for msg_id, fields in messages:
            try:
                raw = fields.get("data", "")
                event_data = json.loads(raw) if raw else fields
            except (json.JSONDecodeError, TypeError) as exc:
                logger.error("Bad billing event %s: %s", msg_id, exc)
                client.xack(STREAM_KEY, GROUP_NAME, msg_id)
                errors += 1
                continue

            event_type = event_data.get(
                "event_type", event_data.get("type", "")
            )

            try:
                _process_event(event_type, event_data)
                client.xack(STREAM_KEY, GROUP_NAME, msg_id)
                processed += 1
            except Exception as exc:
                errors += 1
                # Check retry count via XPENDING
                try:
                    pending = client.xpending_range(
                        STREAM_KEY, GROUP_NAME, msg_id, msg_id, 1
                    )
                    retry_count = (
                        pending[0].get("times_delivered", 0) if pending else 0
                    )
                except Exception:
                    retry_count = MAX_RETRIES  # Assume exhausted on error

                if retry_count >= MAX_RETRIES:
                    _move_to_dlq(client, msg_id, event_data, str(exc))
                else:
                    logger.warning(
                        "Billing event %s failed (attempt %d/%d): %s",
                        msg_id,
                        retry_count + 1,
                        MAX_RETRIES,
                        exc,
                    )

    client.close()
    return {"processed": processed, "errors": errors}
