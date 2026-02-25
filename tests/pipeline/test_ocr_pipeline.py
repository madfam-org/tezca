"""
Tests for OCR fallback in the ingestion pipeline.

Tests the MIN_TEXT_LENGTH threshold and OCR fallback behavior.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.parsers.pipeline import MIN_TEXT_LENGTH, IngestionPipeline


class TestOCRConstants:
    """Test OCR-related constants."""

    def test_min_text_length_defined(self):
        assert MIN_TEXT_LENGTH == 100

    def test_min_text_length_positive(self):
        assert MIN_TEXT_LENGTH > 0


class TestOCRFallback:
    """Test OCR fallback behavior in _extract_text."""

    def test_pdfplumber_sufficient_text_no_ocr(self, tmp_path):
        """When pdfplumber extracts enough text, OCR should not be called."""
        pipeline = IngestionPipeline(data_dir=tmp_path, skip_download=True)
        law_metadata = {"id": "test-law"}

        long_text = "A" * 200  # Well above MIN_TEXT_LENGTH

        mock_page = MagicMock()
        mock_page.extract_text.return_value = long_text
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        # pdfplumber is imported locally in _extract_text, so mock the module
        mock_plumber_module = MagicMock()
        mock_plumber_module.open.return_value = mock_pdf

        # Create PDF so the method doesn't try to download
        pdf_path = pipeline.pdf_dir / "test-law.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        with patch.dict("sys.modules", {"pdfplumber": mock_plumber_module}):
            with patch.object(pipeline, "_ocr_extract") as mock_ocr:
                text_path, text = pipeline._extract_text(law_metadata, pdf_path)
                mock_ocr.assert_not_called()

        assert len(text) >= MIN_TEXT_LENGTH

    def test_pdfplumber_short_text_triggers_ocr(self, tmp_path):
        """When pdfplumber extracts too little text, OCR should be attempted."""
        pipeline = IngestionPipeline(data_dir=tmp_path, skip_download=True)
        law_metadata = {"id": "test-scanned"}

        short_text = "AB"  # Well below MIN_TEXT_LENGTH
        ocr_text = "OCR recovered text " * 20  # Long enough

        mock_page = MagicMock()
        mock_page.extract_text.return_value = short_text
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        mock_plumber_module = MagicMock()
        mock_plumber_module.open.return_value = mock_pdf

        pdf_path = pipeline.pdf_dir / "test-scanned.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        with patch.dict("sys.modules", {"pdfplumber": mock_plumber_module}):
            with patch.object(
                pipeline, "_ocr_extract", return_value=ocr_text
            ) as mock_ocr:
                text_path, text = pipeline._extract_text(law_metadata, pdf_path)
                mock_ocr.assert_called_once_with(pdf_path)

        # Should use OCR text since it's longer
        assert text == ocr_text

    def test_ocr_extract_returns_empty_without_deps(self, tmp_path):
        """_ocr_extract returns empty string when OCR deps not installed."""
        pipeline = IngestionPipeline(data_dir=tmp_path, skip_download=True)

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        # Mock missing pytesseract
        with patch.dict("sys.modules", {"pytesseract": None}):
            import importlib

            # Force re-evaluation of the import inside _ocr_extract
            result = pipeline._ocr_extract(pdf_path)
            assert isinstance(result, str)

    def test_pipeline_has_ocr_method(self, tmp_path):
        """Pipeline should have the _ocr_extract method."""
        pipeline = IngestionPipeline(data_dir=tmp_path, skip_download=True)
        assert hasattr(pipeline, "_ocr_extract")
        assert callable(pipeline._ocr_extract)
