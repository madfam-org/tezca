"""Tests for ``apps.scraper.utils.law_registry``.

LawRegistry is a thin wrapper around a JSON file. These tests use a
fixture-based registry written into ``tmp_path`` so we don't depend on
the real ``data/law_registry.json`` shape and contents.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.scraper.utils.law_registry import LawRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry_file(tmp_path: Path) -> Path:
    """Write a synthetic registry to tmp and return its path."""
    payload = {
        "federal_laws": [
            {
                "id": "amparo",
                "name": "Ley de Amparo",
                "short_name": "Amparo",
                "type": "ley",
                "slug": "amparo",
                "expected_articles": 300,
                "publication_date": "2013-04-02",
                "url": "https://example.com/amparo.pdf",
                "priority": 1,
                "tier": "constitutional",
                "status": "active",
                "category": "ley",
            },
            {
                "id": "iva",
                "name": "Ley del IVA",
                "short_name": "IVA",
                "type": "ley",
                "slug": "iva",
                "expected_articles": 50,
                "publication_date": "1978-12-29",
                "url": "https://example.com/iva.pdf",
                "priority": 1,
                "tier": "fiscal",
                "status": "active",
                "category": "ley",
            },
            {
                "id": "deprecated_law",
                "name": "Ley Vieja",
                "short_name": "Vieja",
                "type": "ley",
                "slug": "vieja",
                "expected_articles": 0,
                "publication_date": "1990-01-01",
                "url": "https://example.com/vieja.pdf",
                "priority": 2,
                "tier": "labor",
                "status": "deprecated",
                "category": "ley",
            },
        ]
    }
    path = tmp_path / "law_registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# __init__ + _load_registry
# ---------------------------------------------------------------------------


def test_init_loads_registry_file(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    assert registry.count() == 3
    assert registry.registry_path == registry_file


def test_init_raises_when_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        LawRegistry(registry_path=tmp_path / "nope.json")


def test_init_skips_reglamentos_when_disabled(registry_file):
    registry = LawRegistry(registry_path=registry_file, include_reglamentos=False)
    assert registry.count() == 3


def test_init_includes_reglamentos_when_present(registry_file, tmp_path):
    """When include_reglamentos=True and a sibling JSON exists, entries merge."""
    reglamentos = [
        {
            "id": "reg_amparo",
            "name": "Reglamento de la Ley de Amparo",
            "url": "https://example.com/reg_amparo.pdf",
        }
    ]
    (registry_file.parent / "discovered_reglamentos.json").write_text(
        json.dumps(reglamentos), encoding="utf-8"
    )

    registry = LawRegistry(registry_path=registry_file, include_reglamentos=True)
    assert registry.count() == 4
    # The reglamento gets normalised to the standard schema
    reg = registry.get_by_id("reg_amparo")
    assert reg is not None
    assert reg["category"] == "reglamento"
    assert reg["tier"] == "federal"
    assert reg["priority"] == 2


def test_include_reglamentos_with_no_sibling_file(registry_file):
    """When include_reglamentos=True but no sibling file, base set is used."""
    registry = LawRegistry(registry_path=registry_file, include_reglamentos=True)
    assert registry.count() == 3


# ---------------------------------------------------------------------------
# all() — returns a copy
# ---------------------------------------------------------------------------


def test_all_returns_a_copy(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    laws = registry.all()
    laws.append({"id": "injected"})
    # Mutating the returned list must not affect the registry
    assert registry.count() == 3


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


def test_get_by_id_returns_match(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    law = registry.get_by_id("amparo")
    assert law is not None
    assert law["name"] == "Ley de Amparo"


def test_get_by_id_returns_none_for_missing(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    assert registry.get_by_id("does_not_exist") is None


def test_get_by_id_returns_a_copy(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    law = registry.get_by_id("amparo")
    law["mutated"] = True
    # Re-fetch — mutation must not have leaked
    fresh = registry.get_by_id("amparo")
    assert "mutated" not in fresh


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_filter_by_priority_returns_matching(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    p1 = registry.filter_by_priority(1)
    assert len(p1) == 2
    assert all(law["priority"] == 1 for law in p1)


def test_filter_by_priority_empty_when_no_match(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    assert registry.filter_by_priority(99) == []


def test_filter_by_tier(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    fiscal = registry.filter_by_tier("fiscal")
    assert len(fiscal) == 1
    assert fiscal[0]["id"] == "iva"


def test_filter_by_category(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    leyes = registry.filter_by_category("ley")
    assert len(leyes) == 3


def test_filter_by_status_default_is_active(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    active = registry.filter_by_status()  # defaults to "active"
    assert len(active) == 2
    assert all(law["status"] == "active" for law in active)


def test_filter_by_status_explicit(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    deprecated = registry.filter_by_status("deprecated")
    assert len(deprecated) == 1


# ---------------------------------------------------------------------------
# get_ids / count
# ---------------------------------------------------------------------------


def test_get_ids_returns_all_ids(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    ids = registry.get_ids()
    assert set(ids) == {"amparo", "iva", "deprecated_law"}


def test_count_matches_data(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    assert registry.count() == 3


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------


def test_summary_aggregates_correctly(registry_file):
    registry = LawRegistry(registry_path=registry_file)
    summary = registry.summary()
    assert summary["total_laws"] == 3
    assert summary["by_priority"][1] == 2
    assert summary["by_priority"][2] == 1
    assert summary["by_tier"]["constitutional"] == 1
    assert summary["by_tier"]["fiscal"] == 1
    assert summary["by_tier"]["labor"] == 1
    assert summary["by_status"]["active"] == 2
    assert summary["by_status"]["deprecated"] == 1


def test_count_by_field_handles_missing_value(registry_file, tmp_path):
    """Laws without the requested field are bucketed under 'unknown'."""
    payload = {
        "federal_laws": [
            {"id": "a", "name": "A"},  # no tier/status/priority
            {"id": "b", "name": "B", "tier": "fiscal"},
        ]
    }
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    registry = LawRegistry(registry_path=path)
    summary = registry.summary()
    assert summary["by_tier"]["unknown"] == 1
    assert summary["by_tier"]["fiscal"] == 1


# ---------------------------------------------------------------------------
# Real-registry contract: RLFPDPPP reglamento must be ingest-ready (Defect 4)
# ---------------------------------------------------------------------------


def _real_registry_path() -> Path:
    # tests/scraper/test_law_registry.py → repo root → data/law_registry.json
    return Path(__file__).resolve().parents[2] / "data" / "law_registry.json"


def test_real_registry_is_valid_json():
    """The shipped registry must always be parseable — a broken registry
    breaks the entire ingest pipeline."""
    data = json.loads(_real_registry_path().read_text(encoding="utf-8"))
    assert isinstance(data.get("federal_laws"), list)
    assert len(data["federal_laws"]) > 0


def test_reg_lfpdppp_entry_is_ingest_ready():
    """Reglamento de la LFPDPPP must be present in law_registry.json with a
    real publication_date so db_saver creates a LawVersion (and therefore the
    downstream parser/indexer can populate Art. 51 and the rest). Without a
    non-empty, non-placeholder publication_date, db_saver skips version
    creation and the reglamento stays a 0-article stub."""
    registry = LawRegistry(registry_path=_real_registry_path())
    entry = registry.get_by_id("reg_reg_lfpdppp")

    assert entry is not None, "reg_reg_lfpdppp missing from law_registry.json"

    pub_date = entry.get("publication_date")
    assert pub_date, "publication_date must be set for a LawVersion to be created"
    assert pub_date != "1900-01-01", "placeholder date is rejected by db_saver"

    # Points at the official Cámara de Diputados Reglamento PDF.
    assert entry.get("url", "").endswith("Reg_LFPDPPP.pdf")
    assert entry.get("slug")
