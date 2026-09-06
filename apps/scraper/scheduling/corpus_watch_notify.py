"""Corpus-watch → operator NOTIFY: the durability hook.

The corpus watch (``corpus_watch.py``) detects, once a year, that a pinned
yearly instrument (the SEP calendario escolar, the JCF ROP) has reappeared in
the DOF — the class of publication the generic change detector misses. Detection
is deliberately *never* an auto-seed: pinning a DOF codigo requires the
identity-verification a human does, and the vendored SEP-calendario snapshot is
a hand-verified artifact by design (a tezca outage must never block a kalya
seed). See ``corpus_watch.py`` and ``federal/sep_calendario_dates.py``.

What was missing was the last hop: a hit was logged (WARNING) and recorded on
the AcquisitionLog, but nothing PUSHED an operator-facing signal. This module is
that hop — it fires an operator alert (a gated, HMAC-signed webhook, no-op when
unconfigured) so the next-ciclo trigger reaches a person instead of waiting in a
log, and it fires **once per publication** (de-duplicated by URL) so a daily
scan does not re-alert while the acuerdo lingers in the edition window.

It never seeds and never mutates the corpus: the alert's whole content is "an
operator must now pin+re-vendor+re-seed", carrying the watch's own action
instruction.
"""

import logging

logger = logging.getLogger(__name__)

#: The AcquisitionLog operation under which a fired alert is recorded — also the
#: de-dup key source (a prior row with the same URL means we already alerted).
ALERT_OPERATION = "corpus_watch_alert"

#: How many recent alert rows to scan for the de-dup check. Alerts are rare (a
#: handful of yearly instruments), so a small window covers every live watch
#: without an unbounded scan.
_DEDUP_SCAN_LIMIT = 200


def _already_alerted(url: str) -> bool:
    """Whether an operator alert has already been recorded for this DOF URL.

    Backend-agnostic on purpose: it scans recent ``corpus_watch_alert``
    AcquisitionLog rows in Python rather than a JSON DB lookup, so it behaves
    identically on Postgres (prod) and SQLite (tests). A blank URL is treated as
    "not yet alerted" so a hit with a missing URL still notifies (better a
    possible duplicate than a silently dropped year-over-year trigger).
    """
    if not url:
        return False
    from apps.scraper.dataops.models import AcquisitionLog

    recent = AcquisitionLog.objects.filter(operation=ALERT_OPERATION).order_by(
        "-started_at"
    )[:_DEDUP_SCAN_LIMIT]
    for row in recent:
        params = row.parameters or {}
        if params.get("url") == url:
            return True
    return False


def _record_alert(hit_dict: dict) -> None:
    """Record that an alert fired for this hit, so it is not re-sent tomorrow."""
    from apps.scraper.dataops.models import AcquisitionLog

    log = AcquisitionLog.objects.create(
        operation=ALERT_OPERATION,
        parameters={
            "watch_key": hit_dict.get("watch_key", ""),
            "url": hit_dict.get("url", ""),
            "title": (hit_dict.get("title", "") or "")[:200],
        },
    )
    log.error_summary = (
        f"corpus-watch alert sent: {hit_dict.get('watch_key', '?')} "
        f"({hit_dict.get('url', '')})"
    )
    log.finish()


def notify_corpus_watch_hits(hits) -> int:
    """Fire an operator alert for each NEW corpus-watch hit; return how many
    were newly alerted.

    ``hits`` is the list of :class:`~apps.scraper.scheduling.corpus_watch.WatchHit`
    from ``scan_entries``. Each hit is de-duplicated by its DOF URL: a hit
    already alerted (a prior ``corpus_watch_alert`` row with the same URL) is
    skipped, so a daily scan that keeps seeing the same acuerdo alerts exactly
    once.

    Best-effort and non-fatal: any failure per hit is logged and swallowed — the
    alert is a durability nicety on top of the existing WARNING log +
    AcquisitionLog record, never a reason to fail the daily DOF check.

    The hit is RECORDED BEFORE the alert is dispatched. ``.delay()`` reaches the
    Celery broker, so a Redis outage raises there; recording afterwards meant a
    broker blip during the 7 AM beat run left no ``corpus_watch_alert`` row at
    all, and the once-a-year SEP/JCF trigger was lost with nothing to replay
    from. Recording first costs at most a duplicate alert next run (the far
    cheaper failure) and keeps the trail even when delivery is impossible.
    """
    newly = 0
    for hit in hits:
        try:
            hit_dict = hit.to_dict()
            url = hit_dict.get("url", "")
            if _already_alerted(url):
                logger.info(
                    "Corpus-watch alert already sent for %s (%s) — skipping",
                    hit_dict.get("watch_key", "?"),
                    url,
                )
                continue

            # Record first — the durable trail must not depend on the broker.
            _record_alert(hit_dict)

            # Import the delivery task lazily (Celery task in apps.api.tasks) to
            # keep this module import-light and match the scheduling package's
            # lazy-import convention.
            from apps.api.tasks import deliver_operator_alert

            try:
                deliver_operator_alert.delay("corpus_watch.hit", hit_dict)
            except Exception:
                # Delivery failed (broker down, queue refused). The hit is
                # already recorded, so the operator trail survives; log loudly
                # because nothing was pushed to a human.
                logger.exception(
                    "Corpus-watch hit %s recorded but its operator alert could "
                    "NOT be dispatched — check the Celery broker",
                    hit_dict.get("watch_key", "?"),
                )
                continue

            newly += 1
        except Exception:
            logger.exception(
                "Failed to fire corpus-watch operator alert for %s",
                getattr(hit, "watch_key", "?"),
            )
    return newly
