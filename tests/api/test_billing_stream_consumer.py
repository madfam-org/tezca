"""Tests for ``apps.api.billing_stream_consumer``.

The handlers that update APIKey.tier need Django DB access; this file
targets the pure routing + DLQ + Redis-mocked code paths.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import redis

from apps.api import billing_stream_consumer as bsc

# ---------------------------------------------------------------------------
# Constants / mappings
# ---------------------------------------------------------------------------


def test_plan_to_tier_mapping_includes_all_tiers():
    """Every Tezca tier must be mappable from at least one Dhanam plan."""
    expected_tiers = {
        "free_member",
        "community",
        "essentials",
        "academic",
        "institutional",
        "madfam",
    }
    actual_tiers = set(bsc.PLAN_TO_TIER.values())
    assert expected_tiers.issubset(actual_tiers)


def test_legacy_plan_aliases_resolved():
    """`tezca_pro` is the legacy name for academic — must still map."""
    assert bsc.PLAN_TO_TIER["tezca_pro"] == "academic"


# ---------------------------------------------------------------------------
# _get_redis_client
# ---------------------------------------------------------------------------


def test_get_redis_client_uses_redis_url(monkeypatch):
    """REDIS_URL takes precedence over CELERY_BROKER_URL."""
    monkeypatch.setenv("REDIS_URL", "redis://from-env:6379/0")
    fake_client = MagicMock()
    with patch.object(redis.Redis, "from_url", return_value=fake_client) as m:
        result = bsc._get_redis_client()
    m.assert_called_once()
    assert "from-env" in m.call_args.args[0]
    assert result is fake_client


def test_get_redis_client_falls_back_to_celery_broker(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://celery-broker:6379/1")
    with patch.object(redis.Redis, "from_url") as m:
        bsc._get_redis_client()
    assert "celery-broker" in m.call_args.args[0]


# ---------------------------------------------------------------------------
# _ensure_consumer_group
# ---------------------------------------------------------------------------


def test_ensure_consumer_group_calls_xgroup_create():
    client = MagicMock()
    bsc._ensure_consumer_group(client)
    client.xgroup_create.assert_called_once()
    call = client.xgroup_create.call_args
    assert call.args[0] == bsc.STREAM_KEY
    assert call.args[1] == bsc.GROUP_NAME
    assert call.kwargs["mkstream"] is True


def test_ensure_consumer_group_swallows_busygroup():
    """An existing group raises BUSYGROUP; this is not an error."""
    client = MagicMock()
    err = redis.exceptions.ResponseError("BUSYGROUP Consumer Group already exists")
    client.xgroup_create.side_effect = err
    # Must not raise
    bsc._ensure_consumer_group(client)


def test_ensure_consumer_group_re_raises_other_errors():
    client = MagicMock()
    client.xgroup_create.side_effect = redis.exceptions.ResponseError("OTHER ERROR")
    with pytest.raises(redis.exceptions.ResponseError):
        bsc._ensure_consumer_group(client)


# ---------------------------------------------------------------------------
# _process_event — routing
# ---------------------------------------------------------------------------


def test_process_event_routes_to_payment_succeeded():
    with patch.object(bsc, "_on_payment_succeeded") as handler:
        ok = bsc._process_event("billing.payment.succeeded", {"user_id": "u1"})
    handler.assert_called_once_with({"user_id": "u1"})
    assert ok is True


def test_process_event_routes_to_payment_failed():
    with patch.object(bsc, "_on_payment_failed") as handler:
        bsc._process_event("billing.payment.failed", {"user_id": "u1"})
    handler.assert_called_once()


def test_process_event_routes_to_kyc_verified():
    with patch.object(bsc, "_on_kyc_verified") as handler:
        bsc._process_event("kyc.verified", {})
    handler.assert_called_once()


def test_process_event_routes_to_kyc_rejected():
    with patch.object(bsc, "_on_kyc_rejected") as handler:
        bsc._process_event("kyc.rejected", {})
    handler.assert_called_once()


def test_process_event_returns_true_for_unknown_type():
    """Unknown event types are silently ignored — returns True."""
    ok = bsc._process_event("some.unknown.type", {})
    assert ok is True


# ---------------------------------------------------------------------------
# _on_payment_* / _on_kyc_* — log-only handlers
# ---------------------------------------------------------------------------


def test_on_payment_succeeded_calls_logger():
    """Patch the logger directly to verify the handler invokes it."""
    with patch.object(bsc.logger, "info") as mock_info:
        bsc._on_payment_succeeded(
            {
                "user_id": "u1",
                "amount": "100.00",
                "currency": "MXN",
                "invoice_id": "inv-1",
            }
        )
    mock_info.assert_called_once()
    # The first positional arg is the format string
    assert "payment succeeded" in mock_info.call_args.args[0]


def test_on_payment_failed_calls_logger_warning():
    with patch.object(bsc.logger, "warning") as mock_warn:
        bsc._on_payment_failed(
            {
                "user_id": "u1",
                "amount": "100.00",
                "currency": "MXN",
                "error_message": "decline",
            }
        )
    mock_warn.assert_called_once()
    assert "payment failed" in mock_warn.call_args.args[0]


def test_on_kyc_verified_calls_logger():
    with patch.object(bsc.logger, "info") as mock_info:
        bsc._on_kyc_verified(
            {"user_id": "u1", "email": "x@y.z", "verification_id": "v1"}
        )
    mock_info.assert_called_once()
    assert "KYC verified" in mock_info.call_args.args[0]


def test_on_kyc_rejected_calls_logger_warning():
    with patch.object(bsc.logger, "warning") as mock_warn:
        bsc._on_kyc_rejected({"user_id": "u1", "verification_id": "v1", "reason": "x"})
    mock_warn.assert_called_once()
    assert "KYC rejected" in mock_warn.call_args.args[0]


# ---------------------------------------------------------------------------
# _move_to_dlq
# ---------------------------------------------------------------------------


def test_move_to_dlq_writes_and_acks():
    client = MagicMock()
    bsc._move_to_dlq(
        client,
        msg_id="msg-1",
        event_data={"event_type": "billing.payment.failed", "user_id": "u1"},
        error="boom",
    )
    client.xadd.assert_called_once()
    # xadd was called with DLQ_KEY and a {"data": "<json>"} payload
    args = client.xadd.call_args.args
    assert args[0] == bsc.DLQ_KEY
    payload = json.loads(args[1]["data"])
    assert payload["error"] == "boom"
    assert payload["original_id"] == "msg-1"
    client.xack.assert_called_once()


def test_move_to_dlq_serializes_non_string_data():
    """The default=str fallback handles non-JSON-serializable values."""
    client = MagicMock()
    import datetime

    bsc._move_to_dlq(
        client,
        msg_id="m",
        event_data={"created_at": datetime.datetime(2024, 1, 1, 12, 0, 0)},
        error="x",
    )
    # Must not raise; payload includes the stringified date
    payload = json.loads(client.xadd.call_args.args[1]["data"])
    assert "2024" in payload["created_at"]


# ---------------------------------------------------------------------------
# poll_billing_events — orchestration
# ---------------------------------------------------------------------------


def test_poll_returns_zero_when_no_results():
    client = MagicMock()
    client.xreadgroup.return_value = []
    with patch.object(bsc, "_get_redis_client", return_value=client), patch.object(
        bsc, "_ensure_consumer_group"
    ):
        out = bsc.poll_billing_events()
    assert out == {"processed": 0, "errors": 0}


def test_poll_handles_xreadgroup_exception():
    client = MagicMock()
    client.xreadgroup.side_effect = RuntimeError("redis down")
    with patch.object(bsc, "_get_redis_client", return_value=client), patch.object(
        bsc, "_ensure_consumer_group"
    ):
        out = bsc.poll_billing_events()
    assert out["errors"] == 1
    assert "redis down" in out.get("error", "")


def test_poll_processes_valid_event():
    client = MagicMock()
    client.xreadgroup.return_value = [
        (
            "stream",
            [
                (
                    "msg-1",
                    {
                        "data": json.dumps(
                            {
                                "event_type": "billing.payment.succeeded",
                                "user_id": "u1",
                                "amount": "100",
                                "currency": "MXN",
                                "invoice_id": "inv1",
                            }
                        )
                    },
                )
            ],
        )
    ]

    with patch.object(bsc, "_get_redis_client", return_value=client), patch.object(
        bsc, "_ensure_consumer_group"
    ):
        out = bsc.poll_billing_events()

    assert out["processed"] == 1
    assert out["errors"] == 0
    client.xack.assert_called()


def test_poll_acks_bad_json_and_increments_errors():
    client = MagicMock()
    client.xreadgroup.return_value = [
        ("stream", [("msg-1", {"data": "not json"})]),
    ]

    with patch.object(bsc, "_get_redis_client", return_value=client), patch.object(
        bsc, "_ensure_consumer_group"
    ):
        out = bsc.poll_billing_events()
    assert out["errors"] >= 1
    client.xack.assert_called()


def test_poll_moves_to_dlq_after_max_retries():
    client = MagicMock()
    client.xreadgroup.return_value = [
        (
            "stream",
            [
                (
                    "msg-1",
                    {
                        "data": json.dumps(
                            {
                                "event_type": "billing.subscription.created",
                                "user_id": "u1",
                                "plan": "tezca_essentials",
                            }
                        )
                    },
                )
            ],
        )
    ]
    # Force handler failure
    client.xpending_range.return_value = [{"times_delivered": bsc.MAX_RETRIES}]

    with patch.object(bsc, "_get_redis_client", return_value=client), patch.object(
        bsc, "_ensure_consumer_group"
    ), patch.object(
        bsc, "_process_event", side_effect=RuntimeError("handler failed")
    ), patch.object(
        bsc, "_move_to_dlq"
    ) as dlq_mock:
        bsc.poll_billing_events()
    dlq_mock.assert_called_once()
