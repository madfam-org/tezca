"""Tests for state scrapers that were at 0% coverage.

Five state scrapers (cdmx, estado_de_mexico, michoacan, san_luis_potosi,
zacatecas) all extend the same StateCongressScraper base. They share the
``scrape_catalog`` / ``scrape_law_content`` interface but use slightly
different path strategies. This file uses parametrization so adding a
new state needs only one entry in ``ZERO_PCT_SCRAPERS``.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.scraper.state.cdmx import CDMXScraper
from apps.scraper.state.estado_de_mexico import EstadoDeMexicoScraper
from apps.scraper.state.michoacan import MichoacanScraper
from apps.scraper.state.san_luis_potosi import SanLuisPotosiScraper
from apps.scraper.state.zacatecas import ZacatecasScraper

ZERO_PCT_SCRAPERS = [
    (CDMXScraper, "Ciudad de Mexico"),
    (EstadoDeMexicoScraper, "Estado de Mexico"),
    (MichoacanScraper, "Michoacan"),
    (SanLuisPotosiScraper, "San Luis Potosi"),
    (ZacatecasScraper, "Zacatecas"),
]


@pytest.fixture(params=ZERO_PCT_SCRAPERS, ids=lambda x: x[1])
def scraper_pair(request):
    """Yields ``(scraper_instance, expected_state_name)`` for each scraper."""
    scraper_cls, state_name = request.param
    return scraper_cls(), state_name


# ---------------------------------------------------------------------------
# Initialization sanity
# ---------------------------------------------------------------------------


def test_state_name_set_correctly(scraper_pair):
    scraper, state_name = scraper_pair
    assert scraper.state == state_name


def test_base_url_has_https_scheme(scraper_pair):
    scraper, _ = scraper_pair
    assert scraper.base_url.startswith("https://")


def test_session_initialized(scraper_pair):
    scraper, _ = scraper_pair
    assert scraper.session is not None


# ---------------------------------------------------------------------------
# Catalog scraping (network-mocked)
# ---------------------------------------------------------------------------


def _sample_html(state_name: str) -> str:
    return f"""
    <html><body>
      <table>
        <tr><td><a href="/leyes/constitucion.pdf">Constitución Política del Estado de {state_name}</a></td></tr>
        <tr><td><a href="/leyes/codigo-civil.pdf">Código Civil del Estado de {state_name}</a></td></tr>
        <tr><td><a href="/leyes/ley-organica.pdf">Ley Orgánica del Poder Legislativo del Estado de {state_name}</a></td></tr>
        <tr><td><a href="/leyes/reglamento-interior.pdf">Reglamento Interior del Congreso del Estado de {state_name}</a></td></tr>
      </table>
    </body></html>
    """


def test_scrape_catalog_extracts_some_entries(scraper_pair):
    """A populated HTML page should yield at least one law for every scraper."""
    scraper, state_name = scraper_pair
    with patch.object(scraper, "fetch_page", return_value=_sample_html(state_name)):
        catalog = scraper.scrape_catalog()
    assert isinstance(catalog, list)
    # Each scraper should at least extract something — the exact count varies
    # because category-specific paths differ across implementations.
    assert len(catalog) >= 1


def test_scrape_catalog_returns_empty_when_unreachable(scraper_pair):
    """All paths failing → empty list, no exception."""
    scraper, _ = scraper_pair
    with patch.object(scraper, "fetch_page", return_value=None):
        catalog = scraper.scrape_catalog()
    assert catalog == []


def test_scrape_catalog_dedups_by_url(scraper_pair):
    """The same URL repeated must produce only one entry."""
    scraper, state_name = scraper_pair
    html = f"""
    <html><body>
      <table>
        <tr><td><a href="/leyes/dup.pdf">Ley Duplicada del Estado de {state_name}</a></td></tr>
      </table>
      <ul>
        <li><a href="/leyes/dup.pdf">Ley Duplicada del Estado de {state_name}</a></li>
      </ul>
    </body></html>
    """
    with patch.object(scraper, "fetch_page", return_value=html):
        catalog = scraper.scrape_catalog()

    urls = [law["url"] for law in catalog]
    assert len(urls) == len(set(urls))


# ---------------------------------------------------------------------------
# Field shape
# ---------------------------------------------------------------------------


def test_scraped_law_has_required_shape(scraper_pair):
    scraper, state_name = scraper_pair
    with patch.object(scraper, "fetch_page", return_value=_sample_html(state_name)):
        catalog = scraper.scrape_catalog()

    for law in catalog:
        # Every state scraper must produce these core fields
        assert "name" in law
        assert "url" in law
        assert "state" in law
        assert "tier" in law
        assert law["state"] == state_name
        assert law["tier"] == "state"
        assert law["url"].startswith("https://")


# ---------------------------------------------------------------------------
# scrape_law_content — passthrough to download_file
# ---------------------------------------------------------------------------


def test_scrape_law_content_routes_to_download(scraper_pair):
    scraper, _ = scraper_pair
    with patch.object(scraper, "download_file") as mock_dl:
        mock_dl.return_value = {"file_type": "pdf", "size_bytes": 100}
        result = scraper.scrape_law_content("https://example.com/x.pdf")
    assert result == {"file_type": "pdf", "size_bytes": 100}
    mock_dl.assert_called_once()
    # Confirm the per-state output dir is correctly namespaced
    called_dir = mock_dl.call_args[0][1]
    assert called_dir.startswith("data/state/")


# ---------------------------------------------------------------------------
# Class-level constants (sanity)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scraper_cls",
    [c for c, _ in ZERO_PCT_SCRAPERS],
    ids=[name for _, name in ZERO_PCT_SCRAPERS],
)
def test_alternative_paths_or_catalog_paths_present(scraper_cls):
    """Each scraper exposes either ALTERNATIVE_PATHS or CATALOG_PATHS for fallback."""
    has_alts = hasattr(scraper_cls, "ALTERNATIVE_PATHS")
    has_catalog = hasattr(scraper_cls, "CATALOG_PATHS")
    has_consejeria = hasattr(scraper_cls, "CONSEJERIA_CATALOG_PATHS")
    assert (
        has_alts or has_catalog or has_consejeria
    ), f"{scraper_cls.__name__} has no fallback path constants"
