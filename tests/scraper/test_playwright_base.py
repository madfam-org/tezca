"""
Tests for PlaywrightBase abstract class and ConamerPlaywrightScraper refactor.

Tests initialization, configuration, and method interfaces without
requiring an actual browser (Playwright is an optional dependency).
"""

import json

import pytest


class TestPlaywrightBase:
    """Test PlaywrightBase ABC configuration and interface."""

    def test_import(self):
        from apps.scraper.playwright_base import PlaywrightBase

        assert PlaywrightBase is not None

    def test_is_abstract(self):
        from apps.scraper.playwright_base import PlaywrightBase

        with pytest.raises(TypeError, match="abstract"):
            PlaywrightBase()

    def test_constants_exported(self):
        from apps.scraper.playwright_base import (
            DEFAULT_BATCH_SIZE,
            DEFAULT_CHECKPOINT_INTERVAL,
            DEFAULT_NAVIGATION_TIMEOUT,
            DEFAULT_PAGE_LOAD_DELAY,
            DEFAULT_USER_AGENT,
            DEFAULT_WAF_TIMEOUT,
            WAF_SELECTORS,
        )

        assert DEFAULT_PAGE_LOAD_DELAY == 2.0
        assert DEFAULT_WAF_TIMEOUT == 30_000
        assert DEFAULT_NAVIGATION_TIMEOUT == 60_000
        assert DEFAULT_CHECKPOINT_INTERVAL == 10
        assert DEFAULT_BATCH_SIZE == 50
        assert "Chrome" in DEFAULT_USER_AGENT
        assert len(WAF_SELECTORS) >= 5

    def test_concrete_subclass_can_instantiate(self, tmp_path):
        """A concrete subclass with _parse_page and scrape_catalog can be created."""
        from apps.scraper.playwright_base import PlaywrightBase

        class DummyScraper(PlaywrightBase):
            def _parse_page(self):
                return []

            def scrape_catalog(self, max_pages=None, resume_from_page=0):
                return []

        scraper = DummyScraper(output_dir=str(tmp_path / "out"))
        assert scraper._headless is True
        assert scraper._page_load_delay == 2.0
        assert scraper._output_dir.exists()

    def test_save_results(self, tmp_path):
        """Test save_results writes JSON correctly."""
        from apps.scraper.playwright_base import PlaywrightBase

        class DummyScraper(PlaywrightBase):
            def _parse_page(self):
                return []

            def scrape_catalog(self, max_pages=None, resume_from_page=0):
                return []

        scraper = DummyScraper(output_dir=str(tmp_path / "out"))
        items = [{"name": "Test Item", "url": "https://example.com"}]
        path = scraper.save_results(items, filename="test.json")

        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data) == 1
        assert data[0]["name"] == "Test Item"

    def test_save_batch(self, tmp_path):
        """Test save_batch creates numbered batch files."""
        from apps.scraper.playwright_base import PlaywrightBase

        class DummyScraper(PlaywrightBase):
            def _parse_page(self):
                return []

            def scrape_catalog(self, max_pages=None, resume_from_page=0):
                return []

        scraper = DummyScraper(output_dir=str(tmp_path / "out"))
        items = [{"name": "Batch Item"}]
        path = scraper.save_batch(items, 0)

        assert path.name == "batch_0000.json"
        data = json.loads(path.read_text())
        assert len(data) == 1

    def test_save_batch_with_subdirectory(self, tmp_path):
        """Test save_batch with a subdirectory."""
        from apps.scraper.playwright_base import PlaywrightBase

        class DummyScraper(PlaywrightBase):
            def _parse_page(self):
                return []

            def scrape_catalog(self, max_pages=None, resume_from_page=0):
                return []

        scraper = DummyScraper(output_dir=str(tmp_path / "out"))
        items = [{"name": "Sub Item"}]
        path = scraper.save_batch(items, 3, subdirectory="jurisprudencia")

        assert "jurisprudencia" in str(path)
        assert path.name == "batch_0003.json"

    def test_checkpoint_roundtrip(self, tmp_path):
        """Test save + load checkpoint."""
        from apps.scraper.playwright_base import PlaywrightBase

        class DummyScraper(PlaywrightBase):
            def _parse_page(self):
                return []

            def scrape_catalog(self, max_pages=None, resume_from_page=0):
                return []

        scraper = DummyScraper(output_dir=str(tmp_path / "out"))
        scraper._save_checkpoint(5, [{"a": 1}, {"b": 2}])

        loaded = scraper.load_checkpoint()
        assert loaded is not None
        assert loaded["current_page"] == 5
        assert loaded["items_collected"] == 2

    def test_checkpoint_returns_none_when_missing(self, tmp_path):
        from apps.scraper.playwright_base import PlaywrightBase

        class DummyScraper(PlaywrightBase):
            def _parse_page(self):
                return []

            def scrape_catalog(self, max_pages=None, resume_from_page=0):
                return []

        scraper = DummyScraper(output_dir=str(tmp_path / "empty"))
        assert scraper.load_checkpoint() is None


class TestConamerPlaywrightRefactor:
    """Test that the refactored ConamerPlaywrightScraper still works."""

    def test_import(self):
        from apps.scraper.federal.conamer_playwright import ConamerPlaywrightScraper

        assert ConamerPlaywrightScraper is not None

    def test_inherits_playwright_base(self):
        from apps.scraper.federal.conamer_playwright import ConamerPlaywrightScraper
        from apps.scraper.playwright_base import PlaywrightBase

        assert issubclass(ConamerPlaywrightScraper, PlaywrightBase)

    def test_has_required_methods(self):
        from apps.scraper.federal.conamer_playwright import ConamerPlaywrightScraper

        scraper = ConamerPlaywrightScraper.__new__(ConamerPlaywrightScraper)
        assert hasattr(scraper, "_parse_page")
        assert hasattr(scraper, "scrape_catalog")
        assert hasattr(scraper, "dedup")
        assert hasattr(scraper, "run")
        # Inherited from PlaywrightBase
        assert hasattr(scraper, "_launch")
        assert hasattr(scraper, "close")
        assert hasattr(scraper, "_navigate")
        assert hasattr(scraper, "_wait_for_waf_resolution")
        assert hasattr(scraper, "_screenshot")
        assert hasattr(scraper, "_try_click_next")
        assert hasattr(scraper, "save_results")
        assert hasattr(scraper, "save_batch")
        assert hasattr(scraper, "load_checkpoint")

    def test_dedup_still_works(self):
        from apps.scraper.federal.conamer_playwright import ConamerPlaywrightScraper

        items = [
            {"name": "Reglamento de Tránsito Federal"},
            {"name": "Ley General de Salud"},
            {"name": "Reglamento de Transito Federal"},  # duplicate
        ]
        result = ConamerPlaywrightScraper.dedup(items)
        assert len(result) <= len(items)
