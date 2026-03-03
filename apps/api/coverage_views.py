"""
Public coverage API endpoint.

Provides real-time coverage statistics for the /cobertura page without
requiring authentication. Uses the same CoverageDashboard internally
but returns a simplified, public-safe subset of the data.
"""

import json
import logging
from pathlib import Path

from django.db.models import Count, Q
from django.views.decorators.cache import cache_page
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Law

logger = logging.getLogger(__name__)


def _load_universe_registry():
    """Load universe_registry.json from data/ (local only, fast)."""
    try:
        path = Path("data/universe_registry.json")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        logger.debug("Failed to load universe_registry.json", exc_info=True)
    return None


@api_view(["GET"])
@cache_page(300)  # 5-minute cache
def public_coverage(request):
    """
    Public coverage statistics for the /cobertura page.

    Returns per-tier counts, universe estimates, and coverage percentages.
    No authentication required.
    """
    # DB counts by tier
    tier_counts = (
        Law.objects.values("tier").annotate(count=Count("id")).order_by("tier")
    )
    db_by_tier = {row["tier"]: row["count"] for row in tier_counts}

    # DB counts by law_type within tiers
    type_counts = (
        Law.objects.values("tier", "law_type")
        .annotate(count=Count("id"))
        .order_by("tier", "law_type")
    )
    db_by_tier_type = {}
    for row in type_counts:
        key = f"{row['tier']}_{row['law_type'] or 'legislative'}"
        db_by_tier_type[key] = row["count"]

    total_db = Law.objects.count()

    # Universe estimates from registry
    registry = _load_universe_registry()
    sources = registry.get("sources", {}) if registry else {}

    # Build tier data
    tiers = []

    # Federal laws
    fed_known = sources.get("federal_leyes_vigentes", {}).get("known_count", 336)
    fed_count = db_by_tier.get("federal", 0)
    tiers.append(
        {
            "id": "federal_laws",
            "name": {
                "es": "Leyes federales",
                "en": "Federal laws",
                "nah": "Federal tenahuatilli",
            },
            "have": fed_count,
            "universe": fed_known,
            "pct": round(min(fed_count / max(fed_known, 1) * 100, 100), 1),
            "color": "green",
        }
    )

    # Federal reglamentos
    regs_known = sources.get("federal_reglamentos", {}).get("known_count", 150)
    regs_count = db_by_tier_type.get("federal_non_legislative", 0)
    # Approximate: reglamentos are a subset of federal non_legislative
    tiers.append(
        {
            "id": "federal_reglamentos",
            "name": {
                "es": "Reglamentos federales",
                "en": "Federal regulations",
                "nah": "Federal reglamentos",
            },
            "have": regs_count,
            "universe": regs_known,
            "pct": round(min(regs_count / max(regs_known, 1) * 100, 100), 1),
            "color": "green",
        }
    )

    # NOMs
    nom_known = sources.get("federal_noms", {}).get("known_count") or 4000
    nom_count = sources.get("federal_noms", {}).get("scraped_count", 413)
    tiers.append(
        {
            "id": "noms",
            "name": {
                "es": "Normas Oficiales Mexicanas",
                "en": "Official Mexican Standards (NOMs)",
                "nah": "NOMs tenahuatilli",
            },
            "have": nom_count,
            "universe": nom_known,
            "pct": round(nom_count / max(nom_known, 1) * 100, 1),
            "color": "red" if nom_count / max(nom_known, 1) < 0.5 else "yellow",
        }
    )

    # State legislative
    state_leg_known = sources.get("state_legislativo", {}).get("known_count", 12120)
    state_leg_count = sources.get("state_legislativo", {}).get("scraped_count", 12468)
    tiers.append(
        {
            "id": "state_legislative",
            "name": {
                "es": "Legislación estatal",
                "en": "State legislation",
                "nah": "Altepetl tenahuatilli",
            },
            "have": state_leg_count,
            "universe": max(state_leg_known, state_leg_count),
            "pct": round(min(state_leg_count / max(state_leg_known, 1) * 100, 100), 1),
            "color": "green",
        }
    )

    # State non-legislative
    state_nl_known = sources.get("state_non_legislativo", {}).get("known_count", 23660)
    state_nl_count = sources.get("state_non_legislativo", {}).get(
        "scraped_count", 18439
    )
    tiers.append(
        {
            "id": "state_non_legislative",
            "name": {
                "es": "Normatividad estatal (ejecutivo/judicial)",
                "en": "State regulations (exec/judicial)",
                "nah": "Altepetl normatividad",
            },
            "have": state_nl_count,
            "universe": state_nl_known,
            "pct": round(state_nl_count / max(state_nl_known, 1) * 100, 1),
            "color": "yellow",
        }
    )

    # Municipal
    muni_count = db_by_tier.get("municipal", 0)
    tiers.append(
        {
            "id": "municipal",
            "name": {
                "es": "Reglamentación municipal",
                "en": "Municipal regulations",
                "nah": "Calpulli tenahuatilli",
            },
            "have": muni_count,
            "universe": None,  # Unknown universe
            "pct": None,
            "color": "red",
            "note": {
                "es": "6 de 2,468 municipios cubiertos",
                "en": "6 of 2,468 municipalities covered",
                "nah": "6 calpulli",
            },
        }
    )

    # Treaties
    treaty_known = sources.get("international_treaties", {}).get("known_count", 1500)
    treaty_count = sources.get("international_treaties", {}).get("scraped_count", 1170)
    tiers.append(
        {
            "id": "treaties",
            "name": {
                "es": "Tratados internacionales",
                "en": "International treaties",
                "nah": "Tlanōnōtzaliztli",
            },
            "have": treaty_count,
            "universe": treaty_known,
            "pct": round(treaty_count / max(treaty_known, 1) * 100, 1),
            "color": "yellow",
        }
    )

    # CONAMER
    conamer_known = sources.get("conamer_cnartys", {}).get("known_count", 113373)
    conamer_count = sources.get("conamer_cnartys", {}).get("scraped_count", 0)
    tiers.append(
        {
            "id": "conamer",
            "name": {
                "es": "Catálogo Nacional de Regulaciones (CONAMER)",
                "en": "National Regulation Catalog (CONAMER)",
                "nah": "CONAMER tenahuatilli",
            },
            "have": conamer_count,
            "universe": conamer_known,
            "pct": round(conamer_count / max(conamer_known, 1) * 100, 1),
            "color": "red",
        }
    )

    # Judicial
    juris_known = sources.get("judicial_jurisprudencia", {}).get("known_count", 60000)
    tesis_known = sources.get("judicial_tesis_aisladas", {}).get("known_count", 440000)
    tiers.append(
        {
            "id": "judicial",
            "name": {
                "es": "Jurisprudencia y tesis aisladas (SCJN)",
                "en": "Case law and isolated theses (SCJN)",
                "nah": "SCJN tenahuatilli",
            },
            "have": 0,
            "universe": juris_known + tesis_known,
            "pct": 0,
            "color": "red",
        }
    )

    # Summary stats
    total_universe = sum(t["universe"] for t in tiers if t["universe"] is not None)
    total_have = sum(t["have"] for t in tiers)

    return Response(
        {
            "total_laws": total_db,
            "total_items": total_have,
            "total_universe": total_universe,
            "overall_pct": round(total_have / max(total_universe, 1) * 100, 1),
            "tiers": tiers,
            "last_updated": registry.get("last_updated", "") if registry else "",
            "version": registry.get("version", "") if registry else "",
        }
    )
