"""
Tests for NOM ingestion helpers — PDF filename fallback logic.
"""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestFindNomPdf:
    """Test _find_nom_pdf filename fallback logic."""

    def test_finds_by_id(self, tmp_path):
        from scripts.ingestion.ingest_noms import _find_nom_pdf

        pdf = tmp_path / "abc123.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")

        nom = {"id": "abc123", "nom_number": "NOM-001-SSA1-2020"}
        result = _find_nom_pdf(nom, tmp_path)
        assert result == pdf

    def test_falls_back_to_nom_number_pdf(self, tmp_path):
        from scripts.ingestion.ingest_noms import _find_nom_pdf

        pdf = tmp_path / "NOM-001-SSA1-2020.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")

        nom = {"id": "missing_id", "nom_number": "NOM-001-SSA1-2020"}
        result = _find_nom_pdf(nom, tmp_path)
        assert result == pdf

    def test_falls_back_to_nom_number_html(self, tmp_path):
        from scripts.ingestion.ingest_noms import _find_nom_pdf

        html = tmp_path / "NOM-001-SSA1-2020.html"
        html.write_text("<html>test</html>")

        nom = {"id": "missing_id", "nom_number": "NOM-001-SSA1-2020"}
        result = _find_nom_pdf(nom, tmp_path)
        assert result == html

    def test_returns_none_when_not_found(self, tmp_path):
        from scripts.ingestion.ingest_noms import _find_nom_pdf

        nom = {"id": "missing_id", "nom_number": "NOM-999-XXX-2099"}
        result = _find_nom_pdf(nom, tmp_path)
        assert result is None

    def test_sanitizes_slashes_in_nom_number(self, tmp_path):
        from scripts.ingestion.ingest_noms import _find_nom_pdf

        pdf = tmp_path / "NOM-001_SSA1_2020.pdf"
        pdf.write_bytes(b"%PDF-1.4 test")

        nom = {"id": "missing", "nom_number": "NOM-001/SSA1/2020"}
        result = _find_nom_pdf(nom, tmp_path)
        assert result == pdf

    def test_skips_empty_files(self, tmp_path):
        from scripts.ingestion.ingest_noms import _find_nom_pdf

        pdf = tmp_path / "abc123.pdf"
        pdf.write_bytes(b"")  # empty file

        nom = {"id": "abc123", "nom_number": ""}
        result = _find_nom_pdf(nom, tmp_path)
        assert result is None
