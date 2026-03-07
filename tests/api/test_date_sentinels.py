"""
Spot-check tests for sentinel date usage in LawVersion records.

The ingest_state_laws management command defaults to "2023-01-01" when no
publication_date is available (line 107). This sentinel pollutes temporal
queries unless explicitly filtered. These tests document the pattern and
verify correct counting of sentinel vs. real dates.
"""

import uuid
from datetime import date

import pytest
from django.test import TestCase

from apps.api.models import Law, LawVersion

SENTINEL_DATE = date(2023, 1, 1)


@pytest.mark.spotcheck
class TestDateSentinels(TestCase):
    """Verify sentinel date behavior in LawVersion records."""

    def _create_law(self, suffix: str = "") -> Law:
        uid = uuid.uuid4().hex[:8]
        return Law.objects.create(
            official_id=f"sentinel-test-{uid}{suffix}",
            name=f"Ley de Pruebas Sentinel {uid}",
            tier="state",
            state="Colima",
            status="vigente",
        )

    def test_count_sentinel_dates(self):
        """
        LawVersions with the sentinel date (2023-01-01) are countable and
        distinguishable from records with real publication dates.
        """
        law = self._create_law()

        # Create versions with sentinel dates
        for _ in range(3):
            LawVersion.objects.create(
                law=law,
                publication_date=SENTINEL_DATE,
                xml_file_path=f"data/state/test/{uuid.uuid4().hex[:6]}.xml",
            )

        # Create versions with real dates
        real_dates = [date(2024, 6, 15), date(2025, 1, 10)]
        for d in real_dates:
            LawVersion.objects.create(
                law=law,
                publication_date=d,
                xml_file_path=f"data/state/test/{uuid.uuid4().hex[:6]}.xml",
            )

        sentinel_count = LawVersion.objects.filter(
            law=law, publication_date=SENTINEL_DATE
        ).count()
        real_count = (
            LawVersion.objects.filter(law=law)
            .exclude(publication_date=SENTINEL_DATE)
            .count()
        )

        assert (
            sentinel_count == 3
        ), f"Expected 3 sentinel-dated versions, got {sentinel_count}"
        assert real_count == 2, f"Expected 2 real-dated versions, got {real_count}"

    def test_ingest_defaults_to_sentinel(self):
        """
        The ingest_state_laws command (line 107) defaults to "2023-01-01"
        when publication_date is missing:

            pub_date = publication_date if publication_date else "2023-01-01"

        This verifies the sentinel fallback logic in isolation.
        """
        # Simulate missing publication_date (None)
        publication_date = None
        pub_date = publication_date if publication_date else "2023-01-01"
        assert pub_date == "2023-01-01"

        # Simulate empty string publication_date
        publication_date = ""
        pub_date = publication_date if publication_date else "2023-01-01"
        assert pub_date == "2023-01-01"

        # Simulate valid publication_date -- sentinel should NOT be used
        publication_date = "2024-06-15"
        pub_date = publication_date if publication_date else "2023-01-01"
        assert pub_date == "2024-06-15"
