"""
Gap Registry: Manages the lifecycle of data gaps from discovery to resolution.

Provides import methods for known gap sources (OJN gap report, probe data)
and CRUD operations for gap tracking and escalation.
"""

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from django.db.models import Count, Q
from django.utils import timezone

from .models import DataSource, GapRecord

logger = logging.getLogger(__name__)

# States with suspiciously low counts in OJN power=2.
# Investigation (2026-02-07) confirmed OJN has severely incomplete data for these
# states. State congress portals have the real catalogs:
LOW_COUNT_STATES = {
    "Durango": 1,
    "Quintana Roo": 1,
    "Baja California": 1,
    "Hidalgo": 38,
}

# State congress portal investigation results (2026-02-07).
# OJN returns near-zero for these states; the actual catalogs live on the
# state congress portals and have downloadable PDF/DOCX files.
STATE_PORTAL_INVESTIGATION = {
    "Baja California": {
        "ojn_count": 3,
        "portal_count": 340,
        "portal_url": "https://www.congresobc.gob.mx/Trabajolegislativo/Leyes",
        "formats": ["pdf", "doc"],
        "status": "scraper_needed",
        "notes": "OJN has only 3 entries (1 successful). State portal lists ~340 laws with PDF+DOC.",
    },
    "Durango": {
        "ojn_count": 1,
        "portal_count": 160,
        "portal_url": "https://congresodurango.gob.mx/trabajo-legislativo/legislacion-estatal/",
        "formats": ["pdf", "docx"],
        "status": "scraper_needed",
        "notes": "OJN has 1 entry. State portal lists ~160 laws with PDF+DOCX downloads.",
    },
    "Quintana Roo": {
        "ojn_count": 1,
        "portal_count": 356,
        "portal_url": "https://www.congresoqroo.gob.mx/leyes/",
        "formats": ["pdf", "csv", "xls"],
        "status": "scraper_needed",
        "notes": "OJN has 1 entry. State portal lists 356 laws with export APIs (csv/xls/xlsx).",
    },
    "Hidalgo": {
        "ojn_count": 38,
        "portal_count": 740,
        "portal_url": "https://www.congreso-hidalgo.gob.mx/biblioteca_legislativa/leyes.html",
        "formats": ["pdf"],
        "status": "mostly_covered",
        "notes": "OJN shows 38 but actual scraped data has 740+ docs. Non-legislative at 99.9%.",
    },
}

# Known missing source categories
MISSING_SOURCES = [
    {
        "level": "federal",
        "gap_type": "missing_source",
        "description": "Federal Reglamentos from diputados.gob.mx (separate page)",
        "priority": 2,
        "status_note": "Spider built (reglamentos_spider.py), pipeline integrated. Pending first run.",
    },
    {
        "level": "federal",
        "gap_type": "not_scraped",
        "description": "DOF daily monitoring (dof_daily.py complete, wired into Celery Beat at 7 AM)",
        "priority": 3,
        "status_note": "Implemented in apps/scraper/federal/dof_daily.py. Scheduled via dataops.check_dof_daily task.",
    },
    {
        "level": "federal",
        "gap_type": "missing_source",
        "description": "NOMs (Normas Oficiales Mexicanas) - no scraper exists",
        "priority": 3,
    },
    {
        "level": "federal",
        "gap_type": "missing_source",
        "description": "SCJN Jurisprudencia - no scraper exists",
        "priority": 4,
    },
    {
        "level": "state",
        "gap_type": "missing_source",
        "description": "State Periodicos Oficiales (individual state gazettes)",
        "priority": 4,
    },
    {
        "level": "federal",
        "gap_type": "missing_source",
        "description": "SIL legislative tracking - reform history system",
        "priority": 5,
    },
    {
        "level": "federal",
        "gap_type": "missing_source",
        "description": "International Treaties (Senado)",
        "priority": 5,
    },
]


class GapRegistry:
    """Manages data gap lifecycle: discovery, tracking, escalation, resolution."""

    def import_from_gap_report(self, path):
        """Import gaps from data/state_laws/gap_report.json (782 dead OJN links)."""
        path = Path(path)
        if not path.exists():
            logger.warning("Gap report not found: %s", path)
            return 0

        data = json.loads(path.read_text())
        created = 0

        ojn_source = DataSource.objects.filter(name__icontains="OJN").first()

        for state_entry in data.get("states", []):
            state_name = state_entry["state_name"]
            permanent = state_entry.get("permanent", 0)
            transient = state_entry.get("transient", 0)

            if permanent > 0:
                _, was_created = GapRecord.objects.get_or_create(
                    level="state",
                    state=state_name,
                    gap_type="dead_link",
                    description=f"{permanent} permanent dead links on OJN",
                    defaults={
                        "status": "permanent",
                        "current_tier": 1,
                        "priority": 2 if permanent > 100 else 3,
                        "source": ojn_source,
                        "next_action": "Search for alternative sources",
                    },
                )
                if was_created:
                    created += 1

            if transient > 0:
                _, was_created = GapRecord.objects.get_or_create(
                    level="state",
                    state=state_name,
                    gap_type="dead_link",
                    description=f"{transient} transient failures on OJN",
                    defaults={
                        "status": "open",
                        "current_tier": 0,
                        "priority": 3,
                        "source": ojn_source,
                        "next_action": "Retry download",
                        "next_action_date": date.today() + timedelta(days=7),
                    },
                )
                if was_created:
                    created += 1

        logger.info("Imported %d gap records from gap report", created)
        return created

    def import_from_ojn_probe(self, path):
        """Import gaps from data/ojn_municipal_probe.json (23,660 undiscovered laws)."""
        path = Path(path)
        if not path.exists():
            logger.warning("OJN probe not found: %s", path)
            return 0

        data = json.loads(path.read_text())
        created = 0

        ojn_source = DataSource.objects.filter(name__icontains="OJN").first()

        for state_entry in data.get("per_state", []):
            new_count = state_entry.get("new_from_other_powers", 0)
            if new_count == 0:
                continue

            state_name = state_entry["state_name"]
            _, was_created = GapRecord.objects.get_or_create(
                level="state",
                state=state_name,
                gap_type="not_scraped",
                description=(
                    f"{new_count} laws in OJN powers 1/3/4 "
                    f"(Ejecutivo/Judicial/Autónomos) not yet downloaded"
                ),
                defaults={
                    "status": "open",
                    "current_tier": 0,
                    "priority": 3,
                    "source": ojn_source,
                    "next_action": "Extend OJN scraper to cover powers 1, 3, 4",
                },
            )
            if was_created:
                created += 1

        logger.info("Imported %d gap records from OJN probe", created)
        return created

    def import_low_count_states(self):
        """Flag states with suspiciously low law counts for investigation."""
        created = 0
        ojn_source = DataSource.objects.filter(name__icontains="OJN").first()

        for state_name, count in LOW_COUNT_STATES.items():
            investigation = STATE_PORTAL_INVESTIGATION.get(state_name, {})
            portal_count = investigation.get("portal_count")
            portal_url = investigation.get("portal_url", "")

            if portal_count:
                desc = (
                    f"OJN has only {count} law(s) for power=2. "
                    f"State portal has ~{portal_count} laws."
                )
                action = f"Build scraper for {portal_url}"
            else:
                desc = (
                    f"Only {count} law(s) found on OJN power=2. "
                    f"Likely incomplete OJN data."
                )
                action = "Search state congress portal for full catalog"

            _, was_created = GapRecord.objects.get_or_create(
                level="state",
                state=state_name,
                gap_type="low_count",
                defaults={
                    "description": desc,
                    "status": "open",
                    "current_tier": 1,
                    "priority": 2,
                    "source": ojn_source,
                    "next_action": action,
                },
            )
            if was_created:
                created += 1

        logger.info("Flagged %d low-count states", created)
        return created

    def import_missing_sources(self):
        """Create GapRecords for known missing source categories."""
        created = 0

        for entry in MISSING_SOURCES:
            _, was_created = GapRecord.objects.get_or_create(
                level=entry["level"],
                gap_type=entry["gap_type"],
                description=entry["description"],
                defaults={
                    "status": "open",
                    "current_tier": 1 if entry["gap_type"] == "missing_source" else 0,
                    "priority": entry["priority"],
                    "next_action": "Identify and build scraper",
                },
            )
            if was_created:
                created += 1

        logger.info("Created %d missing-source gap records", created)
        return created

    def register_gap(self, level, gap_type, description, **kwargs):
        """Create a new gap record."""
        return GapRecord.objects.create(
            level=level,
            gap_type=gap_type,
            description=description,
            **kwargs,
        )

    def escalate(self, gap_id, action_taken, result):
        """Escalate a gap to the next tier."""
        gap = GapRecord.objects.get(id=gap_id)
        gap.escalate(action_taken, result)
        return gap

    def resolve(self, gap_id, via, url=""):
        """Resolve a gap."""
        gap = GapRecord.objects.get(id=gap_id)
        gap.resolve(via, url)
        return gap

    def get_actionable_gaps(self, level=None, max_tier=None):
        """Get gaps that can be acted on (open or in_progress)."""
        qs = GapRecord.objects.filter(status__in=["open", "in_progress"])
        if level:
            qs = qs.filter(level=level)
        if max_tier is not None:
            qs = qs.filter(current_tier__lte=max_tier)
        return qs.order_by("priority", "current_tier")

    def get_dashboard_stats(self):
        """Get summary statistics for the gap dashboard."""
        qs = GapRecord.objects.all()
        stats = {
            "total": qs.count(),
            "by_status": dict(
                qs.values_list("status")
                .annotate(c=Count("id"))
                .values_list("status", "c")
            ),
            "by_tier": dict(
                qs.values_list("current_tier")
                .annotate(c=Count("id"))
                .values_list("current_tier", "c")
            ),
            "by_level": dict(
                qs.values_list("level")
                .annotate(c=Count("id"))
                .values_list("level", "c")
            ),
            "by_type": dict(
                qs.values_list("gap_type")
                .annotate(c=Count("id"))
                .values_list("gap_type", "c")
            ),
            "actionable": qs.filter(status__in=["open", "in_progress"]).count(),
            "overdue": qs.filter(
                next_action_date__lt=date.today(),
                status__in=["open", "in_progress"],
            ).count(),
        }
        # Top 10 actionable gaps by priority
        stats["top_gaps"] = list(
            GapRecord.objects.filter(status__in=["open", "in_progress"])
            .order_by("priority", "current_tier")
            .values(
                "id",
                "level",
                "state",
                "gap_type",
                "description",
                "status",
                "priority",
                "current_tier",
            )[:10]
        )
        return stats
