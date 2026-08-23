"""
Tests for the corpus watch (apps/scraper/scheduling/corpus_watch.py) and its
wiring into check_dof_daily.

The watch is the year-over-year trigger: it flags a yearly-reissued pinned
instrument (SEP calendario escolar, JCF ROP) when it reappears in the DOF —
the class of publication the generic DECRETO/LEY change detector misses.
Detection only; it never mutates the corpus.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.core.management import CommandError, call_command

from apps.scraper.scheduling.corpus_watch import (
    CORPUS_WATCHES,
    CORPUS_WATCHES_BY_KEY,
    SEP_CALENDARIO_WATCH,
    CorpusWatch,
    scan_entries,
)

# A real-shaped DOF entry for the 2027-2028 SEP calendario acuerdo (the
# publication that must trip the watch next year).
SEP_2027_ENTRY = {
    "title": (
        "ACUERDO número 08/07/27 por el que se establecen los calendarios "
        "escolares para el ciclo lectivo 2027-2028, aplicables en toda la "
        "República para la educación preescolar, primaria, secundaria, normal "
        "y demás para la formación de maestras y maestros de educación básica"
    ),
    "section": "PRIMERA SECCION",
    "category": "SECRETARIA DE EDUCACION PUBLICA",
    "url": "https://dof.gob.mx/nota_detalle.php?codigo=5800000&fecha=15/07/2027",
    "date": "2027-07-15",
}

# An unrelated SEP acuerdo the watch must NOT trip on (no "ciclo lectivo").
SEP_OTHER_ENTRY = {
    "title": (
        "ACUERDO número 09/08/27 por el que se emiten las Reglas de Operación "
        "del Programa La Escuela es Nuestra"
    ),
    "section": "SEGUNDA SECCION",
    "category": "SECRETARIA DE EDUCACION PUBLICA",
    "url": "https://dof.gob.mx/nota_detalle.php?codigo=5800001&fecha=10/08/2027",
    "date": "2027-08-10",
}

# A JCF ROP entry (the other watch).
JCF_2027_ENTRY = {
    "title": (
        "REGLAS de Operación del Programa Jóvenes Construyendo el Futuro para "
        "el ejercicio fiscal 2027"
    ),
    "section": "SEGUNDA SECCION",
    "category": "SECRETARIA DEL TRABAJO Y PREVISION SOCIAL",
    "url": "https://dof.gob.mx/nota_detalle.php?codigo=5800002&fecha=31/12/2026",
    "date": "2026-12-31",
}


class TestWatchRegistry:
    def test_watch_keys_are_unique(self):
        keys = [w.key for w in CORPUS_WATCHES]
        assert len(keys) == len(set(keys))

    def test_by_key_index_matches_list(self):
        assert set(CORPUS_WATCHES_BY_KEY) == {w.key for w in CORPUS_WATCHES}

    def test_sep_watch_targets_the_calendario_corpus(self):
        assert SEP_CALENDARIO_WATCH.corpus == "sep_calendario"
        assert SEP_CALENDARIO_WATCH.action.strip()
        # Instruction must point at the actual next-step tooling.
        assert "ingest_sep_calendario" in SEP_CALENDARIO_WATCH.action

    def test_every_watch_has_an_action(self):
        for watch in CORPUS_WATCHES:
            assert watch.action.strip(), watch.key


class TestCorpusWatchMatching:
    def test_sep_watch_fires_on_next_years_acuerdo(self):
        assert SEP_CALENDARIO_WATCH.matches(
            SEP_2027_ENTRY["title"], SEP_2027_ENTRY["category"]
        )

    def test_sep_watch_ignores_unrelated_sep_acuerdo(self):
        """Requires BOTH 'calendario' and 'ciclo lectivo', so a different SEP
        acuerdo does not trip it."""
        assert not SEP_CALENDARIO_WATCH.matches(
            SEP_OTHER_ENTRY["title"], SEP_OTHER_ENTRY["category"]
        )

    def test_sep_watch_requires_the_sep_issuer(self):
        """Same title, wrong issuer — no match."""
        assert not SEP_CALENDARIO_WATCH.matches(
            SEP_2027_ENTRY["title"], "SECRETARIA DE GOBERNACION"
        )

    def test_matching_is_case_insensitive(self):
        assert SEP_CALENDARIO_WATCH.matches(
            SEP_2027_ENTRY["title"].upper(), "secretaria de educacion publica"
        )

    def test_all_patterns_must_match(self):
        watch = CorpusWatch(
            key="k",
            corpus="c",
            description="d",
            title_patterns=["alpha", "omega"],
        )
        assert watch.matches("alpha and omega")
        assert not watch.matches("alpha only")


class TestScanEntries:
    def test_flags_the_sep_calendario_publication(self):
        hits = scan_entries([SEP_2027_ENTRY])
        assert len(hits) == 1
        assert hits[0].watch_key == "sep_calendario_escolar"
        assert hits[0].corpus == "sep_calendario"
        assert hits[0].url == SEP_2027_ENTRY["url"]

    def test_flags_the_jcf_publication(self):
        hits = scan_entries([JCF_2027_ENTRY])
        assert [h.watch_key for h in hits] == ["jcf_reglas_operacion"]

    def test_ignores_routine_entries(self):
        routine = {
            "title": "DECRETO por el que se reforma la Ley del Impuesto sobre la Renta",
            "category": "SECRETARIA DE HACIENDA Y CREDITO PUBLICO",
            "url": "https://dof.gob.mx/x",
        }
        assert scan_entries([routine, SEP_OTHER_ENTRY]) == []

    def test_scans_a_mixed_edition(self):
        entries = [SEP_2027_ENTRY, SEP_OTHER_ENTRY, JCF_2027_ENTRY]
        keys = sorted(h.watch_key for h in scan_entries(entries))
        assert keys == ["jcf_reglas_operacion", "sep_calendario_escolar"]

    def test_hit_to_dict_is_serializable(self):
        hit = scan_entries([SEP_2027_ENTRY])[0]
        d = hit.to_dict()
        assert set(d) == {"watch_key", "corpus", "title", "url", "action"}


class TestCheckDofDailyWiring:
    """The daily task must run the watch and surface hits, without changing
    its existing change-detection behavior."""

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.api.models.Law")
    @patch("apps.scraper.federal.dof_daily.DofScraper")
    def test_watch_hits_are_recorded_and_returned(
        self, mock_scraper_cls, mock_law, mock_log_cls
    ):
        from apps.scraper.scheduling.tasks import check_dof_daily

        mock_law.objects.values_list.return_value = []

        mock_scraper = MagicMock()
        # The SEP acuerdo is an entry but NOT a "change" (no DECRETO/LEY
        # keyword), so it only surfaces via the watch — exactly the gap.
        mock_scraper.run.return_value = {
            "entries": [SEP_2027_ENTRY],
            "changes": [],
        }
        mock_scraper_cls.return_value = mock_scraper

        mock_log_cls.objects.create.return_value = MagicMock()

        result = check_dof_daily()

        # Returned to the caller.
        assert len(result["corpus_watch_hits"]) == 1
        assert result["corpus_watch_hits"][0]["watch_key"] == "sep_calendario_escolar"

        # Recorded on the AcquisitionLog parameters.
        params = mock_log_cls.objects.create.call_args[1]["parameters"]
        assert params["corpus_watch_hits"][0]["watch_key"] == "sep_calendario_escolar"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.api.models.Law")
    @patch("apps.scraper.federal.dof_daily.DofScraper")
    def test_no_hits_leaves_an_empty_list(
        self, mock_scraper_cls, mock_law, mock_log_cls
    ):
        from apps.scraper.scheduling.tasks import check_dof_daily

        mock_law.objects.values_list.return_value = []
        mock_scraper = MagicMock()
        mock_scraper.run.return_value = {"entries": [SEP_OTHER_ENTRY], "changes": []}
        mock_scraper_cls.return_value = mock_scraper
        mock_log_cls.objects.create.return_value = MagicMock()

        result = check_dof_daily()
        assert result["corpus_watch_hits"] == []


class TestCheckCorpusWatchesCommand:
    """The on-demand checker — the manual side of the year-over-year trigger.
    Network is mocked (the command's DofScraper.fetch_daily_edition)."""

    def _patch_editions(self, by_date):
        """Return a DofScraper stub whose fetch_daily_edition returns the
        entries mapped to each constructed date."""

        def _factory(date=None):
            scraper = MagicMock()
            scraper.fetch_daily_edition.return_value = by_date.get(date, [])
            return scraper

        return patch(
            "apps.api.management.commands.check_corpus_watches.DofScraper",
            side_effect=_factory,
        )

    def test_single_date_reports_a_hit(self, capsys):
        import datetime

        target = datetime.date(2027, 7, 15)
        with self._patch_editions({target: [SEP_2027_ENTRY]}):
            call_command("check_corpus_watches", "--date", "2027-07-15")

        out = capsys.readouterr().out
        assert "sep_calendario_escolar" in out
        assert "ingest_sep_calendario" in out  # the action instruction

    def test_no_hit_says_so(self, capsys):
        import datetime

        target = datetime.date(2027, 7, 16)
        with self._patch_editions({target: [SEP_OTHER_ENTRY]}):
            call_command("check_corpus_watches", "--date", "2027-07-16")

        assert "No corpus-watch hits" in capsys.readouterr().out

    def test_date_range_scans_each_day(self, capsys):
        import datetime

        hit_day = datetime.date(2027, 7, 15)
        editions = {hit_day: [SEP_2027_ENTRY]}
        with self._patch_editions(editions) as scraper_cls:
            call_command(
                "check_corpus_watches", "--from", "2027-07-14", "--to", "2027-07-16"
            )

        # Three editions constructed (14th, 15th, 16th).
        assert scraper_cls.call_count == 3
        assert "sep_calendario_escolar" in capsys.readouterr().out

    def test_watch_filter_scopes_results(self, capsys):
        import datetime

        target = datetime.date(2026, 12, 31)
        with self._patch_editions({target: [JCF_2027_ENTRY]}):
            # Filter to SEP only — the JCF hit must be excluded.
            call_command(
                "check_corpus_watches",
                "--date",
                "2026-12-31",
                "--watch",
                "sep_calendario_escolar",
            )
        assert "No corpus-watch hits" in capsys.readouterr().out

    def test_json_output(self, capsys):
        import datetime
        import json

        target = datetime.date(2027, 7, 15)
        with self._patch_editions({target: [SEP_2027_ENTRY]}):
            call_command("check_corpus_watches", "--date", "2027-07-15", "--json")

        payload = json.loads(capsys.readouterr().out)
        assert payload["hits"][0]["watch_key"] == "sep_calendario_escolar"
        assert payload["hits"][0]["date"] == "2027-07-15"

    def test_unknown_watch_is_an_error(self):
        with pytest.raises(CommandError):
            call_command("check_corpus_watches", "--watch", "nope")

    def test_from_without_to_is_an_error(self):
        with pytest.raises(CommandError):
            call_command("check_corpus_watches", "--from", "2027-01-01")

    def test_invalid_date_is_an_error(self):
        with pytest.raises(CommandError):
            call_command("check_corpus_watches", "--date", "not-a-date")
