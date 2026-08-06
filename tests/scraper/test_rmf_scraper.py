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
    def test_dedups_republished_documents(self, mock_get, scraper):
        # Annexes get re-published on the minisite as amendments land —
        # dedup by official_id keeps the first (top-most) listing.
        html = """
        <html><body>
            <a href="documentos2026/rmf/rmf/RMF_2026.pdf">Resolución Miscelánea Fiscal para 2026</a>
            <a href="documentos2026/rmf/anexos/Anexo_1_RMF2026.pdf">Anexo 1 de la RMF 2026</a>
            <a href="documentos2026/rmf/anexos/Anexo_1_RMF2026_v2.pdf">Anexo 1 de la RMF 2026</a>
        </body></html>
        """
        mock_get.return_value = MagicMock(content=html)

        documents = scraper.discover(year=2026, include_annexes=True)
        official_ids = [d.official_id for d in documents]
        assert official_ids.count("rmf_2026") == 1
        assert official_ids.count("rmf_2026_anexo_1") == 1
        anexo = next(d for d in documents if d.official_id == "rmf_2026_anexo_1")
        assert anexo.url.endswith("Anexo_1_RMF2026.pdf"), "first listing wins"

    @patch.object(RmfScraper, "_get")
    def test_fetches_the_per_year_minisite_url(self, mock_get, scraper):
        mock_get.return_value = MagicMock(content="<html></html>")
        scraper.discover(year=2026)
        called_urls = [call.args[0] for call in mock_get.call_args_list]
        assert called_urls == [
            "https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/"
            "normatividad_rmf_rgce2026.html"
        ]

    @patch.object(RmfScraper, "_get")
    def test_relative_hrefs_resolve_against_minisite_dir(self, mock_get, scraper):
        html = """
        <html><body>
            <a href="documentos2026/rmf/rmf/RMF_2026.pdf">Resolución Miscelánea Fiscal para 2026</a>
        </body></html>
        """
        mock_get.return_value = MagicMock(content=html)
        (doc,) = scraper.discover(year=2026)
        assert doc.url == (
            "https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/"
            "documentos2026/rmf/rmf/RMF_2026.pdf"
        )

    @patch.object(RmfScraper, "_get")
    def test_skips_anticipadas_compiladas_and_cotenant_regimes(self, mock_get, scraper):
        # anticipadas = preview modification texts; compiladas = consolidated
        # annex re-issues; rgce/rfa = co-located non-RMF regimes.
        html = """
        <html><body>
            <a href="documentos2026/rmf/rmf/1aRM_RMF2026.pdf">Primera Modificación a la RMF 2026</a>
            <a href="documentos2026/rmf/anticipadas/1aRM_ant.pdf">Primera Modificación a la RMF 2026 (versión anticipada)</a>
            <a href="documentos2026/rmf/compiladas/Anexo_1_comp.pdf">Anexo 1 de la RMF 2026 compilado</a>
            <a href="documentos2026/rgce/anexos/Anexo_2_RGCE.pdf">Anexo 2 de las RGCE 2026</a>
            <a href="documentos2026/rfa/RFA_2026.pdf">Resolución de Facilidades Administrativas Miscelánea Fiscal 2026</a>
        </body></html>
        """
        mock_get.return_value = MagicMock(content=html)
        documents = scraper.discover(year=2026, include_annexes=True)
        official_ids = [d.official_id for d in documents]
        assert official_ids == ["rmf_2026_modificacion_1"]
        (mod,) = documents
        assert "anticipadas" not in mod.url

    @patch.object(RmfScraper, "_get")
    def test_accordion_toggle_anchors_lose_to_real_documents(self, mock_get, scraper):
        # The minisite's collapsible sections use #fragment toggles carrying
        # the same text as the PDF links — the document must win.
        html = """
        <html><body>
            <a href="#anexos_abrirnivel3_1">Anexo 1 de la RMF 2026</a>
            <a href="documentos2026/rmf/anexos/Anexo_1_RMF2026.pdf">Anexo 1 de la RMF 2026</a>
        </body></html>
        """
        mock_get.return_value = MagicMock(content=html)
        (doc,) = scraper.discover(year=2026)
        assert doc.url.endswith(".pdf")

    @patch.object(RmfScraper, "_get")
    def test_target_year_href_overrides_legacy_title_year(self, mock_get, scraper):
        # SAT reuses legacy titles on current files (seen live: 'Novena
        # Modificación al Anexo 6 ... 2014' linking Anexo-6-RMF-2026.pdf).
        html = """
        <html><body>
            <a href="documentos2026/rmf/anexos/Anexo-6-RMF-2026.pdf">Novena Modificación al Anexo 6 de la RMF para 2014</a>
        </body></html>
        """
        mock_get.return_value = MagicMock(content=html)
        (doc,) = scraper.discover(year=2026)
        assert doc.official_id == "rmf_2026_anexo_6"

    @patch.object(RmfScraper, "_get")
    def test_parses_response_bytes_so_accented_keywords_survive(
        self, mock_get, scraper
    ):
        # SAT serves UTF-8 without a charset header; requests' .text decodes
        # latin-1 and mojibakes 'miscelánea'/'modificación' out of the
        # classifier. discover() must parse .content (bytes) instead.
        html_bytes = """
        <html><head><meta charset="utf-8"></head><body>
            <a href="documentos2026/rmf/rmf/RMF_2026.pdf">Resolución Miscelánea Fiscal para 2026</a>
            <a href="documentos2026/rmf/rmf/1aRM_RMF2026.pdf">1a Resolución de Modificaciones a la RMF para 2026</a>
        </body></html>
        """.encode("utf-8")
        resp = MagicMock()
        resp.content = html_bytes
        # simulate the latin-1 mojibake requests would produce
        resp.text = html_bytes.decode("latin-1")
        mock_get.return_value = resp

        documents = scraper.discover(year=2026)
        official_ids = sorted(d.official_id for d in documents)
        assert official_ids == ["rmf_2026", "rmf_2026_modificacion_1"]

    @patch.object(RmfScraper, "_get")
    def test_returns_empty_when_minisite_unreachable(self, mock_get, scraper):
        mock_get.return_value = None  # 5xx / timeout
        documents = scraper.discover(year=2026, include_annexes=True)
        assert documents == []

    @patch.object(RmfScraper, "_get")
    def test_include_annexes_false_filters_annex_documents(self, mock_get, scraper):
        html = """
        <html><body>
            <a href="documentos2026/rmf/rmf/RMF_2026.pdf">Resolución Miscelánea Fiscal para 2026</a>
            <a href="documentos2026/rmf/anexos/Anexo_1_RMF2026.pdf">Anexo 1 de la RMF 2026</a>
        </body></html>
        """
        mock_get.return_value = MagicMock(content=html)
        documents = scraper.discover(year=2026, include_annexes=False)
        assert [d.official_id for d in documents] == ["rmf_2026"]


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
