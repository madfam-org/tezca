"""
Tests for Wave 1A state scrapers (aguascalientes, hidalgo, morelos, yucatan).

Network-free: every test patches ``fetch_page`` so we never hit the live
state portals. Verifies the four scrapers share consistent scrape +
classification behavior with the existing baja_california / michoacan
template.

Each scraper is exercised via the same parametrized suite — adding a new
state to ``WAVE1A_SCRAPERS`` automatically extends test coverage.
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.scraper.state.aguascalientes import AguascalientesScraper
from apps.scraper.state.hidalgo import HidalgoScraper
from apps.scraper.state.morelos import MorelosScraper
from apps.scraper.state.yucatan import YucatanScraper

# (scraper_class, expected_state_name) tuples. Adding a Wave 1B state to
# this list extends every test below to it.
WAVE1A_SCRAPERS = [
    (AguascalientesScraper, "Aguascalientes"),
    (HidalgoScraper, "Hidalgo"),
    (MorelosScraper, "Morelos"),
    (YucatanScraper, "Yucatán"),
]


@pytest.fixture(params=WAVE1A_SCRAPERS, ids=lambda x: x[1])
def scraper_pair(request):
    """Yields ``(scraper_instance, expected_state_name)`` for each Wave 1A state."""
    scraper_cls, state_name = request.param
    return scraper_cls(), state_name


# ── Initialization sanity ─────────────────────────────────────────────


def test_state_name_set_correctly(scraper_pair):
    scraper, state_name = scraper_pair
    assert scraper.state == state_name


def test_base_url_has_https_scheme(scraper_pair):
    scraper, _ = scraper_pair
    assert scraper.base_url.startswith("https://")


def test_session_initialized(scraper_pair):
    scraper, _ = scraper_pair
    assert scraper.session is not None


def test_rate_limit_configured(scraper_pair):
    scraper, _ = scraper_pair
    assert scraper.min_request_interval > 0


def test_alternative_paths_present(scraper_pair):
    """Every Wave 1A scraper provides fallback paths so a single broken link
    doesn't kill the catalog discovery."""
    scraper, _ = scraper_pair
    assert hasattr(scraper, "ALTERNATIVE_PATHS")
    assert len(scraper.ALTERNATIVE_PATHS) >= 1


# ── Catalog scraping (network-mocked) ─────────────────────────────────


def _sample_html(state_name: str) -> str:
    return f"""
    <html><body>
      <table>
        <tr><td><a href="/leyes/constitucion.pdf">Constitución Política del Estado de {state_name}</a></td></tr>
        <tr><td><a href="/leyes/codigo-civil.pdf">Código Civil del Estado de {state_name}</a></td></tr>
        <tr><td><a href="/leyes/ley-organica.pdf">Ley Orgánica del Poder Legislativo del Estado de {state_name}</a></td></tr>
        <tr><td><a href="/leyes/reglamento-x.pdf">Reglamento Interior del H. Congreso del Estado de {state_name}</a></td></tr>
      </table>
    </body></html>
    """


def test_scrape_catalog_extracts_known_law_types(scraper_pair):
    scraper, state_name = scraper_pair
    with patch.object(scraper, "fetch_page", return_value=_sample_html(state_name)):
        catalog = scraper.scrape_catalog()

    assert len(catalog) >= 4
    types = {law["law_type"] for law in catalog}
    assert "constitucion_estatal" in types
    assert "codigo" in types
    assert "ley_organica" in types
    assert "reglamento" in types


def test_scrape_catalog_dedups_by_url(scraper_pair):
    """If the same URL appears in multiple parser strategies, the result
    should only contain it once."""
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
    assert len({law["url"] for law in catalog}) == len(catalog)


def test_scrape_catalog_returns_empty_on_unreachable_portal(scraper_pair):
    """If both primary and alternative paths fail, return empty list — no exception."""
    scraper, _ = scraper_pair
    with patch.object(scraper, "fetch_page", return_value=None):
        catalog = scraper.scrape_catalog()
    assert catalog == []


def test_scrape_catalog_falls_back_to_alternative_paths(scraper_pair):
    """If the primary catalog path 404s, the scraper should walk
    ALTERNATIVE_PATHS until one returns HTML."""
    scraper, state_name = scraper_pair
    call_count = {"n": 0}

    def fake_fetch(url):
        call_count["n"] += 1
        # Fail the first call (primary path), succeed the second
        if call_count["n"] == 1:
            return None
        return _sample_html(state_name)

    with patch.object(scraper, "fetch_page", side_effect=fake_fetch):
        catalog = scraper.scrape_catalog()

    assert len(catalog) > 0
    # We hit at least the primary path + 1 alternative
    assert call_count["n"] >= 2


# ── Field shape ───────────────────────────────────────────────────────


def test_scraped_law_has_required_shape(scraper_pair):
    scraper, state_name = scraper_pair
    with patch.object(scraper, "fetch_page", return_value=_sample_html(state_name)):
        catalog = scraper.scrape_catalog()

    for law in catalog:
        assert set(law.keys()) >= {
            "name",
            "url",
            "state",
            "tier",
            "category",
            "law_type",
        }, law
        assert law["state"] == state_name
        assert law["tier"] == "state"
        assert law["url"].startswith("https://")


# ── Celery dispatch registration ──────────────────────────────────────


def test_all_wave1a_scrapers_registered_in_dispatch_table():
    """Every Wave 1A scraper must be addressable from the Celery task
    so operators can invoke `dataops.run_state_scraper(state_key=...)`
    via Enclii."""
    # Inspect the source rather than importing — the function-local dict
    # isn't easily reachable otherwise.
    from pathlib import Path

    tasks_src = (
        Path(__file__).resolve().parent.parent.parent
        / "apps"
        / "scraper"
        / "scheduling"
        / "tasks.py"
    ).read_text()
    for state_key, _ in [
        ("aguascalientes", None),
        ("hidalgo", None),
        ("morelos", None),
        ("yucatan", None),
    ]:
        assert (
            f'"{state_key}":' in tasks_src
        ), f"State {state_key} not registered in run_state_scraper dispatch table"


# ── Scraping content (download stub) ──────────────────────────────────


def test_scrape_law_content_passes_through_to_download(scraper_pair):
    scraper, _ = scraper_pair
    with patch.object(scraper, "download_file") as mock_dl:
        mock_dl.return_value = {"file_type": "pdf", "size_bytes": 100}
        result = scraper.scrape_law_content("https://example.com/x.pdf")
        assert result == {"file_type": "pdf", "size_bytes": 100}
        # Confirm the per-state output dir is correctly namespaced
        called_dir = mock_dl.call_args[0][1]
        assert called_dir.startswith("data/state/")
