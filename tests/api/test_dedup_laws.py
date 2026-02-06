"""Tests for the dedup_laws management command."""

import uuid

import pytest
from django.core.management import call_command

from apps.api.models import Law, LawVersion


@pytest.mark.django_db
class TestDedupLaws:
    """Test suite for the dedup_laws management command."""

    def _make_law(self, official_id=None, tier="federal", state=None):
        """Helper to create a law with a unique official_id."""
        if official_id is None:
            official_id = f"law_{uuid.uuid4().hex[:8]}"
        law = Law.objects.create(
            official_id=official_id,
            name=f"Test Law {official_id}",
            tier=tier,
            state=state,
        )
        LawVersion.objects.create(
            law=law,
            publication_date="2025-01-01",
        )
        return law

    def test_no_action_specified(self, capsys):
        """Command should error when no action flags are provided."""
        call_command("dedup_laws")
        captured = capsys.readouterr()
        assert "No action specified" in captured.err

    def test_dry_run_state_dupes(self, capsys):
        """--dry-run should report duplicates without deleting."""
        # Create canonical state law (with state field)
        self._make_law(tier="state", state="Jalisco")
        # Create duplicate state law (state=NULL)
        dupe = self._make_law(tier="state", state=None)

        before_count = Law.objects.count()

        call_command("dedup_laws", "--fix-state-dupes", "--dry-run")
        captured = capsys.readouterr()

        assert "DRY RUN" in captured.out
        assert "Would delete" in captured.out
        # Nothing actually deleted
        assert Law.objects.count() == before_count

    def test_fix_state_dupes(self, capsys):
        """--fix-state-dupes should delete state laws with state=NULL."""
        # Create canonical state laws (with state field)
        canonical = self._make_law(tier="state", state="Colima")
        # Create duplicate state laws (state=NULL)
        dupe1 = self._make_law(tier="state", state=None)
        dupe2 = self._make_law(tier="state", state=None)

        assert Law.objects.filter(tier="state", state__isnull=True).count() == 2

        call_command("dedup_laws", "--fix-state-dupes")
        captured = capsys.readouterr()

        # Duplicates should be gone
        assert Law.objects.filter(tier="state", state__isnull=True).count() == 0
        # Canonical law should remain
        assert Law.objects.filter(pk=canonical.pk).exists()
        assert "Deleted" in captured.out

    def test_fix_federal_tiers(self, capsys):
        """--fix-federal-tiers should delete laws with non-standard tier values."""
        # Create canonical federal law
        canonical = self._make_law(tier="federal")
        # Create duplicates with subject-matter tiers
        dupe_fiscal = self._make_law(tier="fiscal")
        dupe_labor = self._make_law(tier="labor")
        # Create standard-tier laws that should NOT be deleted
        state_law = self._make_law(tier="state", state="Jalisco")

        call_command("dedup_laws", "--fix-federal-tiers")
        captured = capsys.readouterr()

        # Non-standard tiers deleted
        assert not Law.objects.filter(pk=dupe_fiscal.pk).exists()
        assert not Law.objects.filter(pk=dupe_labor.pk).exists()
        # Standard tiers preserved
        assert Law.objects.filter(pk=canonical.pk).exists()
        assert Law.objects.filter(pk=state_law.pk).exists()
        assert "Deleted" in captured.out

    def test_all_flag(self, capsys):
        """--all should run both fix steps."""
        self._make_law(tier="state", state=None)
        self._make_law(tier="fiscal")

        call_command("dedup_laws", "--all")
        captured = capsys.readouterr()

        assert "Step 1" in captured.out
        assert "Step 2" in captured.out

    def test_idempotency(self, capsys):
        """Running dedup twice should be safe — second run finds nothing."""
        self._make_law(tier="state", state=None)
        self._make_law(tier="fiscal")

        call_command("dedup_laws", "--all")
        # Run again
        call_command("dedup_laws", "--all")
        captured = capsys.readouterr()

        assert (
            "Nothing to clean up" in captured.out or "No invalid-tier" in captured.out
        )

    def test_cascades_versions(self):
        """Deleting a law should also delete its LawVersions."""
        dupe = self._make_law(tier="state", state=None)
        version_pk = dupe.versions.first().pk

        call_command("dedup_laws", "--fix-state-dupes")

        assert not LawVersion.objects.filter(pk=version_pk).exists()
