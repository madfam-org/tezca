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

# States with suspiciously low counts in OJN power=2
LOW_COUNT_STATES = {
    "Durango": 1,
    "Quintana Roo": 1,
    "Baja California": 1,
    "Hidalgo": 38,
}

# Known missing source categories
MISSING_SOURCES = [
    {
        "level": "federal",
        "gap_type": "missing_source",
        "description": "Federal Reglamentos from diputados.gob.mx (separate page)",
        "priority": 2,
    },
    {
        "level": "federal",
        "gap_type": "not_scraped",
        "description": "DOF daily monitoring (dof_daily.py is a TODO stub)",
        "priority": 3,
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
            _, was_created = GapRecord.objects.get_or_create(
                level="state",
                state=state_name,
                gap_type="low_count",
                defaults={
                    "description": (
                        f"Only {count} law(s) found on OJN power=2. "
                        f"Likely incomplete OJN data."
                    ),
                    "status": "open",
                    "current_tier": 1,
                    "priority": 2,
                    "source": ojn_source,
                    "next_action": "Search state congress portal for full catalog",
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
        return stats
