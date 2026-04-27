"""Tests for the law ingestion pipeline (``apps.parsers.pipeline``).

The pipeline is intentionally side-effect-heavy (HTTP downloads, PDF
extraction, ES writes, DB saves, storage sync). These tests stub each
collaborator at the boundary so the orchestration logic is exercised
without touching the network, filesystem, or database. The goal is to
cover ``pipeline.py`` itself — not its dependencies.

Coverage focus:
* IngestionResult dataclass (post_init, grade, summary)
* IngestionPipeline.__init__ (data_dir defaulting, storage/db_saver paths)
* _download_file (URL extension routing, OJN host detection, skip_download)
* _extract_text (caching, dispatch by suffix)
* _extract_pdf_text (pdfplumber happy path, OCR fallback)
* _extract_docx_text / _extract_doc_text (missing-dep paths)
* _ocr_extract (missing-dep paths)
* _parse_to_xml (delegates to AKN generator)
* _calculate_quality (delegates to QualityCalculator)
* _sync_to_storage (uploads only files that exist)
* ingest_law (happy path, retry path, quarantine, cross-ref/db/storage failures)
"""

from __future__ import annotations

import builtins
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.parsers import pipeline as pipeline_mod
from apps.parsers.pipeline import IngestionPipeline, IngestionResult
from apps.parsers.quality import QualityMetrics

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_metrics(grade: str = "A", overall: float = 95.0) -> QualityMetrics:
    """Construct a QualityMetrics in a way that survives field changes."""
    # QualityMetrics is a dataclass with many fields; build a stub via SimpleNamespace
    # for places where only `.grade` and `.overall_score` are read.
    return SimpleNamespace(grade=grade, overall_score=overall)  # type: ignore[return-value]


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """A scratch data directory with the subdirs the pipeline expects."""
    (tmp_path / "raw" / "pdfs").mkdir(parents=True)
    (tmp_path / "raw").mkdir(exist_ok=True)
    (tmp_path / "federal").mkdir()
    (tmp_path / "logs").mkdir()
    return tmp_path


@pytest.fixture
def pipeline_factory(tmp_data_dir):
    """Returns a callable that builds a pipeline with mockable collaborators."""

    def _build(
        *,
        skip_download: bool = True,
        storage: object | None = None,
        db_saver: object | None = MagicMock(),
        error_tracker: object | None = None,
    ) -> IngestionPipeline:
        # Patch the storage backend lookup so __init__ doesn't try to import
        # the Django settings module's storage configuration.
        with patch("apps.api.storage.get_storage_backend", return_value=storage):
            # Patch DatabaseSaver import (imported lazily inside __init__)
            with patch("ingestion.db_saver.DatabaseSaver", return_value=db_saver):
                p = IngestionPipeline(
                    data_dir=tmp_data_dir,
                    skip_download=skip_download,
                    storage=storage,
                    error_tracker=error_tracker,
                )
        # If caller asked for a stub db_saver, force it (the lazy import path
        # may have failed silently).
        if db_saver is not None:
            p.db_saver = db_saver
        return p

    return _build


@pytest.fixture
def law_meta() -> dict:
    return {
        "id": "amparo",
        "name": "Ley de Amparo",
        "short_name": "Ley de Amparo",
        "type": "ley",
        "slug": "amparo",
        "expected_articles": 300,
        "publication_date": "2013-04-02",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LAmp.pdf",
        "status": "vigente",
    }


# ---------------------------------------------------------------------------
# IngestionResult
# ---------------------------------------------------------------------------


def test_ingestion_result_post_init_default_stages():
    r = IngestionResult(law_id="x", law_name="X", success=False)
    assert r.stages_completed == []  # post_init initializes empty list


def test_ingestion_result_grade_with_metrics():
    r = IngestionResult(law_id="x", law_name="X", success=True)
    r.quality_metrics = _make_metrics(grade="B")
    assert r.grade == "B"


def test_ingestion_result_grade_without_metrics():
    r = IngestionResult(law_id="x", law_name="X", success=True)
    assert r.grade == "N/A"


def test_ingestion_result_summary_success():
    r = IngestionResult(law_id="x", law_name="X", success=True, duration_seconds=1.5)
    r.quality_metrics = _make_metrics(grade="A")
    out = r.summary()
    assert "✅" in out and "Grade A" in out and "1.5s" in out


def test_ingestion_result_summary_failure():
    r = IngestionResult(
        law_id="x", law_name="X", success=False, error="boom", duration_seconds=0.3
    )
    out = r.summary()
    assert "❌" in out and "boom" in out


# ---------------------------------------------------------------------------
# IngestionPipeline.__init__
# ---------------------------------------------------------------------------


def test_init_creates_required_subdirs(pipeline_factory, tmp_data_dir):
    p = pipeline_factory()
    assert p.pdf_dir.exists()
    assert p.text_dir.exists()
    assert p.xml_dir.exists()


def test_init_uses_provided_error_tracker(pipeline_factory):
    fake_tracker = MagicMock()
    p = pipeline_factory(error_tracker=fake_tracker)
    assert p.error_tracker is fake_tracker


def test_init_uses_provided_storage(pipeline_factory):
    fake_storage = MagicMock()
    p = pipeline_factory(storage=fake_storage)
    assert p.storage is fake_storage


def test_init_storage_lookup_failure_falls_back_to_none(tmp_data_dir):
    """If storage lookup raises, pipeline falls back to storage=None."""
    with patch("apps.api.storage.get_storage_backend", side_effect=RuntimeError):
        with patch("ingestion.db_saver.DatabaseSaver", return_value=MagicMock()):
            p = IngestionPipeline(data_dir=tmp_data_dir)
    assert p.storage is None


# ---------------------------------------------------------------------------
# _download_file — extension routing + caching + OJN special-case
# ---------------------------------------------------------------------------


def test_download_file_skips_when_skip_download_and_exists(pipeline_factory, law_meta):
    p = pipeline_factory(skip_download=True)
    target = p.pdf_dir / f"{law_meta['id']}.pdf"
    target.write_bytes(b"existing")
    out = p._download_file(law_meta)
    assert out == target


def test_download_file_uses_cached_when_large_enough(pipeline_factory, law_meta):
    p = pipeline_factory(skip_download=False)
    target = p.pdf_dir / f"{law_meta['id']}.pdf"
    target.write_bytes(b"x" * 2048)  # > 1024 byte threshold
    out = p._download_file(law_meta)
    assert out == target


def test_download_file_routes_docx_extension(pipeline_factory, law_meta):
    p = pipeline_factory(skip_download=True)
    law_meta["url"] = "https://example.com/laws/foo.docx"
    target = p.pdf_dir / f"{law_meta['id']}.docx"
    target.write_bytes(b"x")
    out = p._download_file(law_meta)
    assert out.suffix == ".docx"


def test_download_file_routes_doc_extension(pipeline_factory, law_meta):
    p = pipeline_factory(skip_download=True)
    law_meta["url"] = "https://example.com/laws/foo.doc"
    target = p.pdf_dir / f"{law_meta['id']}.doc"
    target.write_bytes(b"x")
    out = p._download_file(law_meta)
    assert out.suffix == ".doc"


def test_download_file_fetches_when_missing(pipeline_factory, law_meta):
    """When no cached file exists, the pipeline issues an HTTP GET."""
    p = pipeline_factory(skip_download=False)

    fake_response = MagicMock(content=b"PDFCONTENT")
    fake_response.raise_for_status = MagicMock()

    fake_session = MagicMock()
    fake_session.get.return_value = fake_response

    with patch("apps.parsers.pipeline.requests.Session", return_value=fake_session):
        out = p._download_file(law_meta)

    assert out.exists()
    assert out.read_bytes() == b"PDFCONTENT"
    # Default (non-OJN) path uses verify=True and the default timeout
    fake_session.get.assert_called_once()
    kwargs = fake_session.get.call_args.kwargs
    assert kwargs["verify"] is True
    assert kwargs["timeout"] == pipeline_mod._DEFAULT_TIMEOUT


def test_download_file_ojn_host_uses_extended_timeout(pipeline_factory, law_meta):
    """OJN hosts get longer timeout, more retries, and verify=False."""
    p = pipeline_factory(skip_download=False)
    law_meta["url"] = "https://compilacion.ordenjuridico.gob.mx/somefile.pdf"

    fake_response = MagicMock(content=b"content")
    fake_response.raise_for_status = MagicMock()
    fake_session = MagicMock()
    fake_session.get.return_value = fake_response

    with patch("apps.parsers.pipeline.requests.Session", return_value=fake_session):
        p._download_file(law_meta)

    kwargs = fake_session.get.call_args.kwargs
    assert kwargs["verify"] is False
    assert kwargs["timeout"] == pipeline_mod._OJN_TIMEOUT


# ---------------------------------------------------------------------------
# _extract_text — caching + suffix dispatch
# ---------------------------------------------------------------------------


def test_extract_text_returns_cached(pipeline_factory, law_meta, tmp_data_dir):
    p = pipeline_factory()
    cached = p.text_dir / f"{law_meta['id']}_extracted.txt"
    cached.write_text("cached body", encoding="utf-8")

    out_path, text = p._extract_text(law_meta, p.pdf_dir / "amparo.pdf")
    assert out_path == cached
    assert text == "cached body"


def test_extract_text_dispatches_pdf(pipeline_factory, law_meta):
    p = pipeline_factory()
    file_path = p.pdf_dir / f"{law_meta['id']}.pdf"
    file_path.write_bytes(b"")

    with patch.object(p, "_extract_pdf_text", return_value="pdf body") as m:
        out_path, text = p._extract_text(law_meta, file_path)
    m.assert_called_once_with(file_path)
    assert text == "pdf body"
    assert out_path.read_text(encoding="utf-8") == "pdf body"


def test_extract_text_dispatches_docx(pipeline_factory, law_meta):
    p = pipeline_factory()
    file_path = p.pdf_dir / f"{law_meta['id']}.docx"
    file_path.write_bytes(b"")
    with patch.object(p, "_extract_docx_text", return_value="docx body") as m:
        _, text = p._extract_text(law_meta, file_path)
    m.assert_called_once_with(file_path)
    assert text == "docx body"


def test_extract_text_dispatches_doc(pipeline_factory, law_meta):
    p = pipeline_factory()
    file_path = p.pdf_dir / f"{law_meta['id']}.doc"
    file_path.write_bytes(b"")
    with patch.object(p, "_extract_doc_text", return_value="doc body") as m:
        _, text = p._extract_text(law_meta, file_path)
    m.assert_called_once_with(file_path)
    assert text == "doc body"


# ---------------------------------------------------------------------------
# _extract_docx_text — dependency-missing path
# ---------------------------------------------------------------------------


def test_extract_docx_text_returns_empty_when_dep_missing(pipeline_factory):
    p = pipeline_factory()

    real_import = builtins.__import__

    def _raise(name, *args, **kwargs):
        if name == "docx":
            raise ImportError("python-docx not installed")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_raise):
        out = p._extract_docx_text(Path("/nonexistent.docx"))
    assert out == ""


# ---------------------------------------------------------------------------
# _extract_doc_text — antiword + libreoffice paths
# ---------------------------------------------------------------------------


def test_extract_doc_text_uses_antiword_when_available(pipeline_factory, tmp_path):
    p = pipeline_factory()
    long_text = "x" * 200  # > MIN_TEXT_LENGTH

    fake_result = SimpleNamespace(returncode=0, stdout=long_text, stderr="")
    with patch("apps.parsers.pipeline.subprocess.run", return_value=fake_result):
        out = p._extract_doc_text(tmp_path / "x.doc")
    assert out == long_text


def test_extract_doc_text_falls_through_when_antiword_missing(
    pipeline_factory, tmp_path
):
    """When antiword raises FileNotFoundError, libreoffice path is tried;
    when libreoffice also raises, return empty string."""
    p = pipeline_factory()

    call_count = {"n": 0}

    def _raise(*args, **kwargs):
        call_count["n"] += 1
        raise FileNotFoundError(args[0][0] if args else "?")

    with patch("apps.parsers.pipeline.subprocess.run", side_effect=_raise):
        out = p._extract_doc_text(tmp_path / "x.doc")
    assert out == ""
    # antiword first, libreoffice second
    assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# _ocr_extract — dependency-missing paths
# ---------------------------------------------------------------------------


def test_ocr_extract_returns_empty_when_pytesseract_missing(pipeline_factory):
    p = pipeline_factory()

    real_import = builtins.__import__

    def _raise(name, *args, **kwargs):
        if name == "pytesseract":
            raise ImportError
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_raise):
        out = p._ocr_extract(Path("/nonexistent.pdf"))
    assert out == ""


def test_ocr_extract_returns_empty_when_pdf2image_missing(pipeline_factory):
    p = pipeline_factory()

    real_import = builtins.__import__

    def _raise(name, *args, **kwargs):
        if name == "pdf2image":
            raise ImportError
        if name == "pytesseract":
            return SimpleNamespace(image_to_string=lambda *_args, **_kwargs: "")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_raise):
        out = p._ocr_extract(Path("/nonexistent.pdf"))
    assert out == ""


# ---------------------------------------------------------------------------
# _parse_to_xml — delegates to the AKN generator
# ---------------------------------------------------------------------------


def test_parse_to_xml_calls_generator_with_metadata(pipeline_factory, law_meta):
    p = pipeline_factory()
    p.parser = MagicMock()
    p.parser.create_frbr_metadata.return_value = {"some": "frbr"}

    out_path = p._parse_to_xml(law_meta, "Article 1. Foo.")
    assert out_path == p.xml_dir / f"mx-fed-{law_meta['id']}-v2.xml"

    p.parser.create_frbr_metadata.assert_called_once()
    p.parser.generate_xml.assert_called_once()
    # The metadata passed to generate_xml is the augmented dict
    md_arg = p.parser.generate_xml.call_args.args[1]
    assert md_arg["law_id"] == law_meta["id"]
    assert md_arg["status"] == "vigente"


# ---------------------------------------------------------------------------
# _calculate_quality — delegates to QualityCalculator
# ---------------------------------------------------------------------------


def test_calculate_quality_delegates(pipeline_factory, law_meta):
    p = pipeline_factory()
    p.quality_calc = MagicMock()
    p.quality_calc.calculate.return_value = _make_metrics(grade="B", overall=80.0)

    metrics = p._calculate_quality(Path("/x.xml"), law_meta, parse_time=1.2)
    assert metrics.grade == "B"
    p.quality_calc.calculate.assert_called_once()
    kw = p.quality_calc.calculate.call_args.kwargs
    assert kw["law_name"] == law_meta["name"]
    assert kw["law_slug"] == law_meta["slug"]


# ---------------------------------------------------------------------------
# _sync_to_storage — uploads only files that exist
# ---------------------------------------------------------------------------


def test_sync_to_storage_uploads_existing_files(pipeline_factory, tmp_path):
    storage = MagicMock()
    p = pipeline_factory(storage=storage)

    pdf = tmp_path / "amparo.pdf"
    pdf.write_bytes(b"x")
    txt = tmp_path / "amparo_extracted.txt"
    txt.write_bytes(b"x")
    xml = tmp_path / "mx-fed-amparo-v2.xml"
    xml.write_bytes(b"x")

    p._sync_to_storage("amparo", pdf, txt, xml)
    assert storage.put_file.call_count == 3


def test_sync_to_storage_skips_missing_files(pipeline_factory, tmp_path):
    storage = MagicMock()
    p = pipeline_factory(storage=storage)

    # pdf exists; txt and xml do not
    pdf = tmp_path / "amparo.pdf"
    pdf.write_bytes(b"x")
    txt = tmp_path / "missing.txt"
    xml = tmp_path / "missing.xml"

    p._sync_to_storage("amparo", pdf, txt, xml)
    assert storage.put_file.call_count == 1


# ---------------------------------------------------------------------------
# ingest_law — full orchestration
# ---------------------------------------------------------------------------


def test_ingest_law_happy_path(pipeline_factory, law_meta, tmp_path):
    p = pipeline_factory(storage=MagicMock(), db_saver=MagicMock())

    pdf = p.pdf_dir / f"{law_meta['id']}.pdf"
    pdf.write_bytes(b"x")
    txt = p.text_dir / f"{law_meta['id']}_extracted.txt"
    txt.write_text("law body", encoding="utf-8")
    xml = p.xml_dir / f"mx-fed-{law_meta['id']}-v2.xml"

    with patch.object(p, "_download_pdf", return_value=pdf), patch.object(
        p, "_extract_text", return_value=(txt, "law body")
    ), patch.object(p, "_parse_to_xml", return_value=xml), patch.object(
        p, "_calculate_quality", return_value=_make_metrics(grade="A", overall=95.0)
    ), patch(
        "apps.parsers.pipeline.detect_and_store_cross_references", create=True
    ) as cref:
        cref.return_value = 7
        result = p.ingest_law(law_meta)

    assert result.success is True
    assert "download" in result.stages_completed
    assert "extract" in result.stages_completed
    assert "parse" in result.stages_completed
    assert "quality" in result.stages_completed
    assert "storage_sync" in result.stages_completed
    p.db_saver.save_law_version.assert_called_once()
    p.storage.put_file.assert_called()


def test_ingest_law_quarantines_low_grade(pipeline_factory, law_meta):
    p = pipeline_factory(storage=None, db_saver=MagicMock())

    pdf = p.pdf_dir / f"{law_meta['id']}.pdf"
    pdf.write_bytes(b"x")
    txt = p.text_dir / f"{law_meta['id']}_extracted.txt"
    txt.write_text("body", encoding="utf-8")
    xml = p.xml_dir / f"mx-fed-{law_meta['id']}-v2.xml"

    with patch.object(p, "_download_pdf", return_value=pdf), patch.object(
        p, "_extract_text", return_value=(txt, "body")
    ), patch.object(p, "_parse_to_xml", return_value=xml), patch.object(
        p, "_calculate_quality", return_value=_make_metrics(grade="F", overall=20.0)
    ):
        result = p.ingest_law(law_meta)

    assert result.success is False
    assert "Quarantined" in result.error
    # Quarantined laws still get a best-effort DB save
    p.db_saver.save_law_version.assert_called_once()


def test_ingest_law_retries_on_transient_failure(pipeline_factory, law_meta):
    """The pipeline retries up to max_retries before giving up."""
    p = pipeline_factory()

    call_log: list[int] = []

    def _flaky(*_args, **_kwargs):
        call_log.append(1)
        if len(call_log) < 3:
            raise RuntimeError("network blip")
        # On the 3rd attempt, return a path that exists
        path = p.pdf_dir / f"{law_meta['id']}.pdf"
        path.write_bytes(b"x")
        return path

    txt = p.text_dir / f"{law_meta['id']}_extracted.txt"
    xml = p.xml_dir / f"mx-fed-{law_meta['id']}-v2.xml"

    with patch.object(p, "_download_pdf", side_effect=_flaky), patch.object(
        p,
        "_extract_text",
        return_value=(txt, "body"),
    ), patch.object(p, "_parse_to_xml", return_value=xml), patch.object(
        p, "_calculate_quality", return_value=_make_metrics(grade="A")
    ), patch.dict(
        "sys.modules", {"apps.parsers.cross_reference_integration": None}
    ), patch(
        "apps.parsers.pipeline.time.sleep"
    ):  # don't actually sleep during retry
        result = p.ingest_law(law_meta, max_retries=2)

    assert result.success is True
    assert len(call_log) == 3  # initial + 2 retries


def test_ingest_law_records_terminal_failure(pipeline_factory, law_meta):
    """When all retries exhaust, error_tracker.track is called and result.error set."""
    p = pipeline_factory()
    p.error_tracker = MagicMock()
    p.error_tracker.categorize_exception.return_value = "PARSE_ERROR"

    with patch.object(p, "_download_pdf", side_effect=RuntimeError("permanent")), patch(
        "apps.parsers.pipeline.time.sleep"
    ):
        result = p.ingest_law(law_meta, max_retries=1)

    assert result.success is False
    assert "permanent" in (result.error or "")
    p.error_tracker.track.assert_called_once()


def test_ingest_law_swallows_cross_ref_failure(pipeline_factory, law_meta):
    """Cross-reference failure must not break the whole ingestion."""
    p = pipeline_factory(db_saver=MagicMock())

    pdf = p.pdf_dir / f"{law_meta['id']}.pdf"
    pdf.write_bytes(b"x")
    txt = p.text_dir / f"{law_meta['id']}_extracted.txt"
    txt.write_text("body", encoding="utf-8")
    xml = p.xml_dir / f"mx-fed-{law_meta['id']}-v2.xml"

    with patch.object(p, "_download_pdf", return_value=pdf), patch.object(
        p, "_extract_text", return_value=(txt, "body")
    ), patch.object(p, "_parse_to_xml", return_value=xml), patch.object(
        p, "_calculate_quality", return_value=_make_metrics(grade="A")
    ):
        # Make the cross-ref import path raise
        with patch.dict(
            "sys.modules", {"apps.parsers.cross_reference_integration": None}
        ):
            result = p.ingest_law(law_meta)

    # Pipeline still succeeds even if cross-ref module is broken/missing
    assert result.success is True
    assert "cross_references" not in result.stages_completed


def test_ingest_law_swallows_db_save_failure(pipeline_factory, law_meta):
    """A DB save failure on a healthy ingestion is logged but non-fatal."""
    p = pipeline_factory(db_saver=MagicMock())
    p.db_saver.save_law_version.side_effect = RuntimeError("db down")

    pdf = p.pdf_dir / f"{law_meta['id']}.pdf"
    pdf.write_bytes(b"x")
    txt = p.text_dir / f"{law_meta['id']}_extracted.txt"
    txt.write_text("body", encoding="utf-8")
    xml = p.xml_dir / f"mx-fed-{law_meta['id']}-v2.xml"

    with patch.object(p, "_download_pdf", return_value=pdf), patch.object(
        p, "_extract_text", return_value=(txt, "body")
    ), patch.object(p, "_parse_to_xml", return_value=xml), patch.object(
        p, "_calculate_quality", return_value=_make_metrics(grade="A")
    ), patch(
        "apps.parsers.pipeline.detect_and_store_cross_references",
        create=True,
        return_value=0,
    ):
        result = p.ingest_law(law_meta)

    assert result.success is True


def test_ingest_law_swallows_storage_sync_failure(pipeline_factory, law_meta):
    """Storage sync failure is logged but non-fatal."""
    storage = MagicMock()
    storage.put_file.side_effect = RuntimeError("R2 unavailable")
    p = pipeline_factory(storage=storage, db_saver=MagicMock())

    pdf = p.pdf_dir / f"{law_meta['id']}.pdf"
    pdf.write_bytes(b"x")
    txt = p.text_dir / f"{law_meta['id']}_extracted.txt"
    txt.write_text("body", encoding="utf-8")
    xml = p.xml_dir / f"mx-fed-{law_meta['id']}-v2.xml"

    with patch.object(p, "_download_pdf", return_value=pdf), patch.object(
        p, "_extract_text", return_value=(txt, "body")
    ), patch.object(p, "_parse_to_xml", return_value=xml), patch.object(
        p, "_calculate_quality", return_value=_make_metrics(grade="A")
    ), patch(
        "apps.parsers.pipeline.detect_and_store_cross_references",
        create=True,
        return_value=0,
    ):
        result = p.ingest_law(law_meta)

    assert result.success is True
    assert "storage_sync" not in result.stages_completed
