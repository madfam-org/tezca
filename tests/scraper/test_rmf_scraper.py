"""
Tests for SAT RMF scraper (apps/scraper/federal/rmf_scraper.py).

Network-free: every test mocks the requests session. The interesting logic
is in `_classify` (anchor → RmfDocument), `_parse_index_links` (filter
which anchors look like documents), and `discover` (dedup across the two
SAT index pages).
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.scraper.federal.rmf_scraper import (
    RMF_CATEGORY,
    RMF_DOMAINS,
    RmfDocument,
    RmfScraper,
)


@pytest.fixture
def scraper(tmp_path):
    return RmfScraper(output_dir=str(tmp_path))


class TestClassify:
    """RmfScraper._classify: anchor text → RmfDocument."""

    def test_classifies_annex(self, scraper):
        anchor = {
            "text": "Anexo 14 de la Resolución Miscelánea Fiscal para 2026",
            "url": "https://www.sat.gob.mx/cs/Satellite?...anexo14_rmf2026.pdf",
        }
        doc = scraper._classify(anchor, year=2026)
        assert doc is not None
        assert doc.document_type == "annex"
        assert doc.annex_number == "14"
        assert doc.year == 2026
        assert doc.official_id == "rmf_2026_anexo_14"
        assert doc.category == RMF_CATEGORY
        assert doc.domains == RMF_DOMAINS

    def test_classifies_quarterly_modification_ordinal(self, scraper):
        anchor = {
            "text": "Primera Resolución de Modificaciones a la Resolución Miscelánea Fiscal para 2026",
            "url": "https://www.sat.gob.mx/.../1ra_modificacion_rmf2026.pdf",
        }
        doc = scraper._classify(anchor, year=2026)
        assert doc is not None
        assert doc.document_type == "modification"
        assert doc.modification_number == "1"
        assert doc.official_id == "rmf_2026_modificacion_1"

    def test_classifies_quarterly_modification_abbreviated(self, scraper):
        anchor = {
            "text": "3a. Modificación a la RMF 2026",
            "url": "https://www.sat.gob.mx/.../3a_mod_rmf.pdf",
        }
        doc = scraper._classify(anchor, year=2026)
        assert doc is not None
        assert doc.modification_number == "3"

    def test_classifies_annual_rmf(self, scraper):
        anchor = {
            "text": "Resolución Miscelánea Fiscal para 2026",
            "url": "https://www.sat.gob.mx/.../rmf2026.pdf",
        }
        doc = scraper._classify(anchor, year=2026)
        assert doc is not None
        assert doc.document_type == "rmf"
        assert doc.official_id == "rmf_2026"

    def test_returns_none_for_unrelated_anchor(self, scraper):
        anchor = {
            "text": "Aviso de privacidad",
            "url": "https://www.sat.gob.mx/aviso-privacidad",
        }
        doc = scraper._classify(anchor, year=2026)
        assert doc is None

    def test_annex_with_letter_suffix(self, scraper):
        # SAT occasionally publishes "Anexo 1A" sub-annexes
        anchor = {
            "text": "Anexo 1a de la RMF 2026",
            "url": "https://www.sat.gob.mx/.../anexo1a.pdf",
        }
        doc = scraper._classify(anchor, year=2026)
        assert doc is not None
        assert doc.annex_number == "1a"


class TestParseIndexLinks:
    """_parse_index_links must filter out non-document anchors and resolve
    relative URLs against SAT_BASE."""

    def test_drops_anchors_without_text(self, scraper):
        html = '<a href="/foo.pdf">   </a>'
        links = scraper._parse_index_links(html, "https://www.sat.gob.mx", year=2026)
        assert links == []

    def test_drops_unrelated_navigation_links(self, scraper):
        html = '<a href="/contacto">Contáctanos</a>'
        links = scraper._parse_index_links(html, "https://www.sat.gob.mx", year=2026)
        assert links == []

    def test_resolves_root_relative_urls_against_sat_base(self, scraper):
        html = '<a href="/normatividad/anexo1.pdf">Anexo 1 RMF</a>'
        links = scraper._parse_index_links(html, "https://www.sat.gob.mx", year=2026)
        assert len(links) == 1
        assert links[0]["url"] == "https://www.sat.gob.mx/normatividad/anexo1.pdf"

    def test_keeps_pdf_anchors_even_without_keyword(self, scraper):
        # A direct PDF link still counts even if the anchor text is terse
        html = '<a href="/normatividad/file.pdf">file.pdf</a>'
        links = scraper._parse_index_links(html, "https://www.sat.gob.mx", year=2026)
        assert len(links) == 1

    def test_filters_anchors_naming_a_different_year(self, scraper):
        html = '<a href="/normatividad/rmf2024.pdf">RMF 2024</a>'
        links = scraper._parse_index_links(html, "https://www.sat.gob.mx", year=2026)
        assert links == [], "Anchor explicitly naming 2024 should be filtered out"

    def test_keeps_anchors_naming_target_year(self, scraper):
        html = '<a href="/normatividad/rmf2026.pdf">RMF 2026</a>'
        links = scraper._parse_index_links(html, "https://www.sat.gob.mx", year=2026)
        assert len(links) == 1

    def test_keeps_anchors_with_no_year_in_text(self, scraper):
        html = '<a href="/normatividad/file.pdf">Resolución Miscelánea Fiscal</a>'
        links = scraper._parse_index_links(html, "https://www.sat.gob.mx", year=2026)
        assert len(links) == 1


class TestDiscover:
    """End-to-end discover() with mocked HTTP."""

    @patch.object(RmfScraper, "_get")
    def test_dedups_documents_appearing_on_both_indices(self, mock_get, scraper):
        # Same document on both pages — dedup should keep one
        html_main = """
        <html><body>
            <a href="/normatividad/rmf2026.pdf">Resolución Miscelánea Fiscal para 2026</a>
        </body></html>
        """
        html_annexes = """
        <html><body>
            <a href="/normatividad/rmf2026.pdf">Resolución Miscelánea Fiscal para 2026</a>
            <a href="/normatividad/anexo1.pdf">Anexo 1 RMF 2026</a>
        </body></html>
        """

        def _fake_get(url):
            resp = MagicMock()
            resp.text = html_annexes if "22703" in url else html_main
            return resp

        mock_get.side_effect = _fake_get

        documents = scraper.discover(year=2026, include_annexes=True)
        official_ids = [d.official_id for d in documents]
        assert official_ids.count("rmf_2026") == 1, "Annual RMF should be deduped"
        assert "rmf_2026_anexo_1" in official_ids

    @patch.object(RmfScraper, "_get")
    def test_returns_empty_when_indices_unreachable(self, mock_get, scraper):
        mock_get.return_value = None  # both pages 5xx / timeout
        documents = scraper.discover(year=2026, include_annexes=True)
        assert documents == []

    @patch.object(RmfScraper, "_get")
    def test_skips_annexes_index_when_disabled(self, mock_get, scraper):
        mock_get.return_value = MagicMock(text="<html></html>")
        scraper.discover(year=2026, include_annexes=False)
        # Only the main index should have been hit
        called_urls = [call.args[0] for call in mock_get.call_args_list]
        assert all("22702" in url for url in called_urls), called_urls


class TestRun:
    """run() coordinates discover + write_catalog (+ optional download)."""

    @patch.object(RmfScraper, "discover")
    def test_run_writes_catalog_even_when_empty(self, mock_discover, scraper):
        mock_discover.return_value = []
        result = scraper.run(year=2026, download_documents=False)
        assert result["total"] == 0
        assert result["downloaded"] == 0
        assert (scraper.output_dir / "catalog.json").exists()

    @patch.object(RmfScraper, "download")
    @patch.object(RmfScraper, "discover")
    def test_run_downloads_when_requested(
        self, mock_discover, mock_download, scraper, tmp_path
    ):
        doc = RmfDocument(
            official_id="rmf_2026",
            name="Resolución Miscelánea Fiscal 2026",
            url="https://www.sat.gob.mx/.../rmf2026.pdf",
            document_type="rmf",
            year=2026,
        )
        mock_discover.return_value = [doc]
        mock_download.return_value = tmp_path / "rmf_2026.pdf"

        result = scraper.run(year=2026, download_documents=True)
        assert result["total"] == 1
        assert result["downloaded"] == 1
        assert mock_download.called

    @patch.object(RmfScraper, "discover")
    def test_run_summary_groups_by_type(self, mock_discover, scraper):
        mock_discover.return_value = [
            RmfDocument(
                official_id="rmf_2026",
                name="RMF 2026",
                url="x",
                document_type="rmf",
                year=2026,
            ),
            RmfDocument(
                official_id="rmf_2026_modificacion_1",
                name="1ra Mod",
                url="y",
                document_type="modification",
                year=2026,
            ),
            RmfDocument(
                official_id="rmf_2026_anexo_1",
                name="Anexo 1",
                url="z",
                document_type="annex",
                year=2026,
            ),
            RmfDocument(
                official_id="rmf_2026_anexo_14",
                name="Anexo 14",
                url="w",
                document_type="annex",
                year=2026,
            ),
        ]
        result = scraper.run(year=2026, download_documents=False)
        assert result["by_type"]["rmf"] == 1
        assert result["by_type"]["modification"] == 1
        assert result["by_type"]["annex"] == 2


class TestRmfDocument:
    """Sanity for the dataclass — domains list defaults are independent."""

    def test_default_domains_is_independent_per_instance(self):
        a = RmfDocument(
            official_id="a",
            name="A",
            url="https://example.com/a",
            document_type="rmf",
            year=2026,
        )
        b = RmfDocument(
            official_id="b",
            name="B",
            url="https://example.com/b",
            document_type="rmf",
            year=2026,
        )
        a.domains.append("custom")
        assert (
            "custom" not in b.domains
        ), "Mutable default leaked across RmfDocument instances"
