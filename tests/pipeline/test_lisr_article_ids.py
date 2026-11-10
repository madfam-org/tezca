"""LISR lettered articles survive parse → AKN XML → index extraction.

The public API serves ``article_id`` from ``index_laws.extract_articles_from_xml``
(ES ``_id`` = ``"{law}-{article_id}"``). Production LISR (indexed from an XML
built by the pre-Phase-6 parser) serves one "113" whose text is 113-J — the
other nine lettered articles overwrote each other. This round trip pins the
current pipeline: each lettered article gets its own id and its own text, and
the "Artículo 113-E." heading is stripped like any other article heading.
"""

import sys
from unittest.mock import MagicMock

import pytest

from apps.parsers.akn_generator_v2 import AkomaNtosoGeneratorV2
from tests.parsers.test_lisr_lettered_articles import FIXTURE
from tests.pipeline.test_index_laws import Command  # imported under mocked Django

ARTICLE_HEADING_RE = sys.modules[Command.__module__].ARTICLE_HEADING_RE


@pytest.fixture(scope="module")
def by_id(tmp_path_factory):
    generator = AkomaNtosoGeneratorV2()
    metadata = generator.create_frbr_metadata(
        "ley", "2013-12-11", "lisr", "Ley del Impuesto Sobre la Renta"
    )
    out = tmp_path_factory.mktemp("akn") / "mx-fed-lisr-v2.xml"
    generator.generate_xml(FIXTURE.read_text(encoding="utf-8"), metadata, out)

    command = Command()
    command.stdout = MagicMock()
    command.stderr = MagicMock()
    command.style = MagicMock()
    articles = command.extract_articles_from_xml(
        out.read_text(encoding="utf-8"), "lisr"
    )
    ids = [a["article_id"] for a in articles]
    assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"
    return {a["article_id"]: a for a in articles}


def test_api_article_ids(by_id):
    assert list(by_id) == [
        "27",
        "28",
        "82-Bis",
        "82-Ter",
        "82-Quáter",
        "83",
        "113",
        *[f"113-{letter}" for letter in "ABCDEFGHIJ"],
        "114",
    ]
    assert not any(a["is_transitorio"] for a in by_id.values())


def test_113e_text(by_id):
    text = by_id["113-E"]["text"]
    assert text.startswith("Los contribuyentes personas físicas que realicen")
    assert "Perciban los ingresos a que se refieren las fracciones III, IV, V" in text
    assert "Artículo 113-F" not in text


def test_113_is_the_derogated_article(by_id):
    assert by_id["113"]["text"].startswith("Se deroga.")


def test_27_text_holds_fraccion_ix(by_id):
    text = by_id["27"]["text"]
    assert text.startswith("Las deducciones autorizadas en este Título")
    assert "IX. Que tratándose de honorarios o gratificaciones a administradores" in (
        text
    )
    assert "143" not in by_id


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Artículo 27. Las deducciones", "Las deducciones"),
        ("Artículo 113-E. Los contribuyentes", "Los contribuyentes"),
        ("Artículo 82-Quáter. Para los efectos", "Para los efectos"),
        ("Artículo 1o.- Esta Ley", "Esta Ley"),
        ("Artículo 5o. Bis 1.- El texto", "El texto"),
        ("ARTÍCULO 12 BIS.- El texto", "El texto"),
        # The old pattern (\d+[\w\s]*\.) swallowed the whole first sentence.
        (
            "Artículo 5 Bis Se deroga. Segundo enunciado.",
            "Se deroga. Segundo enunciado.",
        ),
        ("Artículo 1.- A los efectos de esta Ley", "A los efectos de esta Ley"),
    ],
)
def test_heading_strip(raw, expected):
    assert ARTICLE_HEADING_RE.sub("", raw, count=1) == expected
