"""The pipeline extracts Diputados PDFs without page furniture and passes the
«Última Reforma DOF» date on to the database saver."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from apps.parsers.pipeline import IngestionPipeline

HEADER = (
    "LEY FEDERAL DE PROTECCIÓN DE DATOS PERSONALES EN POSESIÓN DE LOS PARTICULARES\n"
    "CÁMARA DE DIPUTADOS DEL H. CONGRESO DE LA UNIÓN Última Reforma DOF 14-11-2025\n"
    "Secretaría General\n"
    "Secretaría de Servicios Parlamentarios\n"
)
PAGE_1 = (
    HEADER + "Artículo 1.- La presente Ley es de orden público y de observancia "
    "general en todo el territorio nacional, y tiene por objeto la\n1 de 2"
)
PAGE_2 = (
    HEADER + "protección de los datos personales en posesión de los particulares.\n"
    "Artículo 2.- Para los efectos de esta Ley, se entenderá por:\n2 de 2"
)


@pytest.fixture
def pipeline(tmp_path):
    with patch("apps.api.storage.get_storage_backend", return_value=None):
        with patch("ingestion.db_saver.DatabaseSaver", return_value=MagicMock()):
            built = IngestionPipeline(data_dir=tmp_path, skip_download=True)
    built.db_saver = MagicMock()
    built.storage = None
    return built


def _fake_pdfplumber(*pages):
    pdf = MagicMock()
    pdf.pages = [MagicMock(**{"extract_text.return_value": text}) for text in pages]
    pdf.__enter__ = MagicMock(return_value=pdf)
    pdf.__exit__ = MagicMock(return_value=False)
    module = MagicMock()
    module.open.return_value = pdf
    return module


def test_extracted_text_has_no_page_furniture(pipeline, tmp_path):
    pdf_path = tmp_path / "lfpdppp.pdf"
    with patch.dict(sys.modules, {"pdfplumber": _fake_pdfplumber(PAGE_1, PAGE_2)}):
        text = pipeline._extract_pdf_text(pdf_path)

    assert text == (
        "Artículo 1.- La presente Ley es de orden público y de observancia "
        "general en todo el territorio nacional, y tiene por objeto la\n"
        "protección de los datos personales en posesión de los particulares.\n"
        "Artículo 2.- Para los efectos de esta Ley, se entenderá por:"
    )
    assert pipeline._last_reform_by_file["lfpdppp.pdf"].isoformat() == "2025-11-14"


def test_last_reform_date_reaches_the_database_saver(pipeline, tmp_path):
    law = {
        "id": "lfpdppp",
        "name": "Ley Federal de Protección de Datos Personales",
        "slug": "lfpdppp",
        "publication_date": "2025-03-20",
        "url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf",
    }
    pdf_path = pipeline.pdf_dir / "lfpdppp.pdf"
    pdf_path.write_bytes(b"%PDF" + b"0" * 2048)
    xml_path = pipeline.xml_dir / "mx-fed-lfpdppp-v2.xml"
    metrics = SimpleNamespace(grade="A", overall_score=95.0)

    with patch.dict(
        sys.modules, {"pdfplumber": _fake_pdfplumber(PAGE_1, PAGE_2)}
    ), patch.object(
        pipeline, "_parse_to_xml", return_value=xml_path
    ) as parse, patch.object(
        pipeline, "_calculate_quality", return_value=metrics
    ), patch(
        "apps.parsers.pipeline.detect_and_store_cross_references",
        create=True,
        return_value=0,
    ):
        result = pipeline.ingest_law(law)

    assert result.success
    parsed_text = parse.call_args.args[1]
    assert "Servicios Parlamentarios" not in parsed_text
    saved_metadata = pipeline.db_saver.save_law_version.call_args.args[0]
    assert saved_metadata["last_reform_date"] == "2025-11-14"
    # The caller's registry entry is not mutated.
    assert "last_reform_date" not in law
