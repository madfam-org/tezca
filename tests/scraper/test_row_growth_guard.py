"""Tests for apps/scraper/scheduling/row_growth_guard.py.

Covers the recurrence-guard for the "scraper green but zero rows landed"
wiring-gap bug class (CONAMER #140, judicial #141, DOF #146, RMF/treaty
#156): a scraper logs a healthy AcquisitionLog row (found>0, no error)
but the corpus table it feeds never grows because nothing wired the
ingest command. Tests drive ``check_row_growth`` directly across multiple
simulated runs, with ``_ROW_GROWTH_PIPELINES`` swapped for a single fake
pipeline so each test controls exactly what the "corpus count" and "had a
successful scrape" signals report — no real DB or AcquisitionLog
queryset needed.

Integration coverage confirming the warnings surface through
``check_scraper_health``'s report lives in
``tests/scraper/test_scheduling_tasks.py`` (``TestCheckScraperHealth``),
mirroring how DOF materialization has both dedicated unit tests here-style
and task-level coverage in the shared file.
"""

import json
from datetime import timedelta

from django.utils import timezone


class TestCheckRowGrowth:
    def _fake_pipelines(self, count_fn):
        return {
            "fake_pipeline": {
                "operation_prefixes": ("fake_scrape",),
                "count_fn": count_fn,
            }
        }

    def test_flat_rows_with_successful_scrapes_triggers_after_n_runs(
        self, tmp_path, monkeypatch
    ):
        """Count never moves + scrapes keep succeeding => warning on the
        3rd consecutive flat run, not before."""
        from apps.scraper.scheduling import row_growth_guard as rgg

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            rgg, "_ROW_GROWTH_PIPELINES", self._fake_pipelines(lambda: 42)
        )
        monkeypatch.setattr(
            rgg, "_pipeline_had_successful_scrape", lambda prefixes, since: True
        )

        now = timezone.now()
        # Run 1: establishes the baseline count, no prior state to compare.
        warnings_1 = rgg.check_row_growth(now)
        # Run 2: flat vs run 1 => flat_runs=1
        warnings_2 = rgg.check_row_growth(now + timedelta(days=1))
        # Run 3: flat vs run 2 => flat_runs=2
        warnings_3 = rgg.check_row_growth(now + timedelta(days=2))
        # Run 4: flat vs run 3 => flat_runs=3 => triggers
        warnings_4 = rgg.check_row_growth(now + timedelta(days=3))

        assert warnings_1 == []
        assert warnings_2 == []
        assert warnings_3 == []
        assert len(warnings_4) == 1
        assert "fake_pipeline" in warnings_4[0]
        assert "corpus rows flat" in warnings_4[0]

    def test_growing_rows_never_trigger(self, tmp_path, monkeypatch):
        """Count increases every run => never flags, regardless of run count."""
        from apps.scraper.scheduling import row_growth_guard as rgg

        monkeypatch.chdir(tmp_path)
        counts = iter([10, 20, 30, 40, 50])
        monkeypatch.setattr(
            rgg, "_ROW_GROWTH_PIPELINES", self._fake_pipelines(lambda: next(counts))
        )
        monkeypatch.setattr(
            rgg, "_pipeline_had_successful_scrape", lambda prefixes, since: True
        )

        now = timezone.now()
        all_warnings = []
        for i in range(5):
            all_warnings.extend(rgg.check_row_growth(now + timedelta(days=i)))

        assert all_warnings == []

    def test_flat_rows_without_scrapes_does_not_trigger(self, tmp_path, monkeypatch):
        """Count flat but no successful scrape happened => nothing ran, so
        a flat count isn't evidence of a wiring gap. Never warn."""
        from apps.scraper.scheduling import row_growth_guard as rgg

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            rgg, "_ROW_GROWTH_PIPELINES", self._fake_pipelines(lambda: 7)
        )
        monkeypatch.setattr(
            rgg, "_pipeline_had_successful_scrape", lambda prefixes, since: False
        )

        now = timezone.now()
        all_warnings = []
        for i in range(6):
            all_warnings.extend(rgg.check_row_growth(now + timedelta(days=i)))

        assert all_warnings == []

    def test_guard_exception_does_not_raise_and_returns_empty(
        self, tmp_path, monkeypatch
    ):
        """Any exception inside the guard (bad count_fn, corrupt state, DB
        error) is swallowed — check_scraper_health's report must never
        break because of this secondary signal."""
        from apps.scraper.scheduling import row_growth_guard as rgg

        monkeypatch.chdir(tmp_path)

        def _boom():
            raise RuntimeError("simulated DB outage")

        monkeypatch.setattr(rgg, "_ROW_GROWTH_PIPELINES", self._fake_pipelines(_boom))

        result = rgg.check_row_growth(timezone.now())
        assert result == []

    def test_corrupt_state_file_falls_back_to_fresh_state(self, tmp_path, monkeypatch):
        """A corrupt data/health/corpus_counts.json must not break the
        health report — falls back to fresh state instead of raising."""
        from apps.scraper.scheduling import row_growth_guard as rgg

        monkeypatch.chdir(tmp_path)
        health_dir = tmp_path / "data" / "health"
        health_dir.mkdir(parents=True)
        (health_dir / "corpus_counts.json").write_text("{not valid json")

        monkeypatch.setattr(
            rgg, "_ROW_GROWTH_PIPELINES", self._fake_pipelines(lambda: 1)
        )
        monkeypatch.setattr(
            rgg, "_pipeline_had_successful_scrape", lambda prefixes, since: True
        )

        result = rgg.check_row_growth(timezone.now())
        assert result == []  # first observed run after reset, no baseline yet

    def test_state_file_persists_between_runs(self, tmp_path, monkeypatch):
        """Corpus counts are written to data/health/corpus_counts.json in
        the checkpoint.json style used elsewhere in the scraper (e.g.
        PlaywrightBase._save_checkpoint)."""
        from apps.scraper.scheduling import row_growth_guard as rgg

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            rgg, "_ROW_GROWTH_PIPELINES", self._fake_pipelines(lambda: 99)
        )
        monkeypatch.setattr(
            rgg, "_pipeline_had_successful_scrape", lambda prefixes, since: True
        )

        rgg.check_row_growth(timezone.now())

        state_path = tmp_path / "data" / "health" / "corpus_counts.json"
        assert state_path.exists()
        state = json.loads(state_path.read_text())
        assert state["fake_pipeline"]["count"] == 99
        assert "_last_check_at" in state
