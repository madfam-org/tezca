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
from kombu.exceptions import OperationalError

from apps.scraper.scheduling.corpus_watch import (
    CORPUS_WATCHES,
    CORPUS_WATCHES_BY_KEY,
    SEP_CALENDARIO_WATCH,
    CorpusWatch,
    scan_entries,
)
from apps.scraper.scheduling.corpus_watch_notify import notify_corpus_watch_hits

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


def _created_parameters(mock_log_cls, operation):
    """The ``parameters`` of the single AcquisitionLog row created for
    ``operation``.

    ``check_dof_daily`` writes MORE than one AcquisitionLog row on a hit: the
    ``dof_daily_check`` row, and then a ``corpus_watch_alert`` row from the
    notify hook. Reading ``call_args`` (the LAST call) therefore reads whichever
    row happened to be written last, so an assertion about the daily-check row
    must select it by operation instead. Asserting there is exactly one such row
    also pins the "one daily-check row per run" invariant.
    """
    matching = [
        call
        for call in mock_log_cls.objects.create.call_args_list
        if call.kwargs.get("operation") == operation
    ]
    assert len(matching) == 1, (
        f"expected exactly one {operation!r} AcquisitionLog row, got "
        f"{[c.kwargs.get('operation') for c in mock_log_cls.objects.create.call_args_list]}"
    )
    return matching[0].kwargs["parameters"]


class TestCheckDofDailyWiring:
    """The daily task must run the watch and surface hits, without changing
    its existing change-detection behavior."""

    @patch("apps.scraper.scheduling.corpus_watch_notify.notify_corpus_watch_hits")
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.api.models.Law")
    @patch("apps.scraper.federal.dof_daily.DofScraper")
    def test_watch_hits_are_recorded_and_returned(
        self, mock_scraper_cls, mock_law, mock_log_cls, mock_notify
    ):
        """Detection + recording, isolated from the notify hop.

        ``notify_corpus_watch_hits`` is patched (as in
        ``TestCheckDofDailyNotifyWiring``) so this stays a unit test of
        detection: unpatched, the real hook calls ``deliver_operator_alert
        .delay()``, which reaches for the Celery broker — making the outcome
        depend on whether a Redis happens to be listening on the machine running
        the suite. That hop has its own tests in ``TestCorpusWatchNotify``.
        """
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

        # Recorded on the daily-check AcquisitionLog parameters.
        params = _created_parameters(mock_log_cls, "dof_daily_check")
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


class TestCorpusWatchNotify:
    """The durability hook (FF3): a corpus-watch hit fires an operator NOTIFY,
    once per publication (de-duplicated by URL), and never seeds. AcquisitionLog
    and the Celery delivery task are mocked so this stays a pure unit test."""

    @staticmethod
    def _set_prior_alerts(mock_log_cls, rows):
        """Configure the de-dup query chain
        (AcquisitionLog.objects.filter(...).order_by(...)[:N]) to return `rows`."""
        sliced = MagicMock()
        sliced.__iter__ = lambda self: iter(rows)
        sliced.__getitem__ = lambda self, key: rows
        mock_log_cls.objects.filter.return_value.order_by.return_value = sliced

    @patch("apps.api.tasks.deliver_operator_alert")
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    def test_a_hit_fires_the_operator_alert_and_records_it(
        self, mock_log_cls, mock_deliver
    ):
        # No prior alert rows → the de-dup scan finds nothing.
        self._set_prior_alerts(mock_log_cls, [])
        mock_log_cls.objects.create.return_value = MagicMock()

        hits = scan_entries([SEP_2027_ENTRY])
        newly = notify_corpus_watch_hits(hits)

        assert newly == 1
        # The alert was delivered with the hit's serializable payload…
        mock_deliver.delay.assert_called_once()
        event, payload = mock_deliver.delay.call_args[0]
        assert event == "corpus_watch.hit"
        assert payload["watch_key"] == "sep_calendario_escolar"
        assert "ingest_sep_calendario" in payload["action"]  # the operator runbook
        # …and it was recorded (so tomorrow's scan de-dups it).
        mock_log_cls.objects.create.assert_called_once()
        recorded = mock_log_cls.objects.create.call_args[1]
        assert recorded["operation"] == "corpus_watch_alert"
        assert recorded["parameters"]["url"] == SEP_2027_ENTRY["url"]

    @patch("apps.api.tasks.deliver_operator_alert")
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    def test_a_hit_already_alerted_is_not_re_sent(self, mock_log_cls, mock_deliver):
        # A prior alert row for the SAME url → de-dup skips it.
        prior = MagicMock()
        prior.parameters = {"url": SEP_2027_ENTRY["url"]}
        self._set_prior_alerts(mock_log_cls, [prior])

        hits = scan_entries([SEP_2027_ENTRY])
        newly = notify_corpus_watch_hits(hits)

        assert newly == 0
        mock_deliver.delay.assert_not_called()
        mock_log_cls.objects.create.assert_not_called()

    @patch("apps.api.tasks.deliver_operator_alert")
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    def test_no_hits_fires_nothing(self, mock_log_cls, mock_deliver):
        assert notify_corpus_watch_hits([]) == 0
        mock_deliver.delay.assert_not_called()

    @patch("apps.api.tasks.deliver_operator_alert")
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    def test_a_notify_failure_does_not_raise(self, mock_log_cls, mock_deliver):
        # An unexpected error per hit is swallowed (best-effort): the alert must
        # never fail the DOF check.
        mock_log_cls.objects.filter.side_effect = RuntimeError("db down")
        hits = scan_entries([SEP_2027_ENTRY])
        # Does not raise; nothing counted as newly alerted.
        assert notify_corpus_watch_hits(hits) == 0

    @patch("apps.api.tasks.deliver_operator_alert")
    @patch("apps.scraper.dataops.models.AcquisitionLog")
    def test_a_broker_outage_still_records_the_hit(self, mock_log_cls, mock_deliver):
        """A dead Celery broker must not erase the year-over-year trigger.

        ``.delay()`` reaches the broker; when Redis is down it raises
        (``kombu.exceptions.OperationalError``). Previously that exception was
        raised BEFORE the hit was recorded and then swallowed wholesale, so a
        broker blip during the 7 AM beat run left NO ``corpus_watch_alert`` row
        at all — the once-a-year SEP/JCF signal vanished with nothing to replay
        from. The record must survive the delivery failure.
        """
        self._set_prior_alerts(mock_log_cls, [])
        mock_log_cls.objects.create.return_value = MagicMock()
        mock_deliver.delay.side_effect = OperationalError(
            "Error 61 connecting to localhost:6379. Connection refused."
        )

        hits = scan_entries([SEP_2027_ENTRY])
        # Best-effort contract preserved: it does not raise…
        newly = notify_corpus_watch_hits(hits)

        # …and the hit is still recorded, so the trigger is not lost.
        mock_log_cls.objects.create.assert_called_once()
        recorded = mock_log_cls.objects.create.call_args[1]
        assert recorded["operation"] == "corpus_watch_alert"
        assert recorded["parameters"]["url"] == SEP_2027_ENTRY["url"]
        # Delivery did not succeed, so it is not counted as newly alerted.
        assert newly == 0


class TestCheckDofDailyNotifyWiring:
    """The daily task must PUSH the notify hook for hits, on top of the existing
    log + AcquisitionLog record — without changing detection behavior."""

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.api.models.Law")
    @patch("apps.scraper.federal.dof_daily.DofScraper")
    def test_daily_check_notifies_on_a_hit(
        self, mock_scraper_cls, mock_law, mock_log_cls
    ):
        from apps.scraper.scheduling.tasks import check_dof_daily

        mock_law.objects.values_list.return_value = []
        mock_scraper = MagicMock()
        mock_scraper.run.return_value = {"entries": [SEP_2027_ENTRY], "changes": []}
        mock_scraper_cls.return_value = mock_scraper
        mock_log_cls.objects.create.return_value = MagicMock()

        # Patch the lazily-imported notify function at its source module so the
        # daily task's `from … import notify_corpus_watch_hits` picks up the mock.
        with patch(
            "apps.scraper.scheduling.corpus_watch_notify.notify_corpus_watch_hits"
        ) as mock_notify:
            check_dof_daily()
            mock_notify.assert_called_once()
            passed_hits = mock_notify.call_args[0][0]
            assert len(passed_hits) == 1
            assert passed_hits[0].watch_key == "sep_calendario_escolar"

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.api.models.Law")
    @patch("apps.scraper.federal.dof_daily.DofScraper")
    def test_daily_check_does_not_notify_without_a_hit(
        self, mock_scraper_cls, mock_law, mock_log_cls
    ):
        from apps.scraper.scheduling.tasks import check_dof_daily

        mock_law.objects.values_list.return_value = []
        mock_scraper = MagicMock()
        mock_scraper.run.return_value = {"entries": [SEP_OTHER_ENTRY], "changes": []}
        mock_scraper_cls.return_value = mock_scraper
        mock_log_cls.objects.create.return_value = MagicMock()

        with patch(
            "apps.scraper.scheduling.corpus_watch_notify.notify_corpus_watch_hits"
        ) as mock_notify:
            check_dof_daily()
            mock_notify.assert_not_called()
