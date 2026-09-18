"""Feriados legales — the LFT Art. 74 computation and the CNBV bank additions.

Pure module (no Django, no DB): a year in, a dated artifact out. The dates are
checked against the calendar by hand; the provenance split is the contract that
keeps an unverified bank date out of a client-facing payment vence.
"""

from datetime import date

from apps.scraper.federal.feriados_legales import (
    FERIADOS_CATEGORY,
    FERIADOS_DOCUMENTS_BY_ANIO,
    PUBLISHED,
    SCHEMA,
    SEED_UNVERIFIED,
    _easter,
    _nth_weekday,
    dias_descanso_obligatorio,
    extract_feriados,
    feriados_bancarios,
    inhabiles_bancarios_adicionales,
    is_bancario_verified,
)


class TestEaster:
    def test_known_gregorian_easters(self):
        assert _easter(2024) == date(2024, 3, 31)
        assert _easter(2025) == date(2025, 4, 20)
        assert _easter(2026) == date(2026, 4, 5)
        assert _easter(2027) == date(2027, 3, 28)


class TestNthWeekday:
    def test_first_and_third_mondays(self):
        # 2026-02-01 is a Sunday → first Monday is the 2nd.
        assert _nth_weekday(2026, 2, 0, 1) == date(2026, 2, 2)
        # 2026-03-01 is a Sunday → third Monday is the 16th.
        assert _nth_weekday(2026, 3, 0, 3) == date(2026, 3, 16)
        # 2026-11-01 is a Sunday → third Monday is the 16th.
        assert _nth_weekday(2026, 11, 0, 3) == date(2026, 11, 16)
        # 2027-02-01 is itself a Monday → it is the first Monday.
        assert _nth_weekday(2027, 2, 0, 1) == date(2027, 2, 1)
        # 2027-11-01 is a Monday → third Monday is the 15th.
        assert _nth_weekday(2027, 11, 0, 3) == date(2027, 11, 15)


class TestDiasDescansoObligatorio:
    def test_2026_set(self):
        got = {(f.date, f.title) for f in dias_descanso_obligatorio(2026)}
        assert got == {
            ("2026-01-01", "Año Nuevo"),
            ("2026-02-02", "Conmemoración del 5 de febrero (Constitución)"),
            ("2026-03-16", "Conmemoración del 21 de marzo (Natalicio de Juárez)"),
            ("2026-05-01", "Día del Trabajo"),
            ("2026-09-16", "Independencia de México"),
            ("2026-11-16", "Conmemoración del 20 de noviembre (Revolución)"),
            ("2026-12-25", "Navidad"),
        }

    def test_all_published_and_banks_observe_them(self):
        for f in dias_descanso_obligatorio(2026):
            assert f.provenance == PUBLISHED
            assert f.tipo == "descanso_obligatorio"
            assert set(f.domains) == {"labor", "banking"}
            assert f.fundamento.startswith("LFT Art. 74 fr.")

    def test_sexennial_transmision_only_on_transmision_years(self):
        # 2024, 2030 carry the 1-dic transmisión; 2026/2027 do not.
        assert any(f.date == "2030-12-01" for f in dias_descanso_obligatorio(2030))
        assert any(f.date == "2024-12-01" for f in dias_descanso_obligatorio(2024))
        assert not any(f.date == "2026-12-01" for f in dias_descanso_obligatorio(2026))
        assert not any(f.date == "2027-12-01" for f in dias_descanso_obligatorio(2027))
        assert len(dias_descanso_obligatorio(2030)) == 8
        assert len(dias_descanso_obligatorio(2026)) == 7

    def test_dates_sorted(self):
        dates = [f.date for f in dias_descanso_obligatorio(2027)]
        assert dates == sorted(dates)


class TestInhabilesBancariosAdicionales:
    def test_2026_additions(self):
        got = {(f.date, f.title) for f in inhabiles_bancarios_adicionales(2026)}
        # Easter 2026 = Apr 5 → Jueves Santo Apr 2, Viernes Santo Apr 3.
        assert got == {
            ("2026-04-02", "Jueves Santo"),
            ("2026-04-03", "Viernes Santo"),
            ("2026-11-02", "Día de Muertos"),
            ("2026-12-12", "Día de la Virgen de Guadalupe"),
        }

    def test_2027_semana_santa_moves_with_easter(self):
        got = {f.date for f in inhabiles_bancarios_adicionales(2027)}
        # Easter 2027 = Mar 28 → Jueves Santo Mar 25, Viernes Santo Mar 26.
        assert "2027-03-25" in got
        assert "2027-03-26" in got

    def test_2026_is_read_from_the_ingested_disposicion(self):
        # 2026 has an ingested CNBV disposición (DOF codigo 5775684), so the bank
        # additions are published and cite that CORPUS document — the dates are
        # read from the ingested legal source, not floating constants.
        assert is_bancario_verified(2026) is True
        for f in inhabiles_bancarios_adicionales(2026):
            assert f.provenance == PUBLISHED
            assert f.tipo == "inhabil_bancario"
            assert tuple(f.domains) == ("banking",)
            assert "5775684" in f.fundamento
            assert "corpus cnbv-dias-inhabiles-bancarios-2026" in f.fundamento

    def test_an_unpinned_year_falls_back_to_seed_unverified(self):
        # A year whose CNBV calendar has not been read from the DOF stays honest.
        assert is_bancario_verified(2028) is False
        for f in inhabiles_bancarios_adicionales(2028):
            assert f.provenance == SEED_UNVERIFIED
            assert tuple(f.domains) == ("banking",)


class TestFeriadosBancarios:
    def test_2026_union_matches_the_dof_authoritative_list(self):
        # The full 2026 bank calendar, verbatim from DOF codigo 5775684 Art. 1:
        # 1 ene, 1er lun feb, 3er lun mar, 2 y 3 abr, 1 may, 16 sep, 2 nov,
        # 3er lun nov, 12 y 25 dic.
        expected = {
            "2026-01-01",
            "2026-02-02",
            "2026-03-16",
            "2026-04-02",
            "2026-04-03",
            "2026-05-01",
            "2026-09-16",
            "2026-11-02",
            "2026-11-16",
            "2026-12-12",
            "2026-12-25",
        }
        banc = feriados_bancarios(2026)
        dates = [f.date for f in banc]
        assert set(dates) == expected
        assert len(dates) == 11
        assert dates == sorted(dates)
        assert len(set(dates)) == len(dates)  # no date is both an Art. 74 and a CNBV add

    def test_the_bancario_domain_selects_the_whole_set(self):
        # A payment vence takes every date carrying the "bancario" domain — which
        # is the whole union (Art. 74 banks-closed + the CNBV additions).
        banc = {f.date for f in feriados_bancarios(2026) if "banking" in f.domains}
        assert len(banc) == 11


class TestArtifact:
    def test_schema_shape_2026_is_verified(self):
        art = extract_feriados(2026)
        assert art["schema"] == SCHEMA
        assert art["anio"] == 2026
        assert art["bancario_verificado"] is True
        assert art["source"]["descanso_obligatorio"]["provenance"] == PUBLISHED
        # Verified year → bancario source cites the ingested corpus document.
        bancario = art["source"]["inhabil_bancario"]
        assert bancario["provenance"] == PUBLISHED
        assert bancario["dof_codigo"] == "5775684"
        assert bancario["corpus_official_id"] == "cnbv-dias-inhabiles-bancarios-2026"


class TestFeriadosDocuments:
    def test_the_2026_disposicion_is_a_registered_source_document(self):
        doc = FERIADOS_DOCUMENTS_BY_ANIO[2026]
        assert doc.official_id == "cnbv-dias-inhabiles-bancarios-2026"
        assert doc.dof_codigo == "5775684"
        assert doc.publication_date == "2025-12-10"
        assert doc.category == FERIADOS_CATEGORY == "dias_inhabiles_bancarios"
        assert doc.domains == ["banking"]
        # The derived DOF URL uses the DD/MM/YYYY query format.
        assert doc.dof_url == "https://dof.gob.mx/nota_detalle.php?codigo=5775684&fecha=10/12/2025"

    def test_unpinned_year_artifact_is_unverified(self):
        art = extract_feriados(2028)
        assert art["bancario_verificado"] is False
        assert art["source"]["inhabil_bancario"]["provenance"] == SEED_UNVERIFIED

    def test_events_sorted_single_day_and_provenance_split(self):
        art = extract_feriados(2026)
        events = art["events"]
        assert len(events) == 11
        assert [e["date"] for e in events] == sorted(e["date"] for e in events)
        # Legal feriados are single days: no range ever appears.
        assert all("end_date" not in e for e in events)
        # 2026 is fully verified: every event is published.
        for e in events:
            assert e["provenance"] == PUBLISHED

    def test_unpinned_year_splits_provenance(self):
        events = extract_feriados(2028)["events"]
        for e in events:
            if e["tipo"] == "descanso_obligatorio":
                assert e["provenance"] == PUBLISHED  # the law is the law
            else:
                assert e["provenance"] == SEED_UNVERIFIED  # bank adds unpinned
