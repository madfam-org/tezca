"""Tests for Django signals in apps.api.signals — webhook dispatch on model save.

Covers:
  - law_changed signal on Law create/update
  - version_created signal on LawVersion create
  - version update does NOT fire version.created
  - Signal error handling does not crash model save
  - Payload structure verification
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from apps.api.models import Law, LawVersion

# The signal handlers use lazy import: `from .webhooks import dispatch_webhook_event`
# So we must patch at the module where it's defined, not where it's imported.
DISPATCH_PATCH = "apps.api.webhooks.dispatch_webhook_event"


@pytest.mark.django_db
class TestLawChangedSignal:
    """Tests for the law_changed signal handler."""

    @patch(DISPATCH_PATCH)
    def test_law_create_dispatches_created_event(self, mock_dispatch):
        """Creating a Law fires law.created event."""
        law = Law.objects.create(
            official_id="sig_create_test",
            name="Signal Create Test",
            tier="federal",
            category="fiscal",
        )

        mock_dispatch.assert_called()
        # Find the law.created call
        calls = [c for c in mock_dispatch.call_args_list if c[0][0] == "law.created"]
        assert len(calls) == 1
        payload = calls[0][0][1]
        assert payload["law_id"] == "sig_create_test"
        assert payload["law_name"] == "Signal Create Test"
        assert payload["category"] == "fiscal"
        assert payload["tier"] == "federal"

    @patch(DISPATCH_PATCH)
    def test_law_update_dispatches_updated_event(self, mock_dispatch):
        """Updating a Law fires law.updated event."""
        law = Law.objects.create(
            official_id="sig_update_test",
            name="Signal Update Test",
            tier="federal",
            category="fiscal",
        )
        mock_dispatch.reset_mock()

        law.name = "Signal Update Test Modified"
        law.save()

        calls = [c for c in mock_dispatch.call_args_list if c[0][0] == "law.updated"]
        assert len(calls) == 1
        payload = calls[0][0][1]
        assert payload["law_id"] == "sig_update_test"
        assert payload["law_name"] == "Signal Update Test Modified"

    @patch(DISPATCH_PATCH)
    def test_law_created_with_empty_category(self, mock_dispatch):
        """Category defaults to empty string in payload when None."""
        Law.objects.create(
            official_id="sig_no_cat",
            name="No Category",
            tier="federal",
            category=None,
        )

        calls = [c for c in mock_dispatch.call_args_list if c[0][0] == "law.created"]
        assert len(calls) == 1
        payload = calls[0][0][1]
        assert payload["category"] == ""

    @patch(DISPATCH_PATCH)
    def test_law_created_with_empty_tier(self, mock_dispatch):
        """Tier defaults to empty string in payload when None."""
        Law.objects.create(
            official_id="sig_no_tier",
            name="No Tier",
            tier=None,
            category="ley",
        )

        calls = [c for c in mock_dispatch.call_args_list if c[0][0] == "law.created"]
        assert len(calls) == 1
        payload = calls[0][0][1]
        assert payload["tier"] == ""


@pytest.mark.django_db
class TestVersionCreatedSignal:
    """Tests for the version_created signal handler."""

    @patch(DISPATCH_PATCH)
    def test_version_create_dispatches_event(self, mock_dispatch):
        """Creating a LawVersion fires version.created event."""
        law = Law.objects.create(
            official_id="sig_ver_create",
            name="Version Signal Law",
            tier="federal",
            category="fiscal",
        )
        mock_dispatch.reset_mock()

        LawVersion.objects.create(
            law=law,
            publication_date=date(2026, 3, 1),
        )

        calls = [
            c for c in mock_dispatch.call_args_list if c[0][0] == "version.created"
        ]
        assert len(calls) == 1
        payload = calls[0][0][1]
        assert payload["law_id"] == "sig_ver_create"
        assert payload["law_name"] == "Version Signal Law"
        assert payload["category"] == "fiscal"
        assert payload["publication_date"] == "2026-03-01"

    @patch(DISPATCH_PATCH)
    def test_version_update_does_not_dispatch(self, mock_dispatch):
        """Updating an existing LawVersion does NOT fire version.created."""
        law = Law.objects.create(
            official_id="sig_ver_update",
            name="No Version Event",
            tier="federal",
        )
        ver = LawVersion.objects.create(
            law=law,
            publication_date=date(2026, 1, 1),
        )
        mock_dispatch.reset_mock()

        ver.publication_date = date(2026, 2, 1)
        ver.save()

        # Should have no version.created calls
        version_calls = [
            c for c in mock_dispatch.call_args_list if c[0][0] == "version.created"
        ]
        assert len(version_calls) == 0


@pytest.mark.django_db
class TestSignalErrorResilience:
    """Tests that signal errors propagate correctly (Django default behavior)."""

    @patch(DISPATCH_PATCH, side_effect=Exception("Webhook dispatch failed"))
    def test_dispatch_error_propagates(self, mock_dispatch):
        """If dispatch_webhook_event raises, Django propagates the error.

        Django signals do NOT swallow exceptions by default. This test
        documents that behavior — the law creation will fail if the
        signal handler raises.
        """
        with pytest.raises(Exception, match="Webhook dispatch failed"):
            Law.objects.create(
                official_id="sig_error_test",
                name="Error Test Law",
                tier="federal",
            )

    @patch(DISPATCH_PATCH)
    def test_dispatch_called_once_per_create(self, mock_dispatch):
        """Each create() triggers exactly one dispatch call."""
        Law.objects.create(
            official_id="sig_once_test",
            name="Once Test",
            tier="federal",
            category="ley",
        )
        # create triggers one call
        assert mock_dispatch.call_count == 1

    @patch(DISPATCH_PATCH)
    def test_dispatch_called_once_per_update(self, mock_dispatch):
        """Each save() on existing law triggers exactly one dispatch call."""
        law = Law.objects.create(
            official_id="sig_upd_once",
            name="Update Once Test",
            tier="federal",
            category="ley",
        )
        mock_dispatch.reset_mock()

        law.name = "Updated Name"
        law.save()
        assert mock_dispatch.call_count == 1
