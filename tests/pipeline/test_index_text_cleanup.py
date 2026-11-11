"""A re-index of an existing XML serves clean article text.

XMLs generated before the pipeline stripped it keep the Cámara de Diputados
page furniture, the decree closing and decree stubs inside ``<p>`` text. The
indexer removes them, so cleaning production needs a re-index, not a
re-download. The XML below has the legacy LFPDPPP shape (transitorios as
``Artículo N`` nodes whose text opens with the ordinal heading).
"""

from unittest.mock import MagicMock

import pytest

from tests.pipeline.test_index_laws import Command

AKN = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"

HEADER = (
    "LEY FEDERAL DE PROTECCIÓN DE DATOS PERSONALES EN POSESIÓN DE LOS PARTICULARES "
    "CÁMARA DE DIPUTADOS DEL H. CONGRESO DE LA UNIÓN Última Reforma DOF 14-11-2025\n"
    "Secretaría General Secretaría de Servicios Parlamentarios"
)


def _art(node_id, num, text):
    return (
        f'<article id="{node_id}"><num>{num}</num>'
        f"<content><p>{text}</p></content></article>"
    )


LEGACY_XML = (
    f'<?xml version="1.0" encoding="UTF-8"?><akomaNtoso xmlns="{AKN}"><act><body>'
    + _art(
        "art-1",
        "Artículo 1",
        "La presente Ley es de orden público, sin fines de utilización comercial.\n"
        f"1 de 24\n{HEADER}",
    )
    + _art(
        "art-2",
        "Artículo 2",
        "XI. Ley: Ley Federal de Protección de Datos Personales;\n"
        f"2 de 24\n{HEADER} XII. Persona encargada: Persona física.",
    )
    + _art("art-10", "Artículo 10", "Principio de calidad de los datos.")
    + _art("art-20", "Artículo 20", "El responsable deberá establecer controles.")
    + _art(
        "art-64",
        "Artículo 64",
        "Tratándose de datos personales sensibles, las penas se duplicarán.\n"
        "Artículo Cuarto.- ……..\nTransitorios",
    )
    + _art(
        "art-1",
        "Artículo 1",
        "Primero.- El presente Decreto entrará en vigor al día siguiente.\n"
        f"17 de 24\n{HEADER}",
    )
    + _art(
        "art-10",
        "Artículo 10",
        "Décimo.- Los procedimientos iniciados con anterioridad, se\n"
        f"19 de 24\n{HEADER} sustanciarán conforme a las disposiciones vigentes.",
    )
    + _art(
        "art-10",
        "Artículo 10",
        "Décimo Quinto.- Para efectos de lo dispuesto en los transitorios "
        "Quinto, Sexto, Séptimo, Octavo y",
    )
    + _art(
        "art-10",
        "Artículo 10",
        "Décimo Tercero del presente Decreto el Pleno deberá integrar un Comité.",
    )
    + _art(
        "art-20",
        "Artículo 20",
        "Vigésimo.- El Poder Judicial de la Federación deberá habilitar juzgados.\n"
        "Ciudad de México, a 20 de marzo de 2025.- Sen. Imelda Castro Castro, "
        'Vicepresidenta.- Rúbricas."\n'
        f"21 de 24\n{HEADER} En cumplimiento de lo dispuesto por la fracción I del "
        "Artículo 89 de la Constitución, expido el presente Decreto.\n"
        f"22 de 24\n{HEADER} ARTÍCULOS TRANSITORIOS DE DECRETOS DE REFORMA DECRETO "
        "por el que se reforman diversas disposiciones.\n"
        "Artículo Trigésimo Octavo.- Se reforma el artículo 4.\n……..\nTransitorios",
    )
    + _art(
        "art-1",
        "Artículo 1",
        "Primero. El presente Decreto entrará en vigor el día siguiente.",
    )
    + _art(
        "art-2",
        "Artículo 2",
        "Segundo. La aplicación se sujetará a lo dispuesto.\n"
        "Ciudad de México, a 01 de octubre de 2025.- Sen. Laura Itzel Castillo "
        'Juárez, Presidenta.- Rúbricas."\n'
        "En cumplimiento de lo dispuesto por la fracción I del Artículo 89, expido "
        "el presente Decreto en la\n"
        f"23 de 24\n{HEADER} Residencia del Poder Ejecutivo Federal.- Rúbrica.\n"
        "24 de 24",
    )
    + "</body></act></akomaNtoso>"
)


@pytest.fixture(scope="module")
def by_id():
    command = Command()
    command.stdout = MagicMock()
    command.stderr = MagicMock()
    command.style = MagicMock()
    articles = command.extract_articles_from_xml(LEGACY_XML, "lfpdppp")
    ids = [a["article_id"] for a in articles]
    assert len(ids) == len(set(ids))
    return {a["article_id"]: a for a in articles}


def test_ids_are_one_per_provision(by_id):
    assert sorted(by_id) == sorted(
        ["1", "2", "10", "20", "64"]
        + ["T-1", "T-10", "T-15", "T-20", "T-R2-1", "T-R2-2"]
    )


def test_no_page_furniture_in_any_article(by_id):
    for article in by_id.values():
        assert "Servicios Parlamentarios" not in article["text"]
        assert "CÁMARA DE DIPUTADOS" not in article["text"]
        assert "de 24" not in article["text"]


def test_text_is_joined_across_the_page_break(by_id):
    assert by_id["2"]["text"] == (
        "XI. Ley: Ley Federal de Protección de Datos Personales;\n"
        "XII. Persona encargada: Persona física."
    )
    assert by_id["T-10"]["text"] == (
        "Los procedimientos iniciados con anterioridad, se sustanciarán conforme "
        "a las disposiciones vigentes."
    )


def test_split_transitorio_reads_as_one_sentence(by_id):
    assert (
        "Séptimo, Octavo y Décimo Tercero del presente Decreto el Pleno"
        in by_id["T-15"]["text"]
    )


def test_decree_closing_is_not_indexed(by_id):
    assert by_id["T-20"]["text"] == (
        "El Poder Judicial de la Federación deberá habilitar juzgados."
    )
    assert by_id["T-R2-2"]["text"] == "La aplicación se sujetará a lo dispuesto."


def test_last_body_article_has_no_decree_stub(by_id):
    assert by_id["64"]["text"] == (
        "Tratándose de datos personales sensibles, las penas se duplicarán."
    )
