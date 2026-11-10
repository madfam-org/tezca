"""RMF rules survive segment → AKN → index extraction with citable ids.

``/api/v1/laws/rmf_2026/articles/`` serves ``article_id`` from
``index_laws.extract_articles_from_xml`` (ES ``_id`` = ``"{law}-{article_id}"``).
This round trip pins what consumers cite: rule ``3.13.7`` is article
``3.13.7`` with its own text; transitorios are ``T-N`` (base resolution) and
``T-RK-N`` (block K = the resolución de modificaciones K - 1); rules in
Capítulo 3.23 "De las disposiciones transitorias de la Ley del ISR" stay rules.
"""

from unittest.mock import MagicMock

import pytest
from lxml import etree

from apps.api.transitorios import derive_article_id
from apps.parsers.rmf.akn import build_akn
from apps.parsers.rmf.lines import load_jsonl
from apps.parsers.rmf.segmenter import segment
from tests.parsers.test_rmf_segmenter import FIXTURE
from tests.pipeline.test_index_laws import Command  # imported under mocked Django

AKN = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
META = {
    "official_id": "rmf_2026",
    "work_date": "2025-12-28",
    "expression_date": "2026-10-02",
}


@pytest.fixture(scope="module")
def xml():
    return build_akn(segment(load_jsonl(FIXTURE)), META)


@pytest.fixture(scope="module")
def by_id(xml):
    command = Command()
    command.stdout = MagicMock()
    command.stderr = MagicMock()
    command.style = MagicMock()
    articles = command.extract_articles_from_xml(xml, "rmf_2026")
    ids = [a["article_id"] for a in articles]
    assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"
    command.stderr.write.assert_not_called()  # no -dupN renames, no rewrites
    return {a["article_id"]: a for a in articles}


def test_article_ids(by_id):
    assert list(by_id) == [
        "Glosario",
        "2.12.4",
        "2.12.5",
        *[f"3.13.{n}" for n in range(1, 36)],
        "3.23.1",
        *[f"T-{n}" for n in range(1, 30)],
        "T-R2-1",
        "T-R4-1",
    ]


def test_rule_text_is_its_own_and_ends_with_references(by_id):
    article = by_id["3.13.1"]
    assert not article["is_transitorio"]
    assert article["text"] == (
        "Para los efectos de los artículos 27, apartados A, fracción I y B, "
        "fracción I del CFF, 113-E y 113-G, fracción I de la Ley del ISR, las "
        "personas físicas que soliciten su inscripción en el RFC para tributar "
        "en el Régimen Simplificado de Confianza, deberán realizarlo conforme a "
        "la ficha de trámite 1/CFF “Solicitud de inscripción en el RFC de "
        "personas físicas”, contenida en el Anexo 2."
        "\n\nLISR 113-E, 113-G, CFF 27"
    )
    assert article["title"] == {
        "num": "Título 3.",
        "heading": "Impuesto sobre la renta",
    }
    assert article["chapter"] == {
        "num": "Capítulo 3.13.",
        "heading": "Del Régimen Simplificado de Confianza",
    }


def test_compiler_notes_are_not_rule_text(by_id):
    article = by_id["2.12.4"]
    assert article["text"] == "Se deroga."


def test_rules_under_transitorias_chapter_are_not_transitorios(by_id):
    assert by_id["3.23.1"]["is_transitorio"] is False
    assert by_id["3.23.1"]["chapter"]["num"] == "Capítulo 3.23."


def test_transitorio_ids_and_text(by_id):
    assert by_id["T-1"]["is_transitorio"]
    assert by_id["T-1"]["text"] == (
        "La presente Resolución entrará en vigor el 1o. de enero de 2026 y "
        "estará vigente hasta el 31 de diciembre de 2026."
    )
    assert by_id["T-R4-1"]["text"] == (
        "La presente resolución entrará en vigor a partir del 31 de diciembre de 2026."
    )


def test_akn_structure(xml):
    root = etree.fromstring(xml.encode("utf-8"))
    ns = {"a": AKN}
    rule = root.xpath("//a:article[@eId='regla-3-13-7']", namespaces=ns)[0]
    assert rule.findtext("a:num", namespaces=ns) == "3.13.7."
    assert rule.findtext("a:heading", namespaces=ns) == (
        "Pagos mensuales del Régimen Simplificado de Confianza de personas físicas"
    )
    assert rule.getparent().get("eId") == "tit_3__cap_3-13"
    expression = root.xpath("//a:FRBRExpression/a:FRBRthis/@value", namespaces=ns)[0]
    assert expression == (
        "/mx/fed/resolucion-miscelanea-fiscal/2025-12-28/rmf_2026/spa@2026-10-02/main"
    )
    note = root.xpath("//a:article[@eId='regla-2-12-4']/a:note/a:p", namespaces=ns)
    assert note[1].text.startswith("- Derogada en la Primera RMRMF")


def _article(num, parent_heading):
    xml = (
        f'<akomaNtoso xmlns="{AKN}"><act><body>'
        f"<chapter><num>Capítulo 3.23.</num><heading>{parent_heading}</heading>"
        f'<article eId="regla-3-23-1"><num>{num}</num></article>'
        f"</chapter></body></act></akomaNtoso>"
    )
    return etree.fromstring(xml.encode("utf-8")).xpath(
        "//a:article", namespaces={"a": AKN}
    )[0]


def test_dotted_rule_number_is_never_a_transitorio():
    heading = "De las disposiciones transitorias de la Ley del ISR"
    assert derive_article_id(_article("3.23.1.", heading)) == ("3.23.1", False)
    assert derive_article_id(_article("2.7.7.1.1.", heading)) == ("2.7.7.1.1", False)
    # An ordinal under the same heading is still a transitorio.
    assert derive_article_id(_article("Primero", heading))[1] is True
