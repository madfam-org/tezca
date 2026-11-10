"""ingest_rmf_rules: pinned sources, hash check, dated versions, AKN on disk.

PDF reading is replaced by the committed fixture lines (the same excerpt the
parser tests use), so the command runs without the 10 MB official PDFs; the
"PDFs" here are small placeholder files whose SHA-256 the test manifest pins.
"""

import hashlib
import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.api.models import Law, LawVersion
from apps.parsers.rmf.lines import load_jsonl
from tests.parsers.test_rmf_segmenter import FIXTURE

OFFICIAL_ID = "rmf_2026"


def _manifest(tmp_path, versions):
    manifest = {
        "official_id": OFFICIAL_ID,
        "name": "Resolución Miscelánea Fiscal para 2026",
        "short_name": "RMF 2026",
        "work_date": "2025-12-28",
        "versions": versions,
        "pending": [
            {
                "instrument": "Cuarta RMRMF 2026",
                "dof_date": "2026-10-30",
                "reason": "no compiled edition",
            }
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _source(tmp_path, name, payload):
    src = tmp_path / "sources"
    src.mkdir(exist_ok=True)
    (src / name).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _version(key, filename, sha, publication, valid_from, valid_to):
    return {
        "key": key,
        "publication_date": publication,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "document_url": f"https://www.sat.gob.mx/{filename}",
        "filename": filename,
        "sha256": sha,
        "dof_url": "https://dof.gob.mx/nota_detalle.php?codigo=5777217&fecha=28/12/2025",
        "change_summary": f"version {key}",
    }


@pytest.fixture
def fixture_lines(monkeypatch):
    lines = load_jsonl(FIXTURE)
    monkeypatch.setattr(
        "apps.api.management.commands.ingest_rmf_rules.extract_lines",
        lambda _path: lines,
    )
    return lines


@pytest.fixture
def two_versions(tmp_path):
    sha_a = _source(tmp_path, "base.pdf", b"base")
    sha_b = _source(tmp_path, "compilada.pdf", b"compilada")
    return _manifest(
        tmp_path,
        [
            _version(
                "dof", "base.pdf", sha_a, "2025-12-28", "2026-01-01", "2026-07-10"
            ),
            _version(
                "compilada",
                "compilada.pdf",
                sha_b,
                "2026-10-02",
                "2026-10-02",
                "2026-10-30",
            ),
        ],
    )


def _run(tmp_path, manifest, *extra):
    call_command(
        "ingest_rmf_rules",
        "--manifest",
        str(manifest),
        "--source-dir",
        str(tmp_path / "sources"),
        "--output-dir",
        str(tmp_path / "out"),
        *extra,
    )


@pytest.mark.django_db
class TestIngestRmfRules:
    def test_refuses_without_the_legal_data_guard(
        self, tmp_path, two_versions, monkeypatch
    ):
        monkeypatch.delenv("LOCAL_LEGAL_DATA_OPS", raising=False)
        with pytest.raises(CommandError, match="LOCAL_LEGAL_DATA_OPS"):
            _run(tmp_path, two_versions)
        assert not Law.objects.filter(official_id=OFFICIAL_ID).exists()

    def test_dry_run_needs_no_guard_and_writes_nothing(
        self, tmp_path, two_versions, fixture_lines, monkeypatch
    ):
        monkeypatch.delenv("LOCAL_LEGAL_DATA_OPS", raising=False)
        _run(tmp_path, two_versions, "--dry-run")
        assert not Law.objects.filter(official_id=OFFICIAL_ID).exists()
        assert not (tmp_path / "out").exists()

    def test_registers_each_version_with_its_dates_and_akn(
        self, tmp_path, two_versions, fixture_lines, monkeypatch
    ):
        monkeypatch.setenv("LOCAL_LEGAL_DATA_OPS", "yes")
        _run(tmp_path, two_versions)

        law = Law.objects.get(official_id=OFFICIAL_ID)
        assert law.law_type == Law.LawType.NON_LEGISLATIVE
        assert law.category == "resolución_miscelánea_fiscal"
        assert law.domains == ["fiscal"]

        versions = list(LawVersion.objects.filter(law=law).order_by("publication_date"))
        assert [str(v.publication_date) for v in versions] == [
            "2025-12-28",
            "2026-10-02",
        ]
        assert [str(v.valid_from) for v in versions] == ["2026-01-01", "2026-10-02"]
        assert [str(v.valid_to) for v in versions] == ["2026-07-10", "2026-10-30"]
        assert versions[1].change_summary == "version compilada"

        # index_laws reads the NEWEST version's AKN; it must hold rule articles.
        newest = law.versions.first()
        xml = (tmp_path / "out" / "rmf_2026-compilada.xml").read_text(encoding="utf-8")
        assert newest.xml_file_path.endswith("rmf_2026-compilada.xml")
        assert '<article eId="regla-3-13-7"' in xml
        assert "<num>3.13.7.</num>" in xml

    def test_rerun_is_idempotent(
        self, tmp_path, two_versions, fixture_lines, monkeypatch
    ):
        monkeypatch.setenv("LOCAL_LEGAL_DATA_OPS", "yes")
        _run(tmp_path, two_versions)
        _run(tmp_path, two_versions)
        assert LawVersion.objects.filter(law__official_id=OFFICIAL_ID).count() == 2

    def test_hash_mismatch_aborts_before_any_write(
        self, tmp_path, fixture_lines, monkeypatch
    ):
        monkeypatch.setenv("LOCAL_LEGAL_DATA_OPS", "yes")
        _source(tmp_path, "base.pdf", b"re-uploaded by SAT")
        manifest = _manifest(
            tmp_path,
            [_version("dof", "base.pdf", "0" * 64, "2025-12-28", "2026-01-01", None)],
        )
        with pytest.raises(CommandError, match="failed"):
            _run(tmp_path, manifest)
        assert not Law.objects.filter(official_id=OFFICIAL_ID).exists()

    def test_missing_source_without_download_is_an_error(
        self, tmp_path, fixture_lines, monkeypatch
    ):
        monkeypatch.setenv("LOCAL_LEGAL_DATA_OPS", "yes")
        (tmp_path / "sources").mkdir()
        manifest = _manifest(
            tmp_path,
            [_version("dof", "absent.pdf", "0" * 64, "2025-12-28", "2026-01-01", None)],
        )
        with pytest.raises(CommandError):
            _run(tmp_path, manifest)

    def test_leaves_catalog_placeholder_versions_alone(
        self, tmp_path, two_versions, fixture_lines, monkeypatch
    ):
        monkeypatch.setenv("LOCAL_LEGAL_DATA_OPS", "yes")
        law = Law.objects.create(official_id=OFFICIAL_ID, name="RMF 2026")
        LawVersion.objects.create(law=law, publication_date="2026-01-01")
        _run(tmp_path, two_versions)
        assert LawVersion.objects.filter(law=law).count() == 3
        assert (
            LawVersion.objects.get(law=law, publication_date="2026-01-01").xml_file_path
            is None
        )

    def test_uploads_akn_to_r2_under_the_key_the_reader_uses(
        self, tmp_path, two_versions, fixture_lines, monkeypatch
    ):
        """Pods have no volume under data/: the AKN must reach R2 under the key
        read_data_content derives from xml_file_path ("data/" stripped)."""
        from unittest.mock import MagicMock

        monkeypatch.setenv("LOCAL_LEGAL_DATA_OPS", "yes")
        monkeypatch.setenv("STORAGE_BACKEND", "r2")
        storage = MagicMock()
        monkeypatch.setattr("apps.api.storage.get_storage_backend", lambda: storage)
        monkeypatch.chdir(tmp_path)
        call_command(
            "ingest_rmf_rules",
            "--manifest",
            str(two_versions),
            "--source-dir",
            str(tmp_path / "sources"),
            "--output-dir",
            "data/rmf",
        )
        keys = [c.args[0] for c in storage.put_file.call_args_list]
        assert keys == ["rmf/rmf_2026-dof.xml", "rmf/rmf_2026-compilada.xml"]
        newest = Law.objects.get(official_id=OFFICIAL_ID).versions.first()
        assert newest.xml_file_path == "data/rmf/rmf_2026-compilada.xml"

    def test_r2_needs_a_relative_output_dir_and_writes_no_rows(
        self, tmp_path, two_versions, fixture_lines, monkeypatch
    ):
        monkeypatch.setenv("LOCAL_LEGAL_DATA_OPS", "yes")
        monkeypatch.setenv("STORAGE_BACKEND", "r2")
        with pytest.raises(CommandError, match="relative"):
            _run(tmp_path, two_versions)
        assert not Law.objects.filter(official_id=OFFICIAL_ID).exists()


def test_shipped_manifest_pins_every_document():
    """The committed manifest names a URL, a DOF date and a SHA-256 for every
    text it ingests and every instrument it cites, and its validity ranges
    chain without gaps (half-open intervals)."""
    from pathlib import Path

    from apps.api.management.commands.ingest_rmf_rules import (
        DEFAULT_MANIFEST,
        load_manifest,
    )

    root = Path(__file__).resolve().parents[2]
    manifest = load_manifest(root / DEFAULT_MANIFEST)
    assert manifest["official_id"] == OFFICIAL_ID
    versions = manifest["versions"]
    assert versions[0]["publication_date"] == "2025-12-28"
    assert versions[0]["valid_from"] == "2026-01-01"
    for earlier, later in zip(versions, versions[1:]):
        assert earlier["valid_to"] == later["valid_from"]
        assert earlier["publication_date"] < later["publication_date"]
    for entry in versions + manifest["instruments"] + manifest["pending"]:
        assert len(entry["sha256"]) == 64
        url = entry.get("document_url") or ""
        assert url.startswith(("https://www.sat.gob.mx/", "https://dof.gob.mx/"))
    assert all(
        e["dof_url"].startswith("https://dof.gob.mx/") for e in manifest["instruments"]
    )
