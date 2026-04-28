"""Tests for pure helpers inside management command modules.

Each command's ``Command.handle`` typically needs Django DB access and
gets covered at the integration layer; this file targets the smaller
pure helpers that don't.
"""

from __future__ import annotations

from apps.api.management.commands.ingest_rmf import _short_name

# ---------------------------------------------------------------------------
# ingest_rmf._short_name
# ---------------------------------------------------------------------------


def test_short_name_for_annual_rmf():
    assert _short_name("annual", 2024, {}) == "RMF 2024"


def test_short_name_for_modification():
    out = _short_name("modification", 2024, {"modification_number": 3})
    assert "Mod. RMF 2024" in out
    assert "3" in out


def test_short_name_for_modification_missing_number():
    """When modification_number is absent, falls back to '?'."""
    out = _short_name("modification", 2024, {})
    assert "?" in out


def test_short_name_for_annex():
    out = _short_name("annex", 2024, {"annex_number": "1.A"})
    assert "Anexo" in out
    assert "1.A" in out
    assert "2024" in out


def test_short_name_for_annex_missing_number():
    out = _short_name("annex", 2024, {})
    assert "?" in out


def test_short_name_unknown_type_falls_back_to_annual():
    """Unrecognized document_type falls through to the RMF default."""
    out = _short_name("something_else", 2024, {})
    assert out == "RMF 2024"
