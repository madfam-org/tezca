"""dataops.sync_law_status promotes pre-#218 ``unknown`` statuses (#222)."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db

REGISTRY = [
    {"id": "lfpdppp", "name": "LFPDPPP", "status": "discovered"},
    {"id": "old_law", "name": "Ley abrogada", "status": "abrogated"},
    {"id": "curated", "name": "Ley curada", "status": "discovered"},
    {"id": "not_ingested", "name": "Sin versión", "status": "active"},
]


class _FakeRegistry:
    def all(self):
        return [dict(e) for e in REGISTRY]

    def get_by_id(self, law_id):
        return next((dict(e) for e in REGISTRY if e["id"] == law_id), None)


@pytest.fixture
def laws():
    from apps.api.models import Law

    Law.objects.create(official_id="lfpdppp", name="LFPDPPP", status="unknown")
    Law.objects.create(official_id="old_law", name="Ley abrogada", status="unknown")
    Law.objects.create(official_id="curated", name="Ley curada", status="derogada")
    return Law


@pytest.fixture(autouse=True)
def _registry():
    with patch("apps.scraper.utils.law_registry.LawRegistry", _FakeRegistry), patch(
        "apps.scraper.dataops.models.AcquisitionLog"
    ):
        yield


def _run(**kwargs):
    from apps.scraper.scheduling import tasks

    return tasks.sync_law_status(**kwargs)


def test_single_law_promoted_from_registry(laws):
    result = _run(law_id="lfpdppp")
    assert result["status"] == "completed"
    assert result["updated"] == [{"law_id": "lfpdppp", "to": "vigente"}]
    assert laws.objects.get(official_id="lfpdppp").status == "vigente"


def test_dry_run_reports_without_writing(laws):
    result = _run(law_id="lfpdppp", dry_run="true")
    assert result["dry_run"] is True
    assert result["updated"] == [{"law_id": "lfpdppp", "to": "vigente"}]
    assert laws.objects.get(official_id="lfpdppp").status == "unknown"


def test_string_false_is_not_a_dry_run(laws):
    assert _run(law_id="lfpdppp", dry_run="false")["dry_run"] is False
    assert laws.objects.get(official_id="lfpdppp").status == "vigente"


def test_sweep_never_overwrites_curated_status(laws):
    result = _run()
    assert sorted(u["law_id"] for u in result["updated"]) == ["lfpdppp", "old_law"]
    assert laws.objects.get(official_id="old_law").status == "abrogada"
    assert laws.objects.get(official_id="curated").status == "derogada"
    assert result["missing"] == ["not_ingested"]


def test_unknown_registry_id_is_an_error(laws):
    assert _run(law_id="nope")["status"] == "error"
