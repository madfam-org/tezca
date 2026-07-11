"""DOF daily → ingestion-pipeline materialization helpers.

Extracted from ``scheduling/tasks.py`` (which is at the file-size budget) so
the daily DOF check can turn detected new-law/reform publications into
Law/LawVersion rows. Gated by ``settings.DOF_AUTO_INGEST_ENABLED`` (default
off) — DOF nota URLs are HTML detail pages that don't always resolve to a
direct PDF, so an operator validates materialization before enabling in prod.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


def _dof_change_to_law_metadata(change):
    """Build an ingestion-pipeline law_metadata dict from a DOF change.

    IngestionPipeline._download_file needs at least id/name/url. The DOF
    change carries title + url (the nota detail URL).
    """
    import re
    import unicodedata

    title = (change.get("title") or "").strip()
    slug = unicodedata.normalize("NFKD", title.lower())
    slug = "".join(c for c in slug if not unicodedata.combining(c))
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug).strip("_")[:150]
    return {
        "id": slug or "dof_unknown",
        "name": title,
        "url": change.get("url", ""),
        "source": "dof_daily",
    }


def _materialize_dof_changes(changes):
    """Materialize detected new-law/reform DOF changes via the pipeline.

    Gated by DOF_AUTO_INGEST_ENABLED (default off) — see settings. Returns
    (materialized, failed). Each law is ingested independently so one bad
    parse doesn't abort the batch.
    """
    from django.conf import settings

    if not getattr(settings, "DOF_AUTO_INGEST_ENABLED", False):
        return 0, 0

    from apps.parsers.pipeline import IngestionPipeline

    pipeline = IngestionPipeline()
    materialized = 0
    failed = 0
    for change in changes:
        if change.get("change_type") not in ("new_law", "reform"):
            continue
        metadata = _dof_change_to_law_metadata(change)
        if not metadata["url"]:
            continue
        try:
            result = pipeline.ingest_law(metadata)
            if getattr(result, "success", False):
                materialized += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            logger.exception("DOF auto-ingest failed for %s", metadata.get("id"))
    return materialized, failed


@shared_task(name="dataops.check_dof_daily")
def check_dof_daily():
    """Check today's DOF edition for law changes.

    Runs daily at 7 AM via Celery Beat. Fetches the DOF index, detects
    reforms/new laws/abrogations, and — when DOF_AUTO_INGEST_ENABLED is set —
    materializes new-law/reform publications through the ingestion pipeline.
    With the flag off it detects + logs only.
    """
    import datetime

    # Pass existing law names so the scraper can match against actual DB laws
    from apps.api.models import Law
    from apps.scraper.federal.dof_daily import DofScraper

    existing_laws = list(Law.objects.values_list("name", flat=True))

    scraper = DofScraper(date=datetime.date.today())
    results = scraper.run(existing_laws=existing_laws)

    entries = results.get("entries", [])
    changes = results.get("changes", [])

    materialized, materialize_failed = _materialize_dof_changes(changes)

    # Log to AcquisitionLog
    try:
        from apps.scraper.dataops.models import AcquisitionLog

        log_entry = AcquisitionLog.objects.create(
            operation="dof_daily_check",
            parameters={
                "date": str(datetime.date.today()),
                "existing_laws_count": len(existing_laws),
                "detected": len(changes),
                "changes": [
                    {
                        "change_type": c.get("change_type"),
                        "title": c.get("title", "")[:200],
                    }
                    for c in changes[:20]
                ],
            },
            found=len(entries),
            downloaded=materialized,
            failed=materialize_failed,
            # `ingested` is now an accurate count of laws written to the DB
            # (0 when auto-ingest is off), not the prior detected-count misnomer.
            ingested=materialized,
        )
        if changes:
            log_entry.error_summary = (
                f"{len(changes)} law changes detected, "
                f"{materialized} materialized, {materialize_failed} failed"
            )
        log_entry.finish()
    except Exception:
        # Log persistence failure — don't fail the actual DOF check, but
        # surface it so AcquisitionLog gaps don't go unnoticed.
        logger.exception("Failed to persist AcquisitionLog for dof_daily_check")

    if changes:
        logger.warning(
            "DOF daily: %d entries, %d law changes detected",
            len(entries),
            len(changes),
        )
        for change in changes[:10]:
            logger.warning(
                "  [%s] %s", change.get("change_type", "?"), change.get("title", "?")
            )
    else:
        logger.info("DOF daily: %d entries, no law changes detected", len(entries))

    return {
        "date": str(datetime.date.today()),
        "total_entries": len(entries),
        "law_changes": len(changes),
        "materialized": materialized,
        "materialize_failed": materialize_failed,
        "changes": changes[:20],
    }
