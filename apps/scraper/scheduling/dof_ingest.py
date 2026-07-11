"""DOF daily → ingestion-pipeline materialization helpers.

Extracted from ``scheduling/tasks.py`` (which is at the file-size budget) so
the daily DOF check can turn detected new-law/reform publications into
Law/LawVersion rows. Gated by ``settings.DOF_AUTO_INGEST_ENABLED`` (default
off) — DOF nota URLs are HTML detail pages that don't always resolve to a
direct PDF, so an operator validates materialization before enabling in prod.
"""

import logging

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
