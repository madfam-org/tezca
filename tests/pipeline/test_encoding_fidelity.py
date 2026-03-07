"""
Tests for encoding fidelity across the data pipeline.

Covers two code paths:
  - read_data_content() in apps/api/utils/paths.py (line 201: errors="ignore")
  - Search snippet truncation in apps/api/search_views.py (line 269: source["text"][:200])

These spot-checks verify that UTF-8 text survives round-trips through file I/O
and that Python string slicing never produces invalid UTF-8 on re-encode.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from apps.api.utils.paths import read_data_content

# ---------------------------------------------------------------------------
# Edge-case seed data
# ---------------------------------------------------------------------------

EDGE_CASES = {
    "nahuatl": "Tlālticpāctli in āltepētl",
    "accented": "Artículo décimo — según el párrafo único",
    "null_bytes": "Artículo 1.\x00 La presente ley",
    "very_long": "Esta disposición legal " * 5_000,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_temp_file(content: bytes, suffix: str = ".txt") -> str:
    """Write *content* bytes to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    f.write(content)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.spotcheck
class TestEncodingFidelity:
    """Verify encoding behavior in read_data_content and snippet slicing."""

    # -- 1. Valid UTF-8 with accented chars round-trips cleanly ----------------

    def test_read_data_content_preserves_utf8(self):
        """Accented characters must survive read_data_content() without loss."""
        text = EDGE_CASES["accented"]
        path = _write_temp_file(text.encode("utf-8"))

        with patch(
            "apps.api.utils.paths.resolve_data_path_or_none",
            return_value=Path(path),
        ):
            result = read_data_content(path)

        assert result == text
        # Verify every accented character individually
        for char in ("í", "é", "ú", "á"):
            assert char in result, f"Accented char {char!r} lost during read"

    # -- 2. Invalid bytes are silently dropped (errors="ignore") ---------------

    def test_read_data_content_drops_invalid_bytes(self):
        """Invalid UTF-8 byte sequences are dropped because errors='ignore'.

        read_data_content() calls Path.read_text(encoding='utf-8', errors='ignore').
        The 'ignore' error handler silently discards bytes that cannot be decoded
        as valid UTF-8.  This is intentional: some scraped PDFs contain stray
        binary bytes, and dropping them is preferable to crashing the pipeline.
        """
        valid_part = "Ley General"
        raw = valid_part.encode("utf-8") + b"\xff\xfe" + b" vigente"
        path = _write_temp_file(raw)

        with patch(
            "apps.api.utils.paths.resolve_data_path_or_none",
            return_value=Path(path),
        ):
            result = read_data_content(path)

        # The valid prefix and suffix survive; the two invalid bytes vanish
        assert result is not None
        assert "Ley General" in result
        assert "vigente" in result
        # \xff and \xfe are not representable in UTF-8 -- they must be gone
        assert "\xff" not in result
        assert "\xfe" not in result
        assert result == "Ley General vigente"

    # -- 3. Null bytes pass through (they are valid UTF-8) ---------------------

    def test_null_bytes_in_content(self):
        """Null bytes (U+0000) are valid UTF-8 and must survive read_data_content().

        While null bytes are unusual in legal text, they can appear in
        OCR-extracted PDFs.  Since \\x00 is a valid Unicode codepoint,
        errors='ignore' does NOT strip it.
        """
        text = EDGE_CASES["null_bytes"]
        path = _write_temp_file(text.encode("utf-8"))

        with patch(
            "apps.api.utils.paths.resolve_data_path_or_none",
            return_value=Path(path),
        ):
            result = read_data_content(path)

        assert result == text
        assert "\x00" in result, "Null byte must survive -- it is valid UTF-8"

    # -- 4. Snippet slicing is safe for multi-byte characters ------------------

    def test_snippet_truncation_safe_for_multibyte(self):
        """Python text[:200] on a string with multi-byte chars is codepoint-safe.

        In search_views.py line 269, the fallback snippet is source["text"][:200].
        Python 3 strings are sequences of Unicode codepoints, so slicing at any
        position always produces a valid string -- there is no risk of splitting
        a multi-byte UTF-8 sequence the way there would be with raw bytes.

        This test places accented characters right at the slice boundary to
        confirm that the result encodes to valid UTF-8 without replacement chars.
        """
        # Build a string where positions 198-200 contain accented chars
        prefix = "X" * 198
        boundary = "áé"  # 2 chars, each 2 bytes in UTF-8
        suffix = "Z" * 100
        text = prefix + boundary + suffix  # total 300 chars

        snippet = text[:200]

        assert len(snippet) == 200
        assert snippet.endswith("áé")

        # Re-encode to UTF-8 and verify validity
        encoded = snippet.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == snippet
        # No replacement character (U+FFFD) should appear
        assert "\ufffd" not in decoded

        # Also test with Nahuatl macrons at the boundary
        nahuatl_prefix = "Y" * 198
        nahuatl_boundary = "āē"  # macron vowels, each 2 bytes in UTF-8
        nahuatl_text = nahuatl_prefix + nahuatl_boundary + "W" * 50

        nahuatl_snippet = nahuatl_text[:200]
        assert len(nahuatl_snippet) == 200
        assert nahuatl_snippet[-2:] == "āē"
        assert nahuatl_snippet.encode("utf-8").decode("utf-8") == nahuatl_snippet
