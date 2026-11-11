"""A consolidated Cámara de Diputados law parses into clean provisions.

The text below is a hand-written excerpt shaped like the LFPDPPP PDF: the
body, the ellipsis stub of the publishing decree's other articles, the law's
own transitorios, the decree closing, and the «ARTÍCULOS TRANSITORIOS DE
DECRETOS DE REFORMA» section with one reform decree. Production served the
closing glued onto the last transitorio and the stub glued onto Artículo 64.
"""

import pytest

from apps.parsers.akn_generator_v2 import AkomaNtosoGeneratorV2

CONSOLIDATED_LAW = """\
Artículo 63.- Se impondrán de tres meses a tres años de prisión.
Artículo 64.- Tratándose de datos personales sensibles, las penas se duplicarán.
Artículo Cuarto.- ……..
Transitorios
Primero.- El presente Decreto entrará en vigor al día siguiente de su publicación.
Segundo.- Se abroga la Ley publicada el 5 de julio de 2010.
Décimo Tercero.- Los expedientes en trámite se remitirán a la Secretaría.
Décimo Quinto.- Para efectos de lo dispuesto en los transitorios Quinto, Sexto, Octavo y
Décimo Tercero del presente Decreto el Pleno deberá integrar un Comité.
Vigésimo.- El Poder Judicial de la Federación deberá habilitar juzgados.
Para efectos de lo previsto en este transitorio, se suspenden los plazos.
Ciudad de México, a 20 de marzo de 2025.- Sen. Imelda Castro Castro, Vicepresidenta.- Rúbricas."
En cumplimiento de lo dispuesto por la fracción I del Artículo 89 de la Constitución, expido el presente Decreto.
ARTÍCULOS TRANSITORIOS DE DECRETOS DE REFORMA
DECRETO por el que se reforman diversas disposiciones de diversos ordenamientos.
Publicado en el Diario Oficial de la Federación el 14 de noviembre de 2025
Artículo Trigésimo Octavo.- Se reforma el artículo 4 de la Ley, para quedar como sigue:
……..
Transitorios
Primero. El presente Decreto entrará en vigor el día siguiente al de su publicación.
Segundo. La aplicación de lo dispuesto se sujetará al artículo Sexto Transitorio.
Ciudad de México, a 01 de octubre de 2025.- Sen. Laura Itzel Castillo Juárez, Presidenta.- Rúbricas."
"""


@pytest.fixture(scope="module")
def elements():
    result = AkomaNtosoGeneratorV2().parse_structure_v2(CONSOLIDATED_LAW)
    return {e["id"]: e for e in result.elements}


def test_one_representation_per_provision(elements):
    assert sorted(elements) == sorted(
        [
            "art-63",
            "art-64",
            "trans-1",
            "trans-2",
            "trans-13",
            "trans-15",
            "trans-20",
            "trans-r2-1",
            "trans-r2-2",
        ]
    )


def test_transitorios_are_never_numbered_as_body_articles(elements):
    assert [e["type"] for i, e in elements.items() if i.startswith("art-")] == [
        "article",
        "article",
    ]
    assert all(
        e["type"] == "transitorio" for i, e in elements.items() if i.startswith("tr")
    )


def test_last_body_article_drops_the_decree_stub(elements):
    content = elements["art-64"]["content"]
    assert content.endswith("las penas se duplicarán.")
    assert "Artículo Cuarto" not in content


def test_ordinal_inside_a_sentence_does_not_split_the_transitorio(elements):
    content = elements["trans-15"]["content"]
    assert "Octavo y\nDécimo Tercero del presente Decreto el Pleno" in content
    # The real Décimo Tercero keeps its own text.
    assert elements["trans-13"]["content"].startswith("Los expedientes en trámite")


def test_decree_closing_is_not_part_of_the_last_transitorio(elements):
    content = elements["trans-20"]["content"]
    assert content.endswith("se suspenden los plazos.")
    for furniture in ("Rúbricas", "Artículo 89", "DECRETOS DE REFORMA", "DECRETO por"):
        assert furniture not in content


def test_reform_decree_is_its_own_group(elements):
    assert elements["trans-r2-1"]["block"] == 2
    assert elements["trans-r2-1"]["content"].startswith("El presente Decreto entrará")
    assert elements["trans-r2-2"]["content"].endswith("artículo Sexto Transitorio.")
    assert elements["trans-1"]["block"] == 1


@pytest.mark.parametrize(
    "ordinal, number",
    [
        ("Décimo Primero", 11),
        ("Décimo Noveno", 19),
        ("Vigésimo", 20),
        ("Vigésimo Noveno", 29),
        ("Trigésimo", 30),
        ("TRIGÉSIMO PRIMERO", 31),
    ],
)
def test_compound_ordinals_resolve_to_stable_ids(ordinal, number):
    text = (
        "Artículo 1.- Objeto.\nTransitorios\nPrimero.- Vigencia.\n"
        f"{ordinal}.- Disposición final."
    )
    trans = AkomaNtosoGeneratorV2()._find_transitorios(text)
    assert [t["id"] for t in trans] == ["trans-1", f"trans-{number}"]
