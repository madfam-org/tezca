"""
Tests for scraper idempotency — skip-existing logic.

Verifies that scrapers don't re-download files that already exist on disk,
avoiding wasted bandwidth and rate-limiting during healing re-runs.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts/scraping to path so we can import scrapers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "scraping")
)


class TestOJNDownloadDocumentSkip:
    """download_document() returns True without HTTP if file exists and >1KB."""

    def test_skips_existing_valid_file(self):
        from ojn_scraper import OJNScraper

        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = OJNScraper(output_dir=tmpdir)

            # Create a fake PDF >1KB
            file_path = Path(tmpdir) / "existing_law.pdf"
            file_path.write_bytes(b"x" * 2048)

            # Mock _request to track if it's called
            with patch.object(scraper, "_request") as mock_request:
                result = scraper.download_document(
                    "http://example.com/doc.pdf", file_path
                )

            assert result is True
            mock_request.assert_not_called()

    def test_downloads_if_file_too_small(self):
        from ojn_scraper import OJNScraper

        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = OJNScraper(output_dir=tmpdir)

            # Create a tiny file (<= 1KB) — should NOT be skipped
            file_path = Path(tmpdir) / "tiny_law.pdf"
            file_path.write_bytes(b"x" * 100)

            mock_response = MagicMock()
            mock_response.content = b"x" * 5000

            with patch.object(scraper, "_request", return_value=mock_response):
                result = scraper.download_document(
                    "http://example.com/doc.pdf", file_path
                )

            assert result is True
            assert file_path.stat().st_size == 5000

    def test_downloads_if_file_missing(self):
        from ojn_scraper import OJNScraper

        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = OJNScraper(output_dir=tmpdir)
            file_path = Path(tmpdir) / "new_law.pdf"

            mock_response = MagicMock()
            mock_response.content = b"x" * 5000

            with patch.object(scraper, "_request", return_value=mock_response):
                result = scraper.download_document(
                    "http://example.com/doc.pdf", file_path
                )

            assert result is True
            assert file_path.exists()


class TestOJNDownloadLawSkip:
    """_download_law() skips metadata fetch if file already on disk."""

    def test_skips_metadata_fetch_for_existing_file(self):
        from ojn_scraper import OJNScraper

        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = OJNScraper(output_dir=tmpdir)
            state_dir = Path(tmpdir) / "test_state"
            state_dir.mkdir()

            # Pre-create the file matching the expected pattern
            existing = state_dir / "test_law_42.pdf"
            existing.write_bytes(b"x" * 2048)

            results = {
                "successful": 0,
                "failed": 0,
                "laws": [],
                "failed_laws": [],
            }

            law = {"file_id": 42, "name": "Test Law", "state_id": 1, "power_id": 2}

            with patch.object(scraper, "get_law_metadata") as mock_meta:
                scraper._download_law(law, state_dir, results)

            # Metadata should NOT have been fetched
            mock_meta.assert_not_called()
            assert results["successful"] == 1
            assert results["laws"][0]["skipped"] is True
            assert results["laws"][0]["file_id"] == 42

    def test_fetches_metadata_if_no_existing_file(self):
        from ojn_scraper import OJNScraper

        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = OJNScraper(output_dir=tmpdir)
            state_dir = Path(tmpdir) / "test_state"
            state_dir.mkdir()

            results = {
                "successful": 0,
                "failed": 0,
                "laws": [],
                "failed_laws": [],
            }

            law = {"file_id": 99, "name": "New Law", "state_id": 1, "power_id": 2}

            # Return None from metadata (simulates failure)
            with patch.object(
                scraper, "get_law_metadata", return_value=None
            ) as mock_meta:
                scraper._download_law(law, state_dir, results)

            mock_meta.assert_called_once_with(99)
            assert results["failed"] == 1


class TestOJNMunicipalSkip:
    """scrape_municipal_laws() skips already-downloaded files."""

    def test_skips_existing_municipal_file(self):
        from ojn_scraper import OJNScraper

        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = OJNScraper(output_dir=tmpdir)

            # Create the municipal output directory
            muni_dir = Path(str(tmpdir).replace("state_laws", "municipal_laws"))
            state_dir = muni_dir / "test_state"
            state_dir.mkdir(parents=True)

            # Pre-create a file matching the expected pattern
            existing = state_dir / "ley_municipal_55.pdf"
            existing.write_bytes(b"x" * 2048)

            mock_laws = [
                {"file_id": 55, "name": "Ley Municipal", "state_id": 1, "power_id": 2},
            ]

            with patch.object(scraper, "get_state_laws", return_value=mock_laws):
                with patch.object(scraper, "get_law_metadata") as mock_meta:
                    results = scraper.scrape_municipal_laws(
                        1, "Test State", power_ids=[2]
                    )

            mock_meta.assert_not_called()
            assert results["successful"] == 1
            assert results["laws"][0]["skipped"] is True


class TestTier1DownloadPdfSkip:
    """download_pdf() returns True without HTTP if file exists and >1KB."""

    def test_skips_existing_valid_file(self):
        from scrape_tier1_cities import download_pdf

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "existing.pdf"
            file_path.write_bytes(b"x" * 2048)

            with patch("scrape_tier1_cities.requests.Session") as mock_session:
                result = download_pdf("http://example.com/doc.pdf", file_path)

            assert result is True
            # Session should never be instantiated
            mock_session.assert_not_called()

    def test_downloads_if_file_missing(self):
        from scrape_tier1_cities import download_pdf

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "new.pdf"

            mock_response = MagicMock()
            mock_response.content = b"x" * 5000
            mock_response.raise_for_status = MagicMock()

            mock_session = MagicMock()
            mock_session.get.return_value = mock_response

            result = download_pdf(
                "http://example.com/doc.pdf", file_path, session=mock_session
            )

            assert result is True
            mock_session.get.assert_called_once()

    def test_downloads_if_file_too_small(self):
        from scrape_tier1_cities import download_pdf

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "tiny.pdf"
            file_path.write_bytes(b"x" * 500)

            mock_response = MagicMock()
            mock_response.content = b"x" * 5000
            mock_response.raise_for_status = MagicMock()

            mock_session = MagicMock()
            mock_session.get.return_value = mock_response

            result = download_pdf(
                "http://example.com/doc.pdf", file_path, session=mock_session
            )

            assert result is True
            mock_session.get.assert_called_once()
