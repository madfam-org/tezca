"""
Tests for SCJN Playwright scraper.

Tests initialization, interface, and record creation without requiring
a browser (Playwright is an optional dependency).
"""

import json

import pytest


class TestScjnPlaywrightScraper:
    """Test SCJN Playwright scraper interface and helpers."""

    def test_import(self):
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper

        assert ScjnPlaywrightScraper is not None

    def test_inherits_playwright_base(self):
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper
        from apps.scraper.playwright_base import PlaywrightBase

        assert issubclass(ScjnPlaywrightScraper, PlaywrightBase)

    def test_has_required_methods(self):
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper

        scraper = ScjnPlaywrightScraper.__new__(ScjnPlaywrightScraper)
        assert hasattr(scraper, "_parse_page")
        assert hasattr(scraper, "scrape_catalog")
        assert hasattr(scraper, "run")
        assert hasattr(scraper, "_navigate_to_search")
        assert hasattr(scraper, "_fill_search_form")
        assert hasattr(scraper, "_wait_for_results")
        assert hasattr(scraper, "_make_record")

    def test_make_record(self, tmp_path):
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper

        scraper = ScjnPlaywrightScraper(output_dir=str(tmp_path / "out"))
        scraper._epoca = 10
        scraper._tipo = "jurisprudencia"

        record = scraper._make_record(
            registro="2029001",
            rubro="Test Rubro",
            texto="Full text here",
            instancia="Primera Sala",
            materia="Civil",
        )

        assert record["registro"] == "2029001"
        assert record["tipo"] == "jurisprudencia"
        assert record["epoca"] == 10
        assert record["epoca_nombre"] == "Decima Epoca"
        assert record["rubro"] == "Test Rubro"
        assert record["texto"] == "Full text here"
        assert record["instancia"] == "Primera Sala"
        assert record["materia"] == "Civil"
        assert record["source"] == "sjf_scjn_playwright"
        assert "sjf.scjn.gob.mx" in record["url"]

    def test_make_record_default_url(self, tmp_path):
        """When registro is provided, URL is auto-generated."""
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper

        scraper = ScjnPlaywrightScraper(output_dir=str(tmp_path / "out"))
        scraper._epoca = 11
        scraper._tipo = "tesis_aislada"

        record = scraper._make_record(registro="12345", rubro="Test")
        assert record["url"] == "https://sjf.scjn.gob.mx/detalle/tesis/12345"

    def test_make_record_explicit_url(self, tmp_path):
        """When URL is provided, it is used directly."""
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper

        scraper = ScjnPlaywrightScraper(output_dir=str(tmp_path / "out"))
        scraper._epoca = 10
        scraper._tipo = "jurisprudencia"

        record = scraper._make_record(
            registro="999",
            rubro="Test",
            url="https://custom.url/test",
        )
        assert record["url"] == "https://custom.url/test"

    def test_epochs_imported(self):
        """Verify EPOCAS constants are available."""
        from apps.scraper.judicial.scjn_playwright import EPOCAS

        assert 10 in EPOCAS
        assert 11 in EPOCAS
        assert EPOCAS[10] == "Decima Epoca"
        assert EPOCAS[11] == "Undecima Epoca"

    def test_save_batch_with_subdirectory(self, tmp_path):
        """Test batch saving creates correct file structure."""
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper

        scraper = ScjnPlaywrightScraper(output_dir=str(tmp_path / "judicial"))
        items = [
            {
                "registro": "2029001",
                "tipo": "jurisprudencia",
                "rubro": "Test",
                "texto": "Text",
            }
        ]
        path = scraper.save_batch(items, 0, subdirectory="jurisprudencia")

        assert path.exists()
        assert "jurisprudencia" in str(path)
        data = json.loads(path.read_text())
        assert len(data) == 1
