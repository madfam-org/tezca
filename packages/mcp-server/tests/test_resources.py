"""Tests for MCP resource content."""

from __future__ import annotations

from resources import DOMAINS, STATES, TAXONOMY


def test_domains_includes_generic_domains():
    """DOMAINS resource includes backward-compatible generic domains."""
    for domain in ("finance", "criminal", "labor", "civil", "administrative", "constitutional"):
        assert domain in DOMAINS, f"Missing generic domain '{domain}' in DOMAINS resource"


def test_domains_includes_scian_domains():
    """DOMAINS resource includes SCIAN 2023-aligned sector domains."""
    for domain in ("manufacturing", "commerce", "foreign_trade", "financial_services", "professional_services"):
        assert domain in DOMAINS, f"Missing SCIAN domain '{domain}' in DOMAINS resource"


def test_domains_includes_scian_codes():
    """DOMAINS resource references SCIAN sector codes."""
    assert "31-33" in DOMAINS
    assert "43+46" in DOMAINS
    assert "52" in DOMAINS
    assert "54" in DOMAINS


def test_taxonomy_includes_categories():
    """TAXONOMY resource includes all 7 legal categories."""
    for cat in ("civil", "penal", "fiscal", "mercantil", "laboral", "administrativo", "constitucional"):
        assert cat in TAXONOMY


def test_states_includes_all_32():
    """STATES resource mentions all 32 Mexican states."""
    assert "32" in STATES
    assert "Jalisco" in STATES
    assert "Ciudad de México" in STATES
