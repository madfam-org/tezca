"""The legal-date tagging vocabulary — robust (validated) and broad (spans the
categories tezca can capture next). The feriados module tags itself against it,
so these guard the whole tagging contract."""

import pytest

from apps.scraper.federal.feriados_legales import FeriadoFact
from apps.scraper.federal.legal_date_taxonomy import (
    LEGAL_DATE_DOMAIN_SOURCES,
    LEGAL_DATE_DOMAINS,
    LEGAL_DATE_TIPO_PRIMARY_DOMAIN,
    LEGAL_DATE_TIPOS,
    is_valid_domain,
    is_valid_tipo,
    validate_domains,
    validate_tipo,
)


class TestVocabularyIsBroad:
    def test_domains_span_the_categories_we_may_leverage(self):
        # Not just labor + banking: the sectors a future feed would tag against
        # already exist, so a new source adds dates, not a vocabulary.
        assert {
            "labor",
            "banking",
            "fiscal",
            "education",
            "civic",
            "judicial",
            "electoral",
            "public_sector",
        } <= LEGAL_DATE_DOMAINS

    def test_tipos_span_the_kinds_we_may_leverage(self):
        assert {
            "descanso_obligatorio",
            "inhabil_bancario",
            "inhabil_fiscal",
            "suspension_escolar",
            "dia_civico",
            "inhabil_judicial",
            "jornada_electoral",
        } <= LEGAL_DATE_TIPOS

    def test_every_domain_is_documented_with_its_source(self):
        # A tag with no stated source is a tag no one can trust — the map is total.
        assert set(LEGAL_DATE_DOMAIN_SOURCES) == LEGAL_DATE_DOMAINS


class TestPrimaryDomainMap:
    def test_is_total_over_tipos_and_lands_in_valid_domains(self):
        # A new tipo cannot be added without declaring its home domain.
        assert set(LEGAL_DATE_TIPO_PRIMARY_DOMAIN) == LEGAL_DATE_TIPOS
        for domain in LEGAL_DATE_TIPO_PRIMARY_DOMAIN.values():
            assert domain in LEGAL_DATE_DOMAINS


class TestValidation:
    def test_is_valid_helpers(self):
        assert is_valid_domain("banking")
        assert not is_valid_domain("bancario")  # Spanish drift is refused
        assert is_valid_tipo("descanso_obligatorio")
        assert not is_valid_tipo("dia_del_taco")

    def test_validate_domains_raises_on_unknown(self):
        validate_domains(["labor", "banking"])  # ok, no raise
        with pytest.raises(ValueError, match="unknown legal-date domain"):
            validate_domains(["banking", "bancario"])

    def test_validate_tipo_raises_on_unknown(self):
        validate_tipo("inhabil_bancario")  # ok
        with pytest.raises(ValueError, match="unknown legal-date tipo"):
            validate_tipo("holiday")


class TestFeriadoFactSelfValidates:
    def test_a_valid_fact_constructs(self):
        FeriadoFact(
            "2026-01-01",
            "descanso_obligatorio",
            ("labor", "banking"),
            "x",
            "y",
            "published",
        )

    def test_an_off_vocabulary_tipo_is_refused_at_construction(self):
        with pytest.raises(ValueError, match="unknown legal-date tipo"):
            FeriadoFact("2026-01-01", "feriado", ("banking",), "x", "y", "published")

    def test_an_off_vocabulary_domain_is_refused_at_construction(self):
        with pytest.raises(ValueError, match="unknown legal-date domain"):
            FeriadoFact(
                "2026-01-01", "inhabil_bancario", ("bancario",), "x", "y", "published"
            )
