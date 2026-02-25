"""
Coverage Dashboard: Calculates coverage metrics across all data sources.

Combines live DB counts with metadata from JSON files to provide
a comprehensive picture of acquisition status.
"""

import json
import logging
from pathlib import Path

from django.conf import settings
from django.db.models import Count, Q

logger = logging.getLogger(__name__)

DATA_DIR = Path(settings.BASE_DIR) / "data"


def _load_json(path):
    """Load a JSON file, returning empty dict on failure."""
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning("Could not load %s: %s", path, e)
        return {}


class CoverageDashboard:
    """Calculates coverage metrics from DB and metadata files."""

    def federal_coverage(self):
        """Federal-level coverage stats."""
        from apps.api.models import Law

        federal_in_db = Law.objects.filter(tier="federal").count()

        # Check scraped metadata
        metadata = _load_json(DATA_DIR / "law_registry.json")
        scraped_federal = 0
        if isinstance(metadata, dict):
            scraped_federal = len(
                [
                    v
                    for v in metadata.values()
                    if isinstance(v, dict) and v.get("tier") == "federal"
                ]
            )
        if scraped_federal == 0:
            # Fallback: count XML files in federal data dir
            federal_dir = DATA_DIR / "federal"
            if federal_dir.exists():
                scraped_federal = len(list(federal_dir.glob("**/*.xml")))

        # Live reglamentos count from DB
        from apps.api.models import Law

        reglamentos_in_db = Law.objects.filter(
            tier="federal", law_type="reglamento"
        ).count()
        if reglamentos_in_db == 0:
            # Fallback: check discovered_reglamentos.json
            reg_meta = _load_json(DATA_DIR / "discovered_reglamentos.json")
            reglamentos_in_db = len(reg_meta) if isinstance(reg_meta, list) else 0

        return {
            "laws_in_db": federal_in_db,
            "laws_scraped": scraped_federal,
            "reglamentos": reglamentos_in_db,
            "noms": 0,  # Scraper in progress
            "treaties": 0,  # Scraper in progress
            "gaps": {
                "noms": "~4,000 estimated, scraper in progress",
                "scjn": "~500,000 judicial instruments, partnership outreach started",
                "conamer": "113,373 listed on CNARTyS, scraper in progress",
                "treaties": "~1,500 on SRE portal, scraper in progress",
            },
        }

    def state_coverage(self):
        """Per-state coverage stats with anomaly flags."""
        from apps.api.models import Law

        # DB counts per state
        db_counts = dict(
            Law.objects.filter(tier="state")
            .exclude(state__isnull=True)
            .exclude(state="")
            .values_list("state")
            .annotate(c=Count("id"))
            .values_list("state", "c")
        )

        # Scraped metadata
        state_metadata = _load_json(DATA_DIR / "state_laws_metadata.json")
        gap_report = _load_json(DATA_DIR / "state_laws" / "gap_report.json")
        ojn_probe = _load_json(DATA_DIR / "ojn_municipal_probe.json")

        # Build per-state scraped counts from directory
        states_dir = DATA_DIR / "state_laws"
        scraped_per_state = {}
        if states_dir.exists():
            for state_dir in states_dir.iterdir():
                if state_dir.is_dir():
                    pdf_count = len(list(state_dir.glob("*.pdf")))
                    html_count = len(list(state_dir.glob("*.html")))
                    total = pdf_count + html_count
                    if total > 0:
                        scraped_per_state[state_dir.name] = total

        # Build gap info per state
        gap_per_state = {}
        for entry in gap_report.get("states", []):
            gap_per_state[entry["state_name"]] = {
                "permanent": entry.get("permanent", 0),
                "transient": entry.get("transient", 0),
            }

        # OJN probe data per state
        probe_per_state = {}
        for entry in ojn_probe.get("per_state", []):
            probe_per_state[entry["state_name"]] = {
                "existing_estatal": entry.get("existing_estatal", 0),
                "new_from_other_powers": entry.get("new_from_other_powers", 0),
            }

        # Combine all data
        all_states = sorted(
            set(
                list(db_counts.keys())
                + list(scraped_per_state.keys())
                + list(probe_per_state.keys())
            )
        )

        per_state = []
        total_in_db = 0
        total_scraped = 0
        total_gaps = 0

        low_count_threshold = 10
        for state in all_states:
            in_db = db_counts.get(state, 0)
            scraped = scraped_per_state.get(state, 0)
            probe = probe_per_state.get(state, {})
            gaps = gap_per_state.get(state, {})
            permanent_gaps = gaps.get("permanent", 0)

            anomaly = None
            ojn_count = probe.get("existing_estatal", 0)
            if ojn_count > 0 and ojn_count < low_count_threshold:
                anomaly = f"Suspiciously low: only {ojn_count} on OJN"

            per_state.append(
                {
                    "state": state,
                    "in_db": in_db,
                    "scraped": scraped,
                    "ojn_estatal": ojn_count,
                    "undiscovered": probe.get("new_from_other_powers", 0),
                    "permanent_gaps": permanent_gaps,
                    "anomaly": anomaly,
                }
            )

            total_in_db += in_db
            total_scraped += scraped
            total_gaps += permanent_gaps

        return {
            "per_state": per_state,
            "total_in_db": total_in_db,
            "total_scraped": total_scraped,
            "total_permanent_gaps": total_gaps,
            "states_with_anomalies": [s["state"] for s in per_state if s["anomaly"]],
        }

    def municipal_coverage(self):
        """Municipal-level coverage stats."""
        from apps.api.models import Law

        # DB counts
        municipal_db = (
            Law.objects.filter(tier="municipal")
            .values("municipality")
            .annotate(c=Count("id"))
            .order_by("-c")
        )

        db_counts = {m["municipality"]: m["c"] for m in municipal_db}
        total_in_db = sum(db_counts.values())

        # Scraped metadata
        municipal_metadata = _load_json(DATA_DIR / "municipal_laws_metadata.json")
        scraped_total = 0
        per_city = []

        if isinstance(municipal_metadata, dict):
            for city, info in municipal_metadata.items():
                count = info.get("count", 0) if isinstance(info, dict) else 0
                scraped_total += count
                per_city.append(
                    {
                        "city": city,
                        "scraped": count,
                        "in_db": db_counts.get(city, 0),
                    }
                )

        # Fallback: check municipal_laws directory
        if scraped_total == 0:
            muni_dir = DATA_DIR / "municipal_laws"
            if muni_dir.exists():
                for city_dir in muni_dir.iterdir():
                    if city_dir.is_dir():
                        count = len(list(city_dir.glob("*")))
                        if count > 0:
                            per_city.append(
                                {
                                    "city": city_dir.name,
                                    "scraped": count,
                                    "in_db": db_counts.get(city_dir.name, 0),
                                }
                            )
                            scraped_total += count

        per_city.sort(key=lambda x: x["scraped"], reverse=True)

        return {
            "per_city": per_city,
            "total_in_db": total_in_db,
            "total_scraped": scraped_total,
            "cities_covered": len(per_city),
            "estimated_total_municipalities": 2468,  # INEGI official count
        }

    def full_report(self):
        """Combined coverage report across all levels."""
        from apps.api.models import Law

        from .models import GapRecord

        federal = self.federal_coverage()
        state = self.state_coverage()
        municipal = self.municipal_coverage()

        gap_stats = {
            "total": GapRecord.objects.count(),
            "open": GapRecord.objects.filter(status="open").count(),
            "in_progress": GapRecord.objects.filter(status="in_progress").count(),
            "resolved": GapRecord.objects.filter(status="resolved").count(),
            "permanent": GapRecord.objects.filter(status="permanent").count(),
        }

        total_in_db = Law.objects.count()
        total_scraped = (
            federal["laws_scraped"]
            + state["total_scraped"]
            + municipal["total_scraped"]
        )

        return {
            "summary": {
                "total_in_db": total_in_db,
                "total_scraped": total_scraped,
                "total_gaps": gap_stats["total"],
                "actionable_gaps": gap_stats["open"] + gap_stats["in_progress"],
            },
            "federal": federal,
            "state": state,
            "municipal": municipal,
            "gaps": gap_stats,
        }

    def dashboard_report(self):
        """Consolidated dashboard report combining universe registry, DB counts, gaps, and health."""
        from apps.api.models import Law

        from .gap_registry import GapRegistry
        from .health_monitor import HealthMonitor
        from .models import DataSource, GapRecord

        # Load universe registry
        registry_path = DATA_DIR / "universe_registry.json"
        registry = _load_json(registry_path)
        sources = registry.get("sources", {})
        views_def = registry.get("coverage_views", {})

        # ── Tier Progress ──────────────────────────────────────────
        tier_db_queries = {
            "federal_leyes_vigentes": Law.objects.filter(tier="federal").count(),
            "state_legislativo": Law.objects.filter(tier="state")
            .exclude(official_id__contains="_nl_")
            .count(),
            "state_non_legislativo": Law.objects.filter(
                tier="state", official_id__contains="_nl_"
            ).count(),
            "municipal": Law.objects.filter(tier="municipal").count(),
        }

        tier_progress = []
        for key, src in sources.items():
            known = src.get("known_count")
            scraped = src.get("scraped_count", 0)
            in_db = tier_db_queries.get(key, 0)
            perm_gaps = src.get("permanent_gaps", 0)
            pct = round(scraped / known * 100, 1) if known and known > 0 else 0
            tier_progress.append(
                {
                    "key": key,
                    "label": src.get("source_name", key),
                    "known_universe": known,
                    "scraped": scraped,
                    "in_db": in_db,
                    "permanent_gaps": perm_gaps,
                    "coverage_pct": pct,
                    "confidence": src.get("confidence", "unknown"),
                    "source_name": src.get("source_name", ""),
                    "source_url": src.get("source_url", ""),
                }
            )

        # ── Coverage Views ─────────────────────────────────────────
        coverage_views = {}
        for view_key, view_def in views_def.items():
            captured = 0
            for comp in view_def.get("components", []):
                src_key = comp["key"]
                field = comp.get("count_field", "scraped_count")
                captured += sources.get(src_key, {}).get(field, 0)
            universe = view_def.get("universe", 0)
            pct = round(captured / universe * 100, 1) if universe > 0 else 0
            coverage_views[view_key] = {
                "label": view_def.get("label", view_key),
                "universe": universe,
                "captured": captured,
                "pct": pct,
            }

        # ── State Coverage ─────────────────────────────────────────
        LOW_COUNT_STATES = {
            "Durango": 1,
            "Quintana Roo": 1,
            "Baja California": 1,
            "Hidalgo": 38,
        }

        state_qs = (
            Law.objects.filter(tier="state")
            .exclude(state__isnull=True)
            .exclude(state="")
            .values("state")
            .annotate(
                legislative=Count("id", filter=~Q(official_id__contains="_nl_")),
                non_legislative=Count("id", filter=Q(official_id__contains="_nl_")),
                total=Count("id"),
            )
            .order_by("state")
        )

        state_coverage = []
        for row in state_qs:
            st = row["state"]
            anomaly = None
            if st in LOW_COUNT_STATES:
                anomaly = (
                    f"Suspiciously low: only {LOW_COUNT_STATES[st]} on OJN power=2"
                )
            state_coverage.append(
                {
                    "state": st,
                    "legislative_in_db": row["legislative"],
                    "non_legislative_in_db": row["non_legislative"],
                    "total_in_db": row["total"],
                    "anomaly": anomaly,
                }
            )

        # ── Gap Summary ────────────────────────────────────────────
        gap_registry = GapRegistry()
        gap_stats = gap_registry.get_dashboard_stats()
        top_gaps = list(
            GapRecord.objects.filter(status__in=["open", "in_progress"])
            .order_by("priority", "current_tier")
            .values(
                "id", "level", "state", "gap_type", "description", "status", "priority"
            )[:10]
        )
        gap_stats["top_gaps"] = top_gaps

        # ── Expansion Priorities ───────────────────────────────────
        expansion_priorities = [
            {
                "rank": 1,
                "action": "OCR pipeline for 4,438 non-legislative parse failures",
                "estimated_gain": 3500,
                "effort": "medium",
                "roi_score": 9.5,
                "status": "in_progress",
            },
            {
                "rank": 2,
                "action": "State congress scrapers: BC (~340), Durango (~160), QR (~356)",
                "estimated_gain": 856,
                "effort": "medium",
                "roi_score": 8.5,
                "status": "in_progress",
            },
            {
                "rank": 3,
                "action": "CONAMER CNARTyS scraper (113K+ regulations, ~50-80K unique after dedup)",
                "estimated_gain": 65000,
                "effort": "high",
                "roi_score": 8.0,
                "status": "in_progress",
            },
            {
                "rank": 4,
                "action": "Federal NOMs scraper (~4,000 instruments)",
                "estimated_gain": 4000,
                "effort": "medium",
                "roi_score": 7.0,
                "status": "planned",
            },
            {
                "rank": 5,
                "action": "SRE International Treaties scraper (~1,500)",
                "estimated_gain": 1500,
                "effort": "low",
                "roi_score": 6.5,
                "status": "planned",
            },
            {
                "rank": 6,
                "action": "SCJN judicial corpus (500K+ via partnership)",
                "estimated_gain": 500000,
                "effort": "high",
                "roi_score": 6.0,
                "status": "outreach_started",
            },
            {
                "rank": 7,
                "action": "Municipal tier-2 expansion (15 more cities)",
                "estimated_gain": 1500,
                "effort": "high",
                "roi_score": 5.0,
                "status": "planned",
            },
        ]

        # ── Health Status ──────────────────────────────────────────
        monitor = HealthMonitor()
        health_summary = monitor.get_summary()
        health_sources = list(
            DataSource.objects.all().values(
                "id",
                "name",
                "source_type",
                "level",
                "status",
                "last_check",
                "last_success",
                "response_time_ms",
            )
        )

        from django.utils import timezone as tz

        return {
            "generated_at": tz.now().isoformat(),
            "tier_progress": tier_progress,
            "coverage_views": coverage_views,
            "state_coverage": state_coverage,
            "gap_summary": gap_stats,
            "expansion_priorities": expansion_priorities,
            "health_status": {
                "summary": health_summary,
                "sources": health_sources,
            },
        }
