"""Tests for ``apps.api.management.commands.classify_law_domains``.

Targets the pure ``classify_domains`` keyword-matching function — the
``Command.handle`` itself needs Django DB access and is exercised at the
integration layer.
"""

from __future__ import annotations

import pytest

from apps.api.management.commands.classify_law_domains import (
    DOMAIN_KEYWORDS,
    classify_domains,
)

# ---------------------------------------------------------------------------
# classify_domains
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,expected_domain",
    [
        ("Ley Federal del Trabajo", "labor"),
        ("Ley del Impuesto sobre la Renta", "fiscal"),
        ("Código Penal Federal", "criminal"),
        ("Código Civil Federal", "civil"),
        ("Ley General de Sociedades Mercantiles", "commercial"),
        (
            "Ley General del Equilibrio Ecológico y la Protección al Ambiente",
            "environmental",
        ),
        ("Ley General de Salud", "health"),
        ("Ley General de Educación", "education"),
    ],
)
def test_classify_domains_matches_known_law(name, expected_domain):
    out = classify_domains(name)
    assert expected_domain in out


def test_classify_domains_returns_empty_for_no_keyword():
    assert classify_domains("Documento sin palabras clave especificas") == []


def test_classify_domains_handles_empty_string():
    assert classify_domains("") == []


def test_classify_domains_handles_none_safe():
    """The function should not crash on falsy input."""
    assert classify_domains(None) == []  # type: ignore[arg-type]


def test_classify_domains_can_match_multiple():
    """A law that touches several branches gets multiple tags."""
    # "labor + fiscal" — covers both worker AND tax aspects
    out = classify_domains("Ley del Impuesto sobre Trabajo y Pensión")
    assert "labor" in out
    assert "fiscal" in out


def test_classify_domains_is_case_insensitive():
    out_upper = classify_domains("LEY FEDERAL DEL TRABAJO")
    out_lower = classify_domains("ley federal del trabajo")
    assert out_upper == out_lower


def test_classify_domains_only_one_match_per_domain():
    """Even if multiple labor keywords match, the domain is added once."""
    # "trabajo" + "trabajador" + "laboral" all match labor
    out = classify_domains("Ley del trabajo del trabajador en el ámbito laboral")
    assert out.count("labor") == 1


def test_classify_domains_word_boundaries_for_short_keywords():
    """The patterns ' iva ', ' isr ', ' ieps ', ' sat ' are bounded by spaces.

    A law mentioning "privacidad" should NOT match "iva" via substring.
    """
    out = classify_domains("Ley General de Privacidad")
    assert "fiscal" not in out


def test_domain_keywords_dict_is_populated():
    """Sanity: the constants dict has the major Mexican legal branches."""
    expected_domains = {
        "labor",
        "fiscal",
        "criminal",
        "civil",
        "commercial",
        "environmental",
        "health",
        "education",
    }
    assert expected_domains.issubset(set(DOMAIN_KEYWORDS.keys()))
