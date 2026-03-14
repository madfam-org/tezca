"""
Integration tests for the spot_check management command.

Tests that the command runs, produces valid JSON output, includes expected
check categories, handles the --golden-set flag, and reports consistent
summary counts.
"""

import json
import os
import tempfile
import uuid

import pytest
from django.core.management import call_command
from django.test import TestCase

from apps.api.models import Law, LawVersion


@pytest.mark.spotcheck
class TestSpotCheckCommand(TestCase):
    """Verify spot_check management command behavior with synthetic data."""

    def setUp(self):
        """Create minimal Law + LawVersion records for the command to sample."""
        uid = uuid.uuid4().hex[:8]

        self.law_fed = Law.objects.create(
            official_id=f"test-spot-fed-{uid}",
            name="Ley Federal de Prueba Spot Check",
            tier="federal",
            status="vigente",
        )
        LawVersion.objects.create(
            law=self.law_fed,
            publication_date="2024-01-15",
        )

        self.law_state = Law.objects.create(
            official_id=f"test-spot-state-{uid}",
            name="Ley Estatal de Prueba Spot Check",
            tier="state",
            state="Colima",
            status="vigente",
        )
        LawVersion.objects.create(
            law=self.law_state,
            publication_date="2024-06-20",
        )

        self.law_muni = Law.objects.create(
            official_id=f"test-spot-muni-{uid}",
            name="Reglamento Municipal de Prueba",
            tier="municipal",
            municipality="Guadalajara",
            state="Jalisco",
            status="vigente",
        )
        LawVersion.objects.create(
            law=self.law_muni,
            publication_date="2024-03-10",
        )

    def test_command_runs_without_crash(self):
        """spot_check --limit 3 executes without raising an exception.

        The command calls sys.exit(1) if any check fails, which Django
        translates to SystemExit. We accept either a clean exit or a
        SystemExit (indicating failures found but command ran to completion).
        """
        try:
            call_command("spot_check", "--limit", "1")
        except SystemExit:
            # Command found failures in checks -- that is acceptable;
            # the test only verifies the command does not crash unexpectedly.
            pass

    def test_report_json_valid(self):
        """spot_check --output produces valid JSON with the expected top-level keys."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = tmp.name

        try:
            try:
                call_command("spot_check", "--limit", "1", "--output", output_path)
            except SystemExit:
                pass

            with open(output_path, encoding="utf-8") as f:
                report = json.load(f)

            expected_keys = {"timestamp", "laws_sampled", "checks", "summary"}
            assert expected_keys.issubset(
                report.keys()
            ), f"Missing keys: {expected_keys - report.keys()}"

            assert isinstance(report["checks"], list)
            assert isinstance(report["summary"], dict)
            assert isinstance(report["laws_sampled"], int)
            assert report["laws_sampled"] >= 1
        finally:
            os.unlink(output_path)

    def test_all_check_categories_present(self):
        """At least some of the expected check types appear in the report."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = tmp.name

        try:
            try:
                call_command("spot_check", "--limit", "1", "--output", output_path)
            except SystemExit:
                pass

            with open(output_path, encoding="utf-8") as f:
                report = json.load(f)

            check_names = {c["check"] for c in report["checks"]}

            # These are core checks that run for every law regardless of ES availability
            core_checks = {"field_lengths", "file_existence", "date_sentinel"}
            found = core_checks & check_names

            assert len(found) >= 2, (
                f"Expected at least 2 of {core_checks} in check output, "
                f"but only found {found}. All checks: {check_names}"
            )
        finally:
            os.unlink(output_path)

    def test_golden_set_flag(self):
        """spot_check --golden-set runs without crashing.

        The golden set looks for specific laws (CPEUM, NOMs, treaties, etc.)
        that may not exist in the test DB, but the command should handle
        missing laws gracefully via its 'not found, skipping' logic.
        """
        try:
            call_command("spot_check", "--golden-set")
        except SystemExit:
            pass

    def test_summary_counts(self):
        """Summary counts (passed + failed + warnings + skipped) equal total checks."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = tmp.name

        try:
            try:
                call_command("spot_check", "--limit", "1", "--output", output_path)
            except SystemExit:
                pass

            with open(output_path, encoding="utf-8") as f:
                report = json.load(f)

            summary = report["summary"]
            total_from_summary = (
                summary["passed"]
                + summary["failed"]
                + summary["warnings"]
                + summary["skipped"]
            )
            total_checks = len(report["checks"])

            assert total_from_summary == total_checks, (
                f"Summary counts ({total_from_summary}) do not match "
                f"total checks ({total_checks}). Summary: {summary}"
            )
        finally:
            os.unlink(output_path)
