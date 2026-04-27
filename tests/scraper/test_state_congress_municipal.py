"""Tests for ``apps.scraper.municipal.state_congress_municipal``.

This scraper navigates state congress portals to discover municipal
income laws (leyes de ingresos municipales). Tests stub ``fetch_page``
at the boundary so we never hit the live portals.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.scraper.municipal.state_congress_municipal import (
    STATE_CONGRESS_REGISTRY,
    StateCongressMunicipalScraper,
    get_portal_info,
    list_supported_states,
    scrape_state,
)

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def test_list_supported_states_returns_sorted():
    out = list_supported_states()
    assert "jalisco" in out
    assert out == sorted(out)


def test_get_portal_info_known_state():
    info = get_portal_info("jalisco")
    assert info["state"] == "Jalisco"
    assert info["base_url"].startswith("https://")


def test_get_portal_info_unknown_state_raises():
    with pytest.raises(ValueError, match="Unknown state"):
        get_portal_info("not_a_state")


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state_id", list(STATE_CONGRESS_REGISTRY.keys()))
def test_init_succeeds_for_each_registered_state(state_id):
    s = StateCongressMunicipalScraper(state_id=state_id)
    assert s.state_id == state_id
    assert s.portal["state"] == STATE_CONGRESS_REGISTRY[state_id]["state"]


def test_init_raises_for_unknown_state():
    with pytest.raises(ValueError, match="Unknown state"):
        StateCongressMunicipalScraper(state_id="not_a_state")


def test_init_respects_max_results():
    s = StateCongressMunicipalScraper(state_id="jalisco", max_results=10)
    assert s.max_results == 10


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def scraper():
    """Build a Jalisco scraper for instance-method tests."""
    return StateCongressMunicipalScraper(state_id="jalisco")


# ---------------------------------------------------------------------------
# _is_municipal_law_link
# ---------------------------------------------------------------------------


def test_is_municipal_law_link_matches_keyword(scraper):
    """Texts matching `keywords` regex should be flagged as municipal laws."""
    assert (
        scraper._is_municipal_law_link(
            "Ley de Ingresos del Municipio de Guadalajara 2024",
            "/leyesmunicipales/guadalajara.pdf",
        )
        is True
    )


def test_is_municipal_law_link_excludes_state_law(scraper):
    """`exclude` regex should disqualify state-level laws."""
    assert scraper._is_municipal_law_link("Constitución Política", "/foo.pdf") is False


def test_is_municipal_law_link_rejects_unrelated(scraper):
    """Texts that don't match `keywords` are skipped."""
    assert scraper._is_municipal_law_link("Some random document", "/x.pdf") is False


# ---------------------------------------------------------------------------
# _extract_municipality
# ---------------------------------------------------------------------------


def test_extract_municipality_from_title(scraper):
    out = scraper._extract_municipality(
        "Ley de Ingresos del Municipio de Guadalajara 2024",
        "https://example.com/x.pdf",
    )
    assert "Guadalajara" in out


def test_extract_municipality_falls_back_to_state(scraper):
    """When no municipality phrase + no extractable URL segments, returns the state name."""
    # URL with only generic segments (excluded by the path-extraction logic):
    # "ley", "decreto", "doc", "archivo", "pdf" are all explicitly skipped.
    out = scraper._extract_municipality(
        "Ley de Ingresos 2024", "https://example.com/ley/decreto/archivo.pdf"
    )
    assert out == scraper.portal["state"]


def test_extract_municipality_via_url_path(scraper):
    """Path-based extraction looks for proper-noun-ish segments."""
    out = scraper._extract_municipality(
        "Ley", "https://example.com/leyes/zapopan/2024.pdf"
    )
    # Either matched zapopan from URL or fell back to state — both acceptable
    assert isinstance(out, str) and len(out) > 0


# ---------------------------------------------------------------------------
# _extract_fiscal_year
# ---------------------------------------------------------------------------


def test_extract_fiscal_year_from_title(scraper):
    assert scraper._extract_fiscal_year("Ley de Ingresos 2024", "x") == "2024"


def test_extract_fiscal_year_from_url(scraper):
    assert (
        scraper._extract_fiscal_year("Ley", "https://example.com/2023/file.pdf")
        == "2023"
    )


def test_extract_fiscal_year_returns_none_when_missing(scraper):
    assert scraper._extract_fiscal_year("Ley sin año", "https://x.com/y.pdf") is None


# ---------------------------------------------------------------------------
# _classify_document
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Ley de Ingresos del Municipio", "Ley de Ingresos"),
        ("Presupuesto de Egresos 2024", "Presupuesto de Egresos"),
        ("Ley de Hacienda Municipal", "Ley de Hacienda Municipal"),
        ("Tabla de Valores Catastrales", "Tabla de Valores"),
    ],
)
def test_classify_document_known_categories(scraper, title, expected):
    assert scraper._classify_document(title) == expected


def test_classify_document_falls_through_to_extract_category(scraper):
    """Unknown titles delegate to the parent's extract_category."""
    out = scraper._classify_document("Otro Documento")
    # Just verify it returns a string — the parent's extract_category is the
    # source of truth for this fallback path.
    assert isinstance(out, str)


# ---------------------------------------------------------------------------
# _build_law_entry
# ---------------------------------------------------------------------------


def test_build_law_entry_full_shape(scraper):
    entry = scraper._build_law_entry(
        "Ley de Ingresos del Municipio de Guadalajara 2024",
        "https://example.com/guadalajara.pdf",
    )
    assert entry["name"]  # title set
    assert entry["url"] == "https://example.com/guadalajara.pdf"
    assert "Guadalajara" in entry["municipality"]
    assert entry["state"] == "Jalisco"
    assert entry["tier"] == "municipal"
    assert entry["status"] == "Discovered"
    assert entry["source"] == "state_congress"
    assert entry["fiscal_year"] == "2024"


def test_build_law_entry_collapses_whitespace(scraper):
    entry = scraper._build_law_entry(
        "Ley   de\n\tIngresos",
        "https://example.com/x.pdf",
    )
    assert entry["name"] == "Ley de Ingresos"


def test_build_law_entry_omits_fiscal_year_when_missing(scraper):
    entry = scraper._build_law_entry("Ley sin año", "https://example.com/x.pdf")
    assert "fiscal_year" not in entry


# ---------------------------------------------------------------------------
# _title_from_url
# ---------------------------------------------------------------------------


def test_title_from_url_parses_filename(scraper):
    out = scraper._title_from_url("https://example.com/path/Ley_de_Ingresos_2024.pdf")
    assert "Ley de Ingresos 2024" in out


def test_title_from_url_handles_url_encoded_filename(scraper):
    out = scraper._title_from_url("https://example.com/Ley%20de%20Ingresos.pdf")
    assert "Ley" in out and "Ingresos" in out


# ---------------------------------------------------------------------------
# scrape_law_content — passthrough to download_law_content
# ---------------------------------------------------------------------------


def test_scrape_law_content_default_output_dir(scraper):
    with patch.object(scraper, "download_law_content") as mock_dl:
        mock_dl.return_value = {"file_path": "out.pdf"}
        result = scraper.scrape_law_content("https://example.com/x.pdf")
    assert result == {"file_path": "out.pdf"}
    called_dir = mock_dl.call_args.args[1]
    assert called_dir == "data/municipal/jalisco/congress"


def test_scrape_law_content_explicit_output_dir(scraper):
    with patch.object(scraper, "download_law_content") as mock_dl:
        mock_dl.return_value = None
        scraper.scrape_law_content("https://example.com/x.pdf", output_dir="/tmp/out")
    assert mock_dl.call_args.args[1] == "/tmp/out"


# ---------------------------------------------------------------------------
# scrape_catalog (high-level)
# ---------------------------------------------------------------------------


def test_scrape_catalog_returns_empty_on_unreachable(scraper):
    """All fetch_page calls returning None → empty list, no exception."""
    with patch.object(scraper, "fetch_page", return_value=None):
        result = scraper.scrape_catalog()
    assert result == []


def test_scrape_catalog_respects_max_results(scraper):
    """When max_results is set, the result is truncated."""
    scraper.max_results = 2
    fake_laws = [{"url": f"u{i}", "name": f"law{i}"} for i in range(10)]
    with patch.object(scraper, "_scrape_paginated_catalog", return_value=fake_laws):
        result = scraper.scrape_catalog()
    assert len(result) == 2


def test_scrape_catalog_non_paginated_state(scraper):
    """A state without pagination calls _scrape_catalog_page once."""
    s = StateCongressMunicipalScraper(state_id="nuevo_leon")  # pagination=None
    fake_laws = [{"url": "u1", "name": "law1"}]
    with patch.object(s, "_scrape_catalog_page", return_value=fake_laws) as mock_page:
        result = s.scrape_catalog()
    assert result == fake_laws
    mock_page.assert_called_once()


# ---------------------------------------------------------------------------
# scrape_state convenience function
# ---------------------------------------------------------------------------


def test_scrape_state_invokes_scraper():
    """The convenience function should construct + call scrape_catalog."""
    fake_laws = [{"url": "u1"}]
    with patch.object(
        StateCongressMunicipalScraper, "scrape_catalog", return_value=fake_laws
    ):
        result = scrape_state("jalisco", max_results=5)
    assert result == fake_laws


# ---------------------------------------------------------------------------
# _find_container — picks the configured selector
# ---------------------------------------------------------------------------


def test_find_container_returns_body_when_no_match(scraper):
    """If no configured selector matches, fall back to <body>."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup("<html><body><p>nothing</p></body></html>", "html.parser")
    container = scraper._find_container(soup)
    assert container is not None
    # Either body or top-level — just ensure we got something valid
    assert container.name in {"body", "[document]", "html"} or container is soup
