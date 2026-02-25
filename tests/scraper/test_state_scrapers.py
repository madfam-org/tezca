"""
Tests for state congress scrapers (Baja California, Durango, Quintana Roo).

Tests initialization, base class behavior, and catalog interface.
"""

import pytest

from apps.scraper.state.baja_california import BajaCaliforniaScraper
from apps.scraper.state.base import StateCongressScraper
from apps.scraper.state.durango import DurangoScraper
from apps.scraper.state.quintana_roo import QuintanaRooScraper


class TestStateCongressScraperBase:
    """Test the StateCongressScraper base class."""

    def test_cannot_instantiate_base_directly(self):
        """Base class is abstract — cannot be instantiated."""
        with pytest.raises(TypeError):
            StateCongressScraper(state="Test", base_url="https://example.com")

    def test_base_has_abstract_methods(self):
        """Verify abstract methods exist on the base class."""
        assert hasattr(StateCongressScraper, "scrape_catalog")
        assert hasattr(StateCongressScraper, "scrape_law_content")


class TestBajaCaliforniaScraper:
    """Test Baja California state scraper."""

    def test_initialization(self):
        scraper = BajaCaliforniaScraper()
        assert scraper.state == "Baja California"
        assert "congresobc" in scraper.base_url
        assert scraper.session is not None

    def test_has_required_methods(self):
        scraper = BajaCaliforniaScraper()
        assert hasattr(scraper, "scrape_catalog")
        assert hasattr(scraper, "scrape_law_content")
        assert callable(scraper.scrape_catalog)

    def test_rate_limiting_configured(self):
        scraper = BajaCaliforniaScraper()
        assert scraper.min_request_interval >= 1.0

    def test_is_downloadable(self):
        scraper = BajaCaliforniaScraper()
        assert scraper.is_downloadable("https://example.com/law.pdf")
        assert scraper.is_downloadable("https://example.com/law.doc")
        assert scraper.is_downloadable("https://example.com/law.docx")
        assert not scraper.is_downloadable("https://example.com/page.html")

    def test_validate_law_data(self):
        scraper = BajaCaliforniaScraper()
        valid = {
            "name": "Ley de Educación",
            "url": "https://congresobc.gob.mx/ley.pdf",
            "state": "Baja California",
        }
        assert scraper.validate_law_data(valid) is True

        invalid = {"name": "", "url": "not-a-url", "state": "BC"}
        assert scraper.validate_law_data(invalid) is False


class TestDurangoScraper:
    """Test Durango state scraper."""

    def test_initialization(self):
        scraper = DurangoScraper()
        assert scraper.state == "Durango"
        assert "congresodurango" in scraper.base_url
        assert scraper.session is not None

    def test_has_required_methods(self):
        scraper = DurangoScraper()
        assert hasattr(scraper, "scrape_catalog")
        assert callable(scraper.scrape_catalog)

    def test_extract_category(self):
        scraper = DurangoScraper()
        assert scraper.extract_category("Ley de Transparencia") == "Ley"
        assert scraper.extract_category("Código Penal") in ("Código", "Codigo")
        assert scraper.extract_category("Reglamento Interior") == "Reglamento"


class TestQuintanaRooScraper:
    """Test Quintana Roo state scraper."""

    def test_initialization(self):
        scraper = QuintanaRooScraper()
        assert scraper.state == "Quintana Roo"
        assert "congresoqroo" in scraper.base_url
        assert scraper.session is not None

    def test_has_structured_data_method(self):
        """QR scraper has special CSV/XLS export method."""
        scraper = QuintanaRooScraper()
        assert hasattr(scraper, "scrape_structured_data")
        assert callable(scraper.scrape_structured_data)

    def test_has_required_methods(self):
        scraper = QuintanaRooScraper()
        assert hasattr(scraper, "scrape_catalog")
        assert callable(scraper.scrape_catalog)


class TestAllStateScrapers:
    """Cross-scraper consistency tests."""

    @pytest.mark.parametrize(
        "scraper_cls,expected_state",
        [
            (BajaCaliforniaScraper, "Baja California"),
            (DurangoScraper, "Durango"),
            (QuintanaRooScraper, "Quintana Roo"),
        ],
    )
    def test_scraper_state_name(self, scraper_cls, expected_state):
        scraper = scraper_cls()
        assert scraper.state == expected_state

    @pytest.mark.parametrize(
        "scraper_cls",
        [BajaCaliforniaScraper, DurangoScraper, QuintanaRooScraper],
    )
    def test_session_has_user_agent(self, scraper_cls):
        scraper = scraper_cls()
        ua = scraper.session.headers.get("User-Agent", "")
        assert "TezcaBot" in ua or "Mozilla" in ua

    @pytest.mark.parametrize(
        "scraper_cls",
        [BajaCaliforniaScraper, DurangoScraper, QuintanaRooScraper],
    )
    def test_normalize_url(self, scraper_cls):
        scraper = scraper_cls()
        result = scraper.normalize_url("/leyes/test.pdf")
        assert result.startswith("http")
        assert "test.pdf" in result
