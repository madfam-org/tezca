"""
Tests for SCJN judicial corpus scraper.

Tests initialization, open data probing interface, and bulk import.
"""

import json

import pytest

from apps.scraper.judicial.scjn_scraper import ScjnScraper


class TestScjnScraper:
    """Test SCJN judicial scraper."""

    def test_initialization(self):
        scraper = ScjnScraper()
        assert scraper.session is not None

    def test_base_urls(self):
        from apps.scraper.judicial import scjn_scraper

        # BASE_URL may be a module-level or class-level constant
        has_base_url = (
            hasattr(scjn_scraper, "BASE_URL")
            or hasattr(ScjnScraper, "BASE_URL")
            or hasattr(ScjnScraper, "base_url")
        )
        assert has_base_url

    def test_has_required_methods(self):
        scraper = ScjnScraper()
        assert hasattr(scraper, "check_open_data")
        assert hasattr(scraper, "probe_search_api")
        assert hasattr(scraper, "scrape_jurisprudencia")
        assert hasattr(scraper, "scrape_tesis_aisladas")
        assert hasattr(scraper, "save_batch")
        assert hasattr(scraper, "run")
        assert hasattr(scraper, "import_bulk_dump")

    def test_save_batch(self, tmp_path):
        """Test batch saving creates correct file structure."""
        scraper = ScjnScraper()
        items = [
            {
                "registro": "2029001",
                "tipo": "jurisprudencia",
                "rubro": "Test thesis",
                "texto": "Full text here",
            }
        ]
        scraper.save_batch(items, str(tmp_path), "jurisprudencia", 1)

        # save_batch may nest under judicial/ or directly under batch_type/
        # Find the batch file wherever it was created
        batch_files = list(tmp_path.rglob("batch_*.json"))
        assert len(batch_files) >= 1

        # Verify content
        data = json.loads(batch_files[0].read_text())
        assert len(data) == 1
        assert data[0]["registro"] == "2029001"

    def test_import_bulk_dump_json(self, tmp_path):
        """Test importing a JSON bulk dump."""
        scraper = ScjnScraper()

        # Create a sample JSON dump
        dump_data = [
            {
                "registro": "2029001",
                "tipo": "jurisprudencia",
                "epoca": "10",
                "rubro": "Test",
                "texto": "Text",
            },
            {
                "registro": "2029002",
                "tipo": "tesis_aislada",
                "epoca": "10",
                "rubro": "Test 2",
                "texto": "Text 2",
            },
        ]
        dump_path = tmp_path / "dump.json"
        dump_path.write_text(json.dumps(dump_data))

        output_dir = tmp_path / "output"
        result = scraper.import_bulk_dump(str(dump_path), str(output_dir))

        assert result is not None

    def test_rate_limiting(self):
        """Verify rate limiting is configured for respectful scraping."""
        scraper = ScjnScraper()
        assert hasattr(scraper, "min_request_interval") or hasattr(
            scraper, "_rate_limit"
        )
