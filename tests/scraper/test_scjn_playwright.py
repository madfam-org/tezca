"""
Tests for SCJN Playwright scraper.

Tests initialization, interface, and record creation without requiring
a browser (Playwright is an optional dependency).
"""

import pytest

pytest.importorskip("playwright")

import json


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
        assert "sjfsemanal.scjn.gob.mx" in record["url"]

    def test_make_record_default_url(self, tmp_path):
        """When registro is provided, URL uses sjfsemanal subdomain."""
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper

        scraper = ScjnPlaywrightScraper(output_dir=str(tmp_path / "out"))
        scraper._epoca = 11
        scraper._tipo = "tesis_aislada"

        record = scraper._make_record(registro="12345", rubro="Test")
        assert record["url"] == "https://sjfsemanal.scjn.gob.mx/detalle/tesis/12345"

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

    def test_detail_url_uses_sjfsemanal(self, tmp_path):
        """Verify URLs use sjfsemanal subdomain, not sjf."""
        from apps.scraper.judicial.scjn_playwright import (
            SJF_BASE_URL,
            SJF_DETAIL_URL,
            ScjnPlaywrightScraper,
        )

        assert "sjfsemanal" in SJF_BASE_URL
        assert "sjfsemanal" in SJF_DETAIL_URL

        scraper = ScjnPlaywrightScraper(output_dir=str(tmp_path / "out"))
        scraper._epoca = 10
        scraper._tipo = "jurisprudencia"
        record = scraper._make_record(registro="2031846", rubro="Test")
        assert "sjfsemanal.scjn.gob.mx" in record["url"]
        assert "2031846" in record["url"]

    def test_has_enrichment_methods(self):
        """Verify enrichment methods exist."""
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper

        scraper = ScjnPlaywrightScraper.__new__(ScjnPlaywrightScraper)
        assert hasattr(scraper, "_fetch_detail_page")
        assert hasattr(scraper, "_enrich_records")
        assert hasattr(scraper, "run_enrich_only")

    def test_enrich_records_skips_populated(self, tmp_path):
        """Records that already have texto are skipped."""
        from apps.scraper.judicial.scjn_playwright import ScjnPlaywrightScraper

        scraper = ScjnPlaywrightScraper(output_dir=str(tmp_path / "out"))
        scraper._epoca = 10
        scraper._tipo = "jurisprudencia"

        records = [
            {"registro": "111", "rubro": "Existing", "texto": "Already has text"},
            {"registro": "222", "rubro": "Also Full", "texto": "More text"},
        ]
        # _enrich_records should return immediately since all have texto
        # No browser is launched, so no _page attribute — that's fine
        result = scraper._enrich_records(records)
        assert len(result) == 2
        assert result[0]["texto"] == "Already has text"

    def test_parse_detail_text(self, tmp_path):
        """Test _fetch_detail_page regex parsing on sample inner_text output."""
        import re

        # Simulate the regex parsing logic without needing Playwright
        raw_text = """Registro digital: 2031846
Materia(s): Común
Tesis: P./J. 16/2026 (12a.)
Instancia: Pleno
Tipo: Jurisprudencia
Fuente: Gaceta del Semanario
Publicación: viernes 07 de marzo de 2026 10:16 horas

COMPETENCIA PARA CONOCER DE LOS JUICIOS DE AMPARO INDIRECTO. CORRESPONDE A LOS JUZGADOS DE DISTRITO.

Hechos: Los Tribunales Colegiados de Circuito denunciaron la posible contradicción de criterios.

Criterio jurídico: El Pleno de la Suprema Corte de Justicia de la Nación determina que...

Justificación: Lo anterior es así porque el análisis del marco constitucional y legal permite concluir...

PLENO.
Ponente: Alfredo Gutiérrez Ortiz Mena"""

        # Test label extraction
        materia_match = re.search(r"Materia\(s\):\s*(.+)", raw_text)
        assert materia_match and materia_match.group(1).strip() == "Común"

        tesis_match = re.search(r"Tesis:\s*(.+)", raw_text)
        assert tesis_match and tesis_match.group(1).strip() == "P./J. 16/2026 (12a.)"

        instancia_match = re.search(r"Instancia:\s*(.+)", raw_text)
        assert instancia_match and instancia_match.group(1).strip() == "Pleno"

        ponente_match = re.search(r"Ponente:\s*(.+)", raw_text)
        assert ponente_match
        assert "Gutiérrez" in ponente_match.group(1)

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
