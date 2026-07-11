"""Tests for DOF daily task and health verification."""

from unittest.mock import MagicMock, patch

import pytest


class TestCheckDofDaily:
    """Tests for the check_dof_daily Celery task."""

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.api.models.Law")
    @patch("apps.scraper.federal.dof_daily.DofScraper")
    def test_passes_existing_laws_to_scraper(
        self, mock_scraper_cls, mock_law, mock_log_cls
    ):
        """Verify existing_laws from DB are passed to the scraper."""
        from apps.scraper.scheduling.tasks import check_dof_daily

        mock_law.objects.values_list.return_value = ["Ley del ISR", "Ley del IVA"]

        mock_scraper = MagicMock()
        mock_scraper.run.return_value = {"entries": [], "changes": []}
        mock_scraper_cls.return_value = mock_scraper

        mock_log_entry = MagicMock()
        mock_log_cls.objects.create.return_value = mock_log_entry

        check_dof_daily()

        mock_scraper.run.assert_called_once_with(
            existing_laws=["Ley del ISR", "Ley del IVA"]
        )

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.api.models.Law")
    @patch("apps.scraper.federal.dof_daily.DofScraper")
    def test_acquisition_log_records_ingested_count(
        self, mock_scraper_cls, mock_law, mock_log_cls
    ):
        """AcquisitionLog.ingested reflects laws actually materialized (0 when
        DOF_AUTO_INGEST_ENABLED is off), not the detected-count; the detected
        count is tracked separately in parameters."""
        from apps.scraper.scheduling.tasks import check_dof_daily

        mock_law.objects.values_list.return_value = []

        changes = [
            {"change_type": "reform", "title": "Reforma al ISR"},
            {"change_type": "new_law", "title": "Nueva Ley"},
        ]
        mock_scraper = MagicMock()
        mock_scraper.run.return_value = {"entries": [{}] * 5, "changes": changes}
        mock_scraper_cls.return_value = mock_scraper

        mock_log_entry = MagicMock()
        mock_log_cls.objects.create.return_value = mock_log_entry

        result = check_dof_daily()

        mock_log_cls.objects.create.assert_called_once()
        call_kwargs = mock_log_cls.objects.create.call_args[1]
        # auto-ingest off (default) -> nothing materialized
        assert call_kwargs["ingested"] == 0
        assert call_kwargs["found"] == 5
        assert call_kwargs["parameters"]["detected"] == 2
        assert "changes" in call_kwargs["parameters"]

    @patch("apps.scraper.dataops.models.AcquisitionLog")
    @patch("apps.api.models.Law")
    @patch("apps.scraper.federal.dof_daily.DofScraper")
    def test_returns_summary(self, mock_scraper_cls, mock_law, mock_log_cls):
        """Verify the task returns expected summary structure."""
        from apps.scraper.scheduling.tasks import check_dof_daily

        mock_law.objects.values_list.return_value = []

        mock_scraper = MagicMock()
        mock_scraper.run.return_value = {
            "entries": [{}] * 3,
            "changes": [{"change_type": "reform"}],
        }
        mock_scraper_cls.return_value = mock_scraper

        mock_log_entry = MagicMock()
        mock_log_cls.objects.create.return_value = mock_log_entry

        result = check_dof_daily()

        assert result["total_entries"] == 3
        assert result["law_changes"] == 1
        assert len(result["changes"]) == 1


class TestNomPriorityPrefixes:
    """Verify STPS prefixes in NOM priority list."""

    def test_stps_expanded_prefixes(self):
        from apps.scraper.federal.nom_scraper import _PRIORITY_PREFIXES

        stps_prefixes = [p for p in _PRIORITY_PREFIXES if "STPS" in p]
        # Should have expanded beyond 5
        assert len(stps_prefixes) >= 15
        # Critical NOMs for manufacturing and training
        assert "NOM-017-STPS" in _PRIORITY_PREFIXES  # PPE
        assert "NOM-020-STPS" in _PRIORITY_PREFIXES  # Training
        assert "NOM-030-STPS" in _PRIORITY_PREFIXES


class TestNomMonthlyBeat:
    """Verify Beat schedule includes monthly full NOM scan."""

    def test_nom_monthly_full_in_beat(self):
        from apps.indigo.settings import CELERY_BEAT_SCHEDULE

        assert "nom-monthly-full" in CELERY_BEAT_SCHEDULE
        entry = CELERY_BEAT_SCHEDULE["nom-monthly-full"]
        assert entry["task"] == "dataops.run_nom_scraper"
        assert entry["kwargs"]["priority_only"] is False
