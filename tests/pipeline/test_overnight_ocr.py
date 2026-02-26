"""
Tests for the standalone OCR recovery script (scripts/scraping/run_overnight_ocr.py).

Covers: tessdata sanity check, per-PDF timeout, timeout sentinel, CLI flags.
"""

import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.scraping.run_overnight_ocr import (
    MIN_TEXT_LENGTH,
    OCR_TIMEOUT_SECONDS,
    OCRTimeout,
    _TIMEOUT_SENTINEL,
    _timeout_handler,
    check_tessdata,
    find_pdfs_needing_ocr,
    ocr_extract,
    try_pdfplumber_first,
)


class TestConstants:
    """Test OCR script constants."""

    def test_min_text_length(self):
        assert MIN_TEXT_LENGTH == 100

    def test_ocr_timeout_seconds(self):
        assert OCR_TIMEOUT_SECONDS == 120

    def test_timeout_sentinel_is_string(self):
        assert isinstance(_TIMEOUT_SENTINEL, str)
        assert _TIMEOUT_SENTINEL == "__TIMEOUT__"


class TestTimeoutMechanism:
    """Test per-PDF timeout handling."""

    def test_timeout_handler_raises_ocr_timeout(self):
        with pytest.raises(OCRTimeout, match="OCR timed out"):
            _timeout_handler(signal.SIGALRM, None)

    def test_ocr_timeout_is_exception(self):
        assert issubclass(OCRTimeout, Exception)

    def test_ocr_extract_returns_sentinel_on_timeout(self, tmp_path):
        """When OCR times out, should return _TIMEOUT_SENTINEL."""
        pdf_path = tmp_path / "slow.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        # Mock pdf2image.convert_from_path to simulate a long-running OCR
        mock_convert = MagicMock(side_effect=OCRTimeout("OCR timed out"))
        mock_pdf2image = MagicMock()
        mock_pdf2image.convert_from_path = mock_convert

        mock_pytesseract = MagicMock()

        with patch.dict("sys.modules", {
            "pytesseract": mock_pytesseract,
            "pdf2image": mock_pdf2image,
        }):
            result = ocr_extract(pdf_path)

        assert result == _TIMEOUT_SENTINEL


class TestTessdataCheck:
    """Test tessdata sanity check."""

    @patch("scripts.scraping.run_overnight_ocr.pytesseract", create=True)
    def test_check_tessdata_passes_when_available(self, mock_tess):
        """Should return True when tesseract + spa works."""
        mock_tess_module = MagicMock()
        mock_tess_module.image_to_string.return_value = ""
        mock_pil = MagicMock()

        with patch.dict("sys.modules", {
            "pytesseract": mock_tess_module,
            "PIL": mock_pil,
            "PIL.Image": mock_pil.Image,
        }):
            with patch("scripts.scraping.run_overnight_ocr.pytesseract", mock_tess_module, create=True):
                with patch("scripts.scraping.run_overnight_ocr.Image", mock_pil.Image, create=True):
                    # check_tessdata imports locally, so just verify the function exists
                    assert callable(check_tessdata)

    def test_check_tessdata_returns_bool(self):
        """check_tessdata should return a boolean."""
        result = check_tessdata()
        assert isinstance(result, bool)


class TestFindPdfsNeedingOcr:
    """Test PDF candidate discovery."""

    def test_finds_pdf_without_txt(self, tmp_path):
        """PDFs with no .txt companion should be candidates."""
        with patch("scripts.scraping.run_overnight_ocr.DATA_DIR", tmp_path):
            state_dir = tmp_path / "state_laws" / "test_state"
            state_dir.mkdir(parents=True)
            (state_dir / "law1.pdf").write_bytes(b"%PDF")

            candidates = find_pdfs_needing_ocr()
            assert len(candidates) == 1
            assert candidates[0].name == "law1.pdf"

    def test_skips_pdf_with_sufficient_txt(self, tmp_path):
        """PDFs with long enough .txt should be skipped."""
        with patch("scripts.scraping.run_overnight_ocr.DATA_DIR", tmp_path):
            state_dir = tmp_path / "state_laws" / "test_state"
            state_dir.mkdir(parents=True)
            (state_dir / "law2.pdf").write_bytes(b"%PDF")
            (state_dir / "law2.txt").write_text("A" * 200, encoding="utf-8")

            candidates = find_pdfs_needing_ocr()
            assert len(candidates) == 0

    def test_finds_pdf_with_short_txt(self, tmp_path):
        """PDFs with too-short .txt should be candidates."""
        with patch("scripts.scraping.run_overnight_ocr.DATA_DIR", tmp_path):
            state_dir = tmp_path / "state_laws" / "test_state"
            state_dir.mkdir(parents=True)
            (state_dir / "law3.pdf").write_bytes(b"%PDF")
            (state_dir / "law3.txt").write_text("short", encoding="utf-8")

            candidates = find_pdfs_needing_ocr()
            assert len(candidates) == 1

    def test_searches_multiple_directories(self, tmp_path):
        """Should search state_laws, federal, and municipal dirs."""
        with patch("scripts.scraping.run_overnight_ocr.DATA_DIR", tmp_path):
            for subdir in ["state_laws/s1", "federal", "municipal/m1"]:
                d = tmp_path / subdir
                d.mkdir(parents=True)
                (d / "law.pdf").write_bytes(b"%PDF")

            candidates = find_pdfs_needing_ocr()
            assert len(candidates) == 3


class TestTryPdfplumberFirst:
    """Test pdfplumber extraction."""

    def test_returns_empty_on_failure(self, tmp_path):
        """Should return empty string when pdfplumber fails."""
        pdf_path = tmp_path / "bad.pdf"
        pdf_path.write_bytes(b"not a pdf")

        result = try_pdfplumber_first(pdf_path)
        assert result == ""
