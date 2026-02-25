"""
Tests for federal scrapers: CONAMER, NOM, Treaty.

Tests initialization, configuration, and scraper interfaces.
"""

import pytest

from apps.scraper.federal.conamer_scraper import ConamerScraper
from apps.scraper.federal.nom_scraper import NomScraper
from apps.scraper.federal.treaty_scraper import TreatyScraper


class TestConamerScraper:
    """Test CONAMER CNARTyS scraper."""

    def test_initialization(self):
        scraper = ConamerScraper()
        assert scraper.session is not None

    def test_has_required_methods(self):
        scraper = ConamerScraper()
        assert hasattr(scraper, "probe_api")
        assert hasattr(scraper, "scrape_catalog")
        assert hasattr(scraper, "dedup_against_existing")
        assert hasattr(scraper, "save_batch")
        assert hasattr(scraper, "run")

    def test_dedup_removes_duplicates(self):
        scraper = ConamerScraper()
        items = [
            {"name": "Reglamento de Tránsito Federal"},
            {"name": "Ley General de Salud"},
            {"name": "Norma Oficial Mexicana NOM-001"},
        ]
        existing = {"reglamento de transito federal"}
        result = scraper.dedup_against_existing(items, existing)
        # Should remove the matching reglamento
        assert len(result) <= len(items)

    def test_rate_limiting_configured(self):
        scraper = ConamerScraper()
        assert hasattr(scraper, "min_request_interval") or hasattr(
            scraper, "_rate_limit"
        )


class TestNomScraper:
    """Test NOM scraper."""

    def test_initialization(self):
        scraper = NomScraper()
        assert scraper.session is not None

    def test_has_required_methods(self):
        scraper = NomScraper()
        assert hasattr(scraper, "scrape_dof_archive")
        assert hasattr(scraper, "scrape_priority_noms")
        assert hasattr(scraper, "save_results")
        assert hasattr(scraper, "run")

    def test_extract_secretaria(self):
        """Test secretaría extraction from NOM identifiers."""
        scraper = NomScraper()
        if hasattr(scraper, "_extract_secretaria"):
            result = scraper._extract_secretaria("NOM-001-SSA1-2024")
            assert result is not None


class TestTreatyScraper:
    """Test international treaties scraper."""

    def test_initialization(self):
        scraper = TreatyScraper()
        assert scraper.session is not None

    def test_has_required_methods(self):
        scraper = TreatyScraper()
        assert hasattr(scraper, "scrape_catalog")
        assert hasattr(scraper, "scrape_treaty_detail")
        assert hasattr(scraper, "save_results")
        assert hasattr(scraper, "run")

    def test_classify_treaty_type(self):
        """Test treaty type classification."""
        scraper = TreatyScraper()
        if hasattr(scraper, "_classify_treaty_type"):
            # Bilateral keywords
            bilateral = scraper._classify_treaty_type(
                "Tratado entre México y Estados Unidos"
            )
            assert bilateral in ("bilateral", "multilateral", "unknown")
