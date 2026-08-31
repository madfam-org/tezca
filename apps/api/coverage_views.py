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

from .constants import KNOWN_STATES
from .models import Law

logger = logging.getLogger(__name__)

VIEW_LABELS = {
    "leyes_vigentes": {
        "es": "Leyes Legislativas Vigentes",
        "en": "Active Legislative Laws",
        "nah": "Tenahuatilli Yancuīc",
    },
    "marco_juridico_completo": {
        "es": "Marco Jurídico Completo",
        "en": "Complete Legal Framework",
        "nah": "Mochi Tenahuatiliz",
    },
    "normatividad_primaria": {
        "es": "Normatividad Primaria",
        "en": "Primary Legislation",
        "nah": "Tenahuatilli Achto",
    },
    "marco_juridico_total": {
        "es": "Marco Jurídico Total",
        "en": "Total Legal Framework",
        "nah": "Mochi Cemānāhuac Tenahuatilli",
    },
}


# Absolute path, resolved from this module rather than the process CWD:
# coverage_views.py -> api/ -> apps/ -> project root. The previous relative
# `Path("data/universe_registry.json")` only resolved when the process happened
# to be started from the repo root, so under gunicorn (WORKDIR /app) it silently
# resolved to nothing and every request fell through to the hardcoded literals
# below. Mirrors REGISTRY_PATH in law_views.py.
REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / (
    "data/universe_registry.json"
)


def _load_universe_registry():
    """Load universe_registry.json from data/ (local only, fast).

    Returns None when the registry is unavailable. Callers then fall back to
    hardcoded literals, so an absence here is not cosmetic — log it loudly
    enough to be visible at production log level.
    """
    try:
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        logger.warning(
            "universe_registry.json not found at %s — coverage will report "
            "hardcoded fallback counts instead of measured ones",
            REGISTRY_PATH,
        )
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "Failed to load universe_registry.json from %s — coverage will "
            "report hardcoded fallback counts instead of measured ones",
            REGISTRY_PATH,
            exc_info=True,
        )
    return None


def _build_tier(tier_id, name, have, universe, color, confidence=None, note=None):
    """Build a single tier dict with consistent percentage capping."""
    if universe is not None:
        pct = round(min(have / max(universe, 1) * 100, 100), 1)
    else:
        pct = None

    tier = {
        "id": tier_id,
        "name": name,
        "have": have,
        "universe": universe,
        "pct": pct,
        "color": color,
        "confidence": confidence,
    }
    if note is not None:
        tier["note"] = note
    return tier


def _build_coverage_views(registry_views, sources):
    """Build coverage perspectives from registry coverage_views section."""
    result = {}
    for view_key, view_def in registry_views.items():
        captured = 0
        for component in view_def.get("components", []):
            source_key = component["key"]
            count_field = component["count_field"]
            captured += sources.get(source_key, {}).get(count_field, 0)

        universe = view_def.get("universe")
        if universe is not None and universe > 0:
            pct = round(min(captured / universe * 100, 100), 1)
        else:
            pct = None

        result[view_key] = {
            "label": VIEW_LABELS.get(
                view_key, {"es": view_key, "en": view_key, "nah": view_key}
            ),
            "universe": universe,
            "captured": captured,
            "pct": pct,
        }
    return result


def _build_state_coverage():
    """Build per-state coverage counts from the DB."""
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
    return [
        {
            "state": KNOWN_STATES.get(row["state"], row["state"]),
            "legislative": row["legislative"],
            "non_legislative": row["non_legislative"],
            "total": row["total"],
        }
        for row in state_qs
    ]


def _get_total_articles():
    """Get total indexed article count from Elasticsearch."""
    try:
        from .config import INDEX_NAME, es_client

        return es_client.count(index=INDEX_NAME)["count"]
    except Exception:
        # WARNING, not DEBUG: this surfaces to the public /cobertura page as a
        # missing article count, so it needs an operator-visible signal.
        logger.warning("Failed to get ES article count", exc_info=True)
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

    def _src_confidence(source_key):
        return sources.get(source_key, {}).get("confidence")

    # Federal laws
    fed_known = sources.get("federal_leyes_vigentes", {}).get("known_count", 336)
    fed_count = db_by_tier.get("federal", 0)
    tiers.append(
        _build_tier(
            "federal_laws",
            {
                "es": "Leyes federales",
                "en": "Federal laws",
                "nah": "Federal tenahuatilli",
            },
            fed_count,
            fed_known,
            "green",
            confidence=_src_confidence("federal_leyes_vigentes"),
        )
    )

    # Federal reglamentos
    regs_known = sources.get("federal_reglamentos", {}).get("known_count", 150)
    regs_count = db_by_tier_type.get("federal_non_legislative", 0)
    tiers.append(
        _build_tier(
            "federal_reglamentos",
            {
                "es": "Reglamentos federales",
                "en": "Federal regulations",
                "nah": "Federal reglamentos",
            },
            regs_count,
            regs_known,
            "green",
            confidence=_src_confidence("federal_reglamentos"),
        )
    )

    # NOMs — no official census exists; known_count may be None
    nom_known = sources.get("federal_noms", {}).get("known_count")  # None if no census
    nom_count = sources.get("federal_noms", {}).get("scraped_count", 413)
    nom_note = (
        {
            "es": "No existe un censo oficial de NOMs vigentes",
            "en": "No official census of active NOMs exists",
            "nah": "Ahmo oncah NOMs tlapohualli",
        }
        if nom_known is None
        else None
    )
    tiers.append(
        _build_tier(
            "noms",
            {
                "es": "Normas Oficiales Mexicanas",
                "en": "Official Mexican Standards (NOMs)",
                "nah": "NOMs tenahuatilli",
            },
            nom_count,
            nom_known,
            (
                "red"
                if nom_known is None
                else ("red" if nom_count / max(nom_known, 1) < 0.5 else "yellow")
            ),
            confidence=_src_confidence("federal_noms"),
            note=nom_note,
        )
    )

    # State legislative
    state_leg_known = sources.get("state_legislativo", {}).get("known_count", 12120)
    state_leg_count = sources.get("state_legislativo", {}).get("scraped_count", 12468)
    tiers.append(
        _build_tier(
            "state_legislative",
            {
                "es": "Legislación estatal",
                "en": "State legislation",
                "nah": "Altepetl tenahuatilli",
            },
            state_leg_count,
            max(state_leg_known, state_leg_count),
            "green",
            confidence=_src_confidence("state_legislativo"),
        )
    )

    # State non-legislative
    state_nl_known = sources.get("state_non_legislativo", {}).get("known_count", 23660)
    state_nl_count = sources.get("state_non_legislativo", {}).get(
        "scraped_count", 18439
    )
    tiers.append(
        _build_tier(
            "state_non_legislative",
            {
                "es": "Normatividad estatal (ejecutivo/judicial)",
                "en": "State regulations (exec/judicial)",
                "nah": "Altepetl normatividad",
            },
            state_nl_count,
            state_nl_known,
            "yellow",
            confidence=_src_confidence("state_non_legislativo"),
        )
    )

    # Municipal
    muni_count = db_by_tier.get("municipal", 0)
    tiers.append(
        _build_tier(
            "municipal",
            {
                "es": "Reglamentación municipal",
                "en": "Municipal regulations",
                "nah": "Calpulli tenahuatilli",
            },
            muni_count,
            None,
            "red",
            confidence=_src_confidence("municipal"),
            note={
                "es": "6 de 2,468 municipios cubiertos",
                "en": "6 of 2,468 municipalities covered",
                "nah": "6 calpulli",
            },
        )
    )

    # Treaties
    treaty_known = sources.get("international_treaties", {}).get("known_count", 1500)
    treaty_count = sources.get("international_treaties", {}).get("scraped_count", 1170)
    tiers.append(
        _build_tier(
            "treaties",
            {
                "es": "Tratados internacionales",
                "en": "International treaties",
                "nah": "Tlanōnōtzaliztli",
            },
            treaty_count,
            treaty_known,
            "yellow",
            confidence=_src_confidence("international_treaties"),
        )
    )

    # CONAMER
    conamer_known = sources.get("conamer_cnartys", {}).get("known_count", 113373)
    conamer_count = sources.get("conamer_cnartys", {}).get("scraped_count", 0)
    tiers.append(
        _build_tier(
            "conamer",
            {
                "es": "Catálogo Nacional de Regulaciones (CONAMER)",
                "en": "National Regulation Catalog (CONAMER)",
                "nah": "CONAMER tenahuatilli",
            },
            conamer_count,
            conamer_known,
            "red",
            confidence=_src_confidence("conamer_cnartys"),
        )
    )

    # Judicial
    juris_known = sources.get("judicial_jurisprudencia", {}).get("known_count", 60000)
    tesis_known = sources.get("judicial_tesis_aisladas", {}).get("known_count", 440000)
    tiers.append(
        _build_tier(
            "judicial",
            {
                "es": "Jurisprudencia y tesis aisladas (SCJN)",
                "en": "Case law and isolated theses (SCJN)",
                "nah": "SCJN tenahuatilli",
            },
            0,
            juris_known + tesis_known,
            "red",
            confidence=_src_confidence("judicial_jurisprudencia"),
        )
    )

    # Summary stats — exclude tiers with no known universe
    total_universe = sum(t["universe"] for t in tiers if t["universe"] is not None)
    total_have = sum(t["have"] for t in tiers)

    # Coverage perspectives
    registry_views = registry.get("coverage_views", {}) if registry else {}
    coverage_views = (
        _build_coverage_views(registry_views, sources) if registry_views else {}
    )

    # State-level breakdown
    state_coverage = _build_state_coverage()

    # Total indexed articles
    total_articles = _get_total_articles()

    return Response(
        {
            "total_laws": total_db,
            "total_items": total_have,
            "total_universe": total_universe,
            "overall_pct": round(total_have / max(total_universe, 1) * 100, 1),
            "tiers": tiers,
            "total_articles": total_articles,
            "coverage_views": coverage_views,
            "state_coverage": state_coverage,
            "last_updated": registry.get("last_updated", "") if registry else "",
            "version": registry.get("version", "") if registry else "",
        }
    )
