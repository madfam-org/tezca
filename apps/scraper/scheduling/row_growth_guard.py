"""Row-growth guard for ``check_scraper_health``.

Extracted from ``scheduling/tasks.py`` (at the file-size budget — see
``dof_ingest.py`` for the same pattern) so the recurrence guard for the
"scraper green but zero rows landed" wiring-gap class lives in its own
module.

Four wiring-gap bugs shipped in one week (CONAMER #140, judicial #141,
DOF #146, RMF/treaty #156): scrapers logged healthy ``AcquisitionLog``
rows with ``found>0`` while their output was never wired into the ingest
management command, so the corpus tables stayed at 0 rows. The staleness
and failure-count checks in ``check_scraper_health`` are structurally
blind to this failure class — the scrape itself succeeds, so nothing
looks stale or failing.

This guard closes that blind spot: it tracks each pipeline's corpus row
count across health-check runs and warns when scrapes keep succeeding
(found>0, no error) but the row count hasn't moved in
``_FLAT_RUNS_THRESHOLD`` consecutive runs.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _count_conamer_rows():
    from apps.api.models import Law

    return Law.objects.filter(official_id__startswith="conamer_").count()


def _count_judicial_rows():
    from apps.api.models import JudicialRecord

    return JudicialRecord.objects.count()


def _count_rmf_rows():
    from apps.api.models import Law

    return Law.objects.filter(category="resolución_miscelánea_fiscal").count()


def _count_treaty_rows():
    from apps.api.models import Law

    return Law.objects.filter(official_id__startswith="treaty_").count()


# Pipeline -> AcquisitionLog operation-name prefixes that count as a
# "successful scrape" signal for that pipeline, and a zero-arg callable
# that returns the current corpus row count.
#
# DOF is intentionally excluded: `dof_daily_check.found` counts DOF index
# entries scanned that day, not new laws detected, and materialization is
# gated behind `settings.DOF_AUTO_INGEST_ENABLED` (default off) — a flat
# LawVersion count with the flag off is expected behavior, not a wiring
# gap, so it would only produce noise. Re-add DOF here if/when auto-ingest
# becomes the default and a clean "materialized" signal exists.
#
# Treaties: `run_treaty_scraper` writes a "treaty_scrape" AcquisitionLog
# entry (added alongside this guard — it previously only logger.info'd,
# which left the pipeline invisible to both staleness and row-growth
# checks).
_ROW_GROWTH_PIPELINES = {
    "conamer": {
        "operation_prefixes": ("conamer_cnartys_scrape", "conamer_playwright_scrape"),
        "count_fn": _count_conamer_rows,
    },
    "judicial": {
        "operation_prefixes": ("scjn_",),
        "count_fn": _count_judicial_rows,
    },
    "rmf": {
        "operation_prefixes": ("rmf_scrape",),
        "count_fn": _count_rmf_rows,
    },
    "treaties": {
        "operation_prefixes": ("treaty_scrape",),
        "count_fn": _count_treaty_rows,
    },
}

# Consecutive flat-count health runs required before warning. Guards
# against a single noisy/slow-catch-up run producing a false positive.
_FLAT_RUNS_THRESHOLD = 3

_CORPUS_COUNTS_PATH = Path("data/health/corpus_counts.json")


def _load_corpus_counts_state():
    """Load persisted row-growth guard state.

    Mirrors the checkpoint.json pattern used by ``PlaywrightBase`` — a
    small JSON file under ``data/`` rather than a new Django model, since
    this is checkpoint-style state, not a queryable domain record, and a
    new model would need a migration.

    Returns an empty dict (fresh state) if the file doesn't exist yet or
    fails to parse.
    """
    if not _CORPUS_COUNTS_PATH.exists():
        return {}
    try:
        with open(_CORPUS_COUNTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        logger.warning(
            "Failed to read %s — starting row-growth guard state fresh",
            _CORPUS_COUNTS_PATH,
        )
        return {}


def _save_corpus_counts_state(state):
    """Persist row-growth guard state as JSON, creating data/health/ if needed."""
    _CORPUS_COUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CORPUS_COUNTS_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _pipeline_had_successful_scrape(operation_prefixes, since):
    """True if any AcquisitionLog row for this pipeline succeeded since ``since``.

    "Succeeded" = found>0 and no error_summary — the exact shape of the
    four incidents this guard targets (scraper reports it found rows, logs
    no error, but nothing reached the DB).
    """
    from django.db.models import Q

    from apps.scraper.dataops.models import AcquisitionLog

    prefix_filter = Q()
    for prefix in operation_prefixes:
        prefix_filter |= Q(operation__startswith=prefix)

    queryset = AcquisitionLog.objects.filter(prefix_filter, found__gt=0).filter(
        Q(error_summary__isnull=True) | Q(error_summary="")
    )
    if since is not None:
        queryset = queryset.filter(started_at__gte=since)
    return queryset.exists()


def check_row_growth(now):
    """Row-growth guard: detect 'scraper green but zero rows landed'.

    Fail-open by design — this is a secondary signal layered on top of the
    existing staleness/failure checks in ``check_scraper_health``. Any
    exception here (bad state file, DB error, missing model) is caught and
    logged so it can never break the primary health report.

    Returns a list of warning strings (empty when nothing to flag).
    """
    warnings = []
    try:
        from django.utils.dateparse import parse_datetime

        state = _load_corpus_counts_state()
        last_check_at_raw = state.get("_last_check_at")
        last_check_at = parse_datetime(last_check_at_raw) if last_check_at_raw else None

        new_state = {"_last_check_at": now.isoformat()}

        for pipeline, config in _ROW_GROWTH_PIPELINES.items():
            pipeline_state = state.get(pipeline, {})
            previous_count = pipeline_state.get("count")
            flat_runs = pipeline_state.get("flat_runs", 0)

            current_count = config["count_fn"]()

            had_scrape = _pipeline_had_successful_scrape(
                config["operation_prefixes"], last_check_at
            )

            if previous_count is not None and current_count == previous_count:
                if had_scrape:
                    flat_runs += 1
                # A flat count with no successful scrape since last check
                # isn't a wiring gap signal — nothing ran to produce rows.
                # Don't increment, but don't reset either: preserve the
                # streak so a later scrape resumes counting where it left
                # off instead of getting a full fresh grace window.
            else:
                flat_runs = 0

            if flat_runs >= _FLAT_RUNS_THRESHOLD:
                warning = (
                    f"pipeline {pipeline}: scrapes succeeding but corpus "
                    f"rows flat — possible wiring gap"
                )
                warnings.append(warning)
                logger.warning(
                    "Row-growth guard: %s (count=%d, flat for %d runs)",
                    warning,
                    current_count,
                    flat_runs,
                )

            new_state[pipeline] = {"count": current_count, "flat_runs": flat_runs}

        _save_corpus_counts_state(new_state)
    except Exception:
        logger.exception(
            "Row-growth guard failed — skipping without affecting health report"
        )
        return []

    return warnings
