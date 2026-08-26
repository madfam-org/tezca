"""
Tests for encoding fidelity across the data pipeline.

Covers two code paths:
  - read_data_content() in apps/api/utils/paths.py — decodes file/R2 bytes via
    _decode_bytes(), which detects mis-encoded (latin-1/cp1252) sources and
    PRESERVES their accents instead of silently deleting them.
  - Search snippet truncation in apps/api/search_views.py (source["text"][:200])

These spot-checks verify that (a) valid UTF-8 round-trips cleanly, (b) a
latin-1/cp1252 legal source keeps its accented characters (á/é/í/ñ/ó/ú) instead
of having them stripped by the old errors="ignore" behaviour, (c) genuinely
undecodable bytes are never *silently dropped*, and (d) Python string slicing
never produces invalid UTF-8 on re-encode.
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

    # -- 2. latin-1 accented source: accents PRESERVED, not deleted ------------

    def test_latin1_source_preserves_accents(self):
        """A latin-1/cp1252 legal source keeps its accents — the core fix.

        This is the defect the old suite lacked coverage for. A latin-1 source
        (SAT, some OJN feeds) decoded as UTF-8 with errors="ignore" does NOT
        raise and does NOT produce U+FFFD — it silently DELETES every accented
        byte (á/é/í/ñ/ó/ú, °, §), so the corruption was invisible to the
        encoding spot-check (which only counts U+FFFD) and accented articles
        entered Elasticsearch stripped of their accents.

        _decode_bytes() detects the real encoding and PRESERVES the accented
        characters instead of deleting them.
        """
        text = (
            "Artículo décimo tercero. La niña, el señor y el año público "
            "gozarán de protección según la Constitución. Nº 5, así."
        )
        # Encode as latin-1 (a non-UTF-8 code page the corpus really sees).
        raw = text.encode("latin-1")
        path = _write_temp_file(raw)

        with patch(
            "apps.api.utils.paths.resolve_data_path_or_none",
            return_value=Path(path),
        ):
            result = read_data_content(path)

        assert result is not None
        # Every accented character must survive — none silently deleted.
        for char in ("í", "é", "á", "ó", "ú", "ñ"):
            assert char in result, (
                f"Accented char {char!r} was DELETED (silent-corruption "
                f"regression); got {result!r}"
            )
        # Whole accented words intact (ñ must be ñ, not the cp1250 mojibake ń).
        for word in ("Artículo", "décimo", "niña", "señor", "año", "público"):
            assert word in result, f"Word {word!r} corrupted; got {result!r}"
        # Crucially: NOT the accent-stripped string the old errors="ignore"
        # path produced.
        assert "Articulo dcimo" not in result
        assert "nia" not in result

    def test_cp1252_source_preserves_special_punctuation(self):
        """cp1252 (Windows-1252) sources keep ñ and Western punctuation."""
        text = "Público Nº 5 según — la compañía española"
        raw = text.encode("cp1252")
        path = _write_temp_file(raw)

        with patch(
            "apps.api.utils.paths.resolve_data_path_or_none",
            return_value=Path(path),
        ):
            result = read_data_content(path)

        assert result is not None
        assert "ñ" in result
        assert "compañía" in result
        assert "según" in result

    # -- 3. Undecodable bytes are NEVER silently dropped -----------------------

    def test_read_data_content_never_silently_drops_bytes(self):
        """Genuinely-undecodable bytes must not vanish without a trace.

        The old errors="ignore" turned ``b"Ley General\\xff\\xfe vigente"`` into
        ``"Ley General vigente"`` — the stray bytes disappeared silently. With
        the fix the bytes are either decoded (as mojibake, if a code page maps
        them) or replaced with U+FFFD, but never silently deleted. Either way
        the surrounding valid text survives and the result differs from the
        old lossy output.
        """
        valid_prefix = "Ley General"
        valid_suffix = " vigente"
        raw = valid_prefix.encode("utf-8") + b"\xff\xfe" + valid_suffix.encode("utf-8")
        path = _write_temp_file(raw)

        with patch(
            "apps.api.utils.paths.resolve_data_path_or_none",
            return_value=Path(path),
        ):
            result = read_data_content(path)

        assert result is not None
        assert valid_prefix in result
        assert "vigente" in result
        # The defining assertion: the stray bytes were NOT silently dropped.
        assert (
            result != "Ley General vigente"
        ), "bytes were silently deleted — errors='ignore' regression"
        # Something stands in for the undecodable bytes: either a replacement
        # char or a mojibake rendering, but never nothing.
        assert ("�" in result) or (len(result) > len("Ley General vigente"))

    # -- 4. Null bytes pass through (they are valid UTF-8) ---------------------

    def test_null_bytes_in_content(self):
        """Null bytes (U+0000) are valid UTF-8 and must survive read_data_content().

        While null bytes are unusual in legal text, they can appear in
        OCR-extracted PDFs.  Since \\x00 is a valid Unicode codepoint, the strict
        UTF-8 decode succeeds and the null byte is preserved (it is never a
        decode error, so no error handler touches it).
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

    # -- 5. Snippet slicing is safe for multi-byte characters ------------------

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
