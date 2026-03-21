"""Tests for the backfill_quality_scores management command."""

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from apps.api.models import Law, LawVersion

MODULE = "apps.api.management.commands.backfill_quality_scores"


def _make_metrics(grade="B", score=75.0):
    m = MagicMock()
    m.grade = grade
    m.overall_score = score
    return m


@pytest.fixture
def federal_law(db):
    return Law.objects.create(
        official_id="cpeum",
        name="Constitución Política",
        tier="federal",
    )


@pytest.fixture
def state_law(db):
    return Law.objects.create(
        official_id="jal-codigo-civil",
        name="Código Civil de Jalisco",
        tier="state",
        state="Jalisco",
    )


def _make_version(law, xml_path="data/federal/test.xml", grade=None, score=None):
    return LawVersion.objects.create(
        law=law,
        publication_date="2024-01-01",
        xml_file_path=xml_path,
        quality_grade=grade,
        quality_score=score,
    )


@pytest.mark.django_db
class TestBackfillQualityScores:
    @patch(f"{MODULE}.resolve_data_path_or_none", return_value="/tmp/fake.xml")
    @patch(f"{MODULE}.QualityCalculator")
    def test_backfills_null_versions(self, MockCalc, mock_resolve, federal_law):
        calc_instance = MockCalc.return_value
        calc_instance.calculate.return_value = _make_metrics("A", 95.0)

        v1 = _make_version(federal_law, "data/v1.xml")
        v2 = _make_version(federal_law, "data/v2.xml")
        v3 = _make_version(federal_law, "data/v3.xml")

        call_command("backfill_quality_scores", "--all")

        for v in [v1, v2, v3]:
            v.refresh_from_db()
            assert v.quality_grade == "A"
            assert v.quality_score == 95.0

    @patch(f"{MODULE}.resolve_data_path_or_none", return_value="/tmp/fake.xml")
    @patch(f"{MODULE}.QualityCalculator")
    def test_skips_already_scored(self, MockCalc, mock_resolve, federal_law):
        calc_instance = MockCalc.return_value
        calc_instance.calculate.return_value = _make_metrics("A", 99.0)

        v1 = _make_version(federal_law, "data/v1.xml", grade="C", score=60.0)

        call_command("backfill_quality_scores", "--all")

        v1.refresh_from_db()
        assert v1.quality_grade == "C"
        assert v1.quality_score == 60.0
        calc_instance.calculate.assert_not_called()

    @patch(f"{MODULE}.resolve_data_path_or_none", return_value="/tmp/fake.xml")
    @patch(f"{MODULE}.QualityCalculator")
    def test_force_rescores(self, MockCalc, mock_resolve, federal_law):
        calc_instance = MockCalc.return_value
        calc_instance.calculate.return_value = _make_metrics("A", 99.0)

        v1 = _make_version(federal_law, "data/v1.xml", grade="C", score=60.0)

        call_command("backfill_quality_scores", "--all", "--force")

        v1.refresh_from_db()
        assert v1.quality_grade == "A"
        assert v1.quality_score == 99.0

    @patch(f"{MODULE}.resolve_data_path_or_none", return_value="/tmp/fake.xml")
    @patch(f"{MODULE}.QualityCalculator")
    def test_dry_run_no_writes(self, MockCalc, mock_resolve, federal_law):
        calc_instance = MockCalc.return_value
        calc_instance.calculate.return_value = _make_metrics("A", 95.0)

        v1 = _make_version(federal_law, "data/v1.xml")

        call_command("backfill_quality_scores", "--all", "--dry-run")

        v1.refresh_from_db()
        assert v1.quality_grade is None
        assert v1.quality_score is None

    @patch(f"{MODULE}.resolve_data_path_or_none", return_value="/tmp/fake.xml")
    @patch(f"{MODULE}.QualityCalculator")
    def test_missing_xml_path_skipped(self, MockCalc, mock_resolve, federal_law):
        _make_version(federal_law, xml_path=None)
        _make_version(federal_law, xml_path="")

        out = StringIO()
        call_command("backfill_quality_scores", "--all", stdout=out)

        assert "Found 0 LawVersion records" in out.getvalue()
        calc_instance = MockCalc.return_value
        calc_instance.calculate.assert_not_called()

    @patch(f"{MODULE}.resolve_data_path_or_none", return_value=None)
    @patch(f"{MODULE}.QualityCalculator")
    def test_nonexistent_xml_skipped(self, MockCalc, mock_resolve, federal_law):
        v1 = _make_version(federal_law, "data/missing.xml")

        out = StringIO()
        call_command("backfill_quality_scores", "--all", stdout=out)

        output = out.getvalue()
        assert "Skipped:     1" in output
        v1.refresh_from_db()
        assert v1.quality_grade is None

    @patch(f"{MODULE}.resolve_data_path_or_none", return_value="/tmp/fake.xml")
    @patch(f"{MODULE}.QualityCalculator")
    def test_tier_filter(self, MockCalc, mock_resolve, federal_law, state_law):
        calc_instance = MockCalc.return_value
        calc_instance.calculate.return_value = _make_metrics("B", 80.0)

        v_fed = _make_version(federal_law, "data/fed.xml")
        v_state = _make_version(state_law, "data/state.xml")

        call_command("backfill_quality_scores", "--all", "--tier", "federal")

        v_fed.refresh_from_db()
        v_state.refresh_from_db()
        assert v_fed.quality_grade == "B"
        assert v_state.quality_grade is None

    @patch(f"{MODULE}.resolve_data_path_or_none", return_value="/tmp/fake.xml")
    @patch(f"{MODULE}.QualityCalculator")
    def test_single_law(self, MockCalc, mock_resolve, federal_law, state_law):
        calc_instance = MockCalc.return_value
        calc_instance.calculate.return_value = _make_metrics("A", 90.0)

        v_fed = _make_version(federal_law, "data/fed.xml")
        v_state = _make_version(state_law, "data/state.xml")

        call_command("backfill_quality_scores", "--law-id", "cpeum")

        v_fed.refresh_from_db()
        v_state.refresh_from_db()
        assert v_fed.quality_grade == "A"
        assert v_state.quality_grade is None

    @patch(f"{MODULE}.resolve_data_path_or_none", return_value="/tmp/fake.xml")
    @patch(f"{MODULE}.QualityCalculator")
    def test_xml_error_grades_f(self, MockCalc, mock_resolve, federal_law):
        calc_instance = MockCalc.return_value
        calc_instance.calculate.side_effect = Exception("XML parse error")

        v1 = _make_version(federal_law, "data/broken.xml")

        call_command("backfill_quality_scores", "--all")

        v1.refresh_from_db()
        assert v1.quality_grade == "F"
        assert v1.quality_score == 0.0

    @patch(f"{MODULE}.resolve_data_path_or_none", return_value="/tmp/fake.xml")
    @patch(f"{MODULE}.QualityCalculator")
    def test_summary_output(self, MockCalc, mock_resolve, federal_law):
        calc_instance = MockCalc.return_value
        calc_instance.calculate.return_value = _make_metrics("B", 78.0)

        _make_version(federal_law, "data/v1.xml")
        _make_version(federal_law, "data/v2.xml")

        out = StringIO()
        call_command("backfill_quality_scores", "--all", stdout=out)

        output = out.getvalue()
        assert "Scored:      2" in output
        assert "B: 2" in output
        assert "Quarantined: 0" in output
