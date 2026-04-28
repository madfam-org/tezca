"""Comprehensive tests for ``apps.scraper.federal.dof_daily``.

Targets pure helpers and the static `detect_law_changes` classification
pipeline without hitting the live DOF website.
"""

from __future__ import annotations

import datetime

from apps.scraper.federal.dof_daily import (
    DofScraper,
    _classify_change,
    _clean_text,
    _find_related_law,
    _is_legal_instrument,
    _normalise_section,
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_clean_text_collapses_whitespace():
    assert _clean_text("  a   b\n\tc  ") == "a b c"


def test_clean_text_handles_empty():
    assert _clean_text("") == ""


def test_normalise_section_uppercases_and_strips_accents():
    assert _normalise_section("Primera  Sección") == "PRIMERA SECCION"


def test_normalise_section_already_uppercase():
    assert _normalise_section("SEGUNDA SECCION") == "SEGUNDA SECCION"


def test_is_legal_instrument_detects_known_keywords():
    assert _is_legal_instrument("DECRETO POR EL QUE SE EXPIDE LA LEY DE FOO") is True
    assert _is_legal_instrument("LEY GENERAL DE SALUD") is True
    assert _is_legal_instrument("REGLAMENTO INTERNO") is True


def test_is_legal_instrument_rejects_non_legal():
    assert _is_legal_instrument("NOTIFICACION DE EVENTO") is False
    assert _is_legal_instrument("CONVOCATORIA A INTERESADOS") is False


# ---------------------------------------------------------------------------
# _classify_change — priority ordering
# ---------------------------------------------------------------------------


def test_classify_change_returns_abrogation_first():
    """Abrogation keywords win over reform keywords (most-specific rule)."""
    out = _classify_change("DECRETO POR EL QUE SE ABROGA LA LEY DE X")
    assert out == "abrogation"


def test_classify_change_detects_reform():
    out = _classify_change("DECRETO POR EL QUE SE REFORMAN DIVERSAS DISPOSICIONES")
    assert out == "reform"


def test_classify_change_detects_new_law():
    out = _classify_change("DECRETO POR EL QUE SE EXPIDE LA LEY DE Y")
    assert out == "new_law"


def test_classify_change_other_when_no_match():
    out = _classify_change("ALGO QUE NO COINCIDE")
    assert out == "other"


# ---------------------------------------------------------------------------
# _find_related_law — longest-match heuristic
# ---------------------------------------------------------------------------


def test_find_related_law_picks_longest():
    """When multiple laws are mentioned, the longest matched name wins."""
    existing = ["Ley General de Salud", "Ley General"]
    existing_upper = [n.upper() for n in existing]
    out = _find_related_law(
        "DECRETO QUE REFORMA LA LEY GENERAL DE SALUD", existing, existing_upper
    )
    assert out == "Ley General de Salud"


def test_find_related_law_returns_none_when_no_match():
    existing = ["Ley de Aguas"]
    existing_upper = [n.upper() for n in existing]
    out = _find_related_law("DECRETO INDEPENDIENTE", existing, existing_upper)
    assert out is None


def test_find_related_law_handles_empty_existing():
    assert _find_related_law("ANY TITLE", None, []) is None
    assert _find_related_law("ANY TITLE", [], []) is None


def test_find_related_law_returns_none_when_lists_misaligned_empty():
    """Empty list inputs short-circuit cleanly."""
    out = _find_related_law("LAW TITLE", [], [])
    assert out is None


# ---------------------------------------------------------------------------
# DofScraper.detect_law_changes
# ---------------------------------------------------------------------------


def test_detect_law_changes_filters_non_legal_entries():
    entries = [
        {"title": "Ley General de Salud — Reforma", "url": "https://x/1"},
        {"title": "Convocatoria al curso de capacitación", "url": "https://x/2"},
    ]
    out = DofScraper.detect_law_changes(entries)
    assert len(out) == 1
    assert "Salud" in out[0]["title"]


def test_detect_law_changes_classifies_each_entry():
    entries = [
        {"title": "DECRETO POR EL QUE SE EXPIDE LA LEY X", "url": "https://x/new"},
        {
            "title": "DECRETO POR EL QUE SE REFORMAN ARTICULOS DE LA LEY Y",
            "url": "https://x/ref",
        },
        {"title": "DECRETO POR EL QUE SE ABROGA LA LEY Z", "url": "https://x/abr"},
    ]
    out = DofScraper.detect_law_changes(entries)
    assert len(out) == 3
    types = {item["change_type"] for item in out}
    assert "new_law" in types
    assert "reform" in types
    assert "abrogation" in types


def test_detect_law_changes_links_to_existing_law():
    entries = [
        {
            "title": "DECRETO QUE REFORMA LA LEY GENERAL DE SALUD",
            "url": "https://x/1",
        },
    ]
    out = DofScraper.detect_law_changes(entries, existing_laws=["Ley General de Salud"])
    assert out[0]["related_law"] == "Ley General de Salud"


def test_detect_law_changes_no_existing_means_none():
    entries = [{"title": "DECRETO POR EL QUE SE EXPIDE LA LEY X", "url": "https://x/1"}]
    out = DofScraper.detect_law_changes(entries)
    assert out[0]["related_law"] is None


def test_detect_law_changes_empty_input():
    assert DofScraper.detect_law_changes([]) == []


# ---------------------------------------------------------------------------
# DofScraper.run — pipeline orchestration
# ---------------------------------------------------------------------------


def test_run_returns_iso_date_string():
    """The run() output dict includes the scraper's date in ISO form."""
    custom_date = datetime.date(2024, 3, 15)
    scraper = DofScraper(date=custom_date)
    out = scraper.run()
    assert out["date"] == "2024-03-15"
    assert "entries" in out
    assert "changes" in out


# ---------------------------------------------------------------------------
# DofScraper._resolve_url — URL resolution helper
# ---------------------------------------------------------------------------


def test_resolve_url_passes_through_absolute():
    scraper = DofScraper()
    out = scraper._resolve_url("https://example.com/x")
    assert out == "https://example.com/x"


def test_resolve_url_resolves_relative():
    scraper = DofScraper()
    out = scraper._resolve_url("/nota_detalle.php?codigo=1")
    assert out.startswith("http")
    assert "nota_detalle" in out
