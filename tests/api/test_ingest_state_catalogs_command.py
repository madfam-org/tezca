"""Tests for the ingest_state_catalogs management command
(apps/api/management/commands/ingest_state_catalogs.py).

Covers the bridge from the bare state-congress scraper catalog
(name/url/state/tier/category/law_type, no law text) into Law rows.
"""

import json

import pytest
from django.core.management import call_command

from apps.api.management.commands.ingest_state_catalogs import build_official_id
from apps.api.models import Law, LawVersion


def _catalog_entry(
    name="LEY ORGÁNICA DEL PODER LEGISLATIVO DEL ESTADO DE GUERRERO",
    url="https://congresoguerrero.gob.mx/leyes/ley-organica",
    state="Guerrero",
    tier="state",
    category="Ley Organica",
    law_type="ley_organica",
):
    return {
        "name": name,
        "url": url,
        "state": state,
        "tier": tier,
        "category": category,
        "law_type": law_type,
    }


def _write_catalog(state_dir, entries):
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "catalog.json").write_text(
        json.dumps(entries, ensure_ascii=False), encoding="utf-8"
    )


@pytest.mark.django_db
class TestIngestStateCatalogsCommand:
    def test_dry_run_no_writes(self, tmp_path):
        state_dir = tmp_path / "guerrero"
        _write_catalog(
            state_dir,
            [_catalog_entry(), _catalog_entry(name="LEY DOS", url="https://x/2")],
        )

        before = Law.objects.count()

        call_command(
            "ingest_state_catalogs",
            "--state",
            "guerrero",
            "--dry-run",
            state_laws_root=str(tmp_path),
        )

        assert Law.objects.count() == before

    def test_ingests_state_catalog(self, tmp_path):
        state_dir = tmp_path / "guerrero"
        _write_catalog(state_dir, [_catalog_entry()])

        call_command(
            "ingest_state_catalogs",
            "--state",
            "guerrero",
            state_laws_root=str(tmp_path),
        )

        official_id = build_official_id("guerrero", _catalog_entry())
        law = Law.objects.get(official_id=official_id)
        assert law.name == "LEY ORGÁNICA DEL PODER LEGISLATIVO DEL ESTADO DE GUERRERO"
        assert law.tier == "state"
        assert law.state == "Guerrero"
        assert law.category == "Ley Organica"
        assert law.law_type == Law.LawType.LEGISLATIVE
        assert law.source_url == "https://congresoguerrero.gob.mx/leyes/ley-organica"
        # No law text available from the scraper yet — no LawVersion created.
        assert LawVersion.objects.filter(law=law).count() == 0

    def test_dedup_upserts_on_rerun(self, tmp_path):
        state_dir = tmp_path / "guerrero"
        entry = _catalog_entry()
        _write_catalog(state_dir, [entry])

        call_command(
            "ingest_state_catalogs",
            "--state",
            "guerrero",
            state_laws_root=str(tmp_path),
        )
        call_command(
            "ingest_state_catalogs",
            "--state",
            "guerrero",
            state_laws_root=str(tmp_path),
        )

        official_id = build_official_id("guerrero", entry)
        assert Law.objects.filter(official_id=official_id).count() == 1

    def test_all_flag_ingests_every_state_dir(self, tmp_path):
        _write_catalog(tmp_path / "guerrero", [_catalog_entry()])
        _write_catalog(
            tmp_path / "hidalgo",
            [
                _catalog_entry(
                    name="CÓDIGO CIVIL DE HIDALGO",
                    url="https://x/hidalgo",
                    state="Hidalgo",
                )
            ],
        )

        call_command("ingest_state_catalogs", "--all", state_laws_root=str(tmp_path))

        assert Law.objects.filter(state="Guerrero").exists()
        assert Law.objects.filter(state="Hidalgo").exists()

    def test_missing_state_dir_no_op(self, tmp_path, capsys):
        call_command(
            "ingest_state_catalogs", "--state", "oaxaca", state_laws_root=str(tmp_path)
        )
        captured = capsys.readouterr()

        assert "No catalog.json files found" in captured.out

    def test_empty_catalog_skipped(self, tmp_path, capsys):
        state_dir = tmp_path / "guerrero"
        _write_catalog(state_dir, [])

        call_command(
            "ingest_state_catalogs",
            "--state",
            "guerrero",
            state_laws_root=str(tmp_path),
        )
        captured = capsys.readouterr()

        assert "empty, skipping" in captured.out
        assert not Law.objects.exists()

    def test_missing_name_falls_back_to_url_slug(self, tmp_path):
        state_dir = tmp_path / "guerrero"
        entry = _catalog_entry(
            name="", url="https://congresoguerrero.gob.mx/doc/123.pdf"
        )
        _write_catalog(state_dir, [entry])

        call_command(
            "ingest_state_catalogs",
            "--state",
            "guerrero",
            state_laws_root=str(tmp_path),
        )

        official_id = build_official_id("guerrero", entry)
        assert Law.objects.filter(official_id=official_id).exists()


class TestBuildOfficialId:
    def test_slugifies_name_with_state_prefix(self):
        oid = build_official_id("guerrero", {"name": "Ley Orgánica del Estado"})
        assert oid == "state_guerrero_ley_organica_del_estado"

    def test_falls_back_to_url_when_name_missing(self):
        oid = build_official_id(
            "hidalgo", {"name": "", "url": "https://x/ley-de-aguas"}
        )
        assert oid.startswith("state_hidalgo_")
        assert "ley" in oid
