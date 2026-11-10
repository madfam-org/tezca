"""LISR article segmentation: lettered (113-A..J), Latin-suffixed (82-Bis/Ter/
Quáter) articles and Art. 27 with its fracciones each resolve to their own text.

Fixture: ``tests/fixtures/lisr/lisr_dof_2024_04_01_excerpt.txt``, verbatim line
excerpts of the LISR consolidated text (Última Reforma DOF 01-04-2024) as
extracted from the Cámara de Diputados PDF:

* Art. 27 (heading + fr. I opening, then fr. VII–X). Fr. VII ends with the
  wrapped cross-reference line "artículo 143 de la presente Ley, …". The
  pre-Phase-6 parser matched article headings case-insensitively, opened a
  bogus "art-143" there and filed fr. VIII onwards — including fr. IX, the
  administrator-fee requirement — under Art. 143;
* Arts. 82-Bis, 82-Ter, 82-Quáter (read as "82-B/T/Q" by the lettered pattern);
* Art. 113 ("Se deroga") and the whole Sección IV, Arts. 113-A..113-J, which
  the legacy export collapsed into a single "113". 113-E fr. IV is the RESICO
  exclusion consumed by Money Moves (RFC 0052, WS-1).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.parsers.akn_generator_v2 import AkomaNtosoGeneratorV2  # noqa: E402
from apps.parsers.patterns.articles import compile_article_patterns  # noqa: E402

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "lisr"
    / "lisr_dof_2024_04_01_excerpt.txt"
)

SECCION_IV = [f"art-113{letter}" for letter in "abcdefghij"]


@pytest.fixture(scope="module")
def articles():
    text = FIXTURE.read_text(encoding="utf-8")
    result = AkomaNtosoGeneratorV2().parse_structure_v2(text)
    return [e for e in result.elements if e["type"] == "article"]


@pytest.fixture(scope="module")
def by_id(articles):
    ids = [a["id"] for a in articles]
    assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"
    return {a["id"]: a for a in articles}


def _first(pattern_text):
    for pattern in compile_article_patterns():
        match = pattern.match(pattern_text)
        if match:
            return match
    return None


class TestLisrSegmentation:
    def test_exact_article_sequence(self, articles):
        assert [a["id"] for a in articles] == [
            "art-27",
            "art-28",
            "art-82bis",
            "art-82ter",
            "art-82quater",
            "art-83",
            "art-113",
            *SECCION_IV,
            "art-114",
        ]

    def test_seccion_iv_numbers_keep_their_letter(self, by_id):
        assert [by_id[i]["number"] for i in SECCION_IV] == [
            f"113-{letter}" for letter in "ABCDEFGHIJ"
        ]

    @pytest.mark.parametrize("letter", list("ABCDEFGHIJ"))
    def test_each_113_letter_holds_only_its_own_text(self, by_id, letter):
        content = by_id[f"art-113{letter.lower()}"]["content"]
        assert content.startswith(f"Artículo 113-{letter}.")
        for other in "ABCDEFGHIJ":
            if other != letter:
                assert f"Artículo 113-{other}." not in content

    def test_113_derogated_stays_separate(self, by_id):
        assert by_id["art-113"]["content"].startswith("Artículo 113. Se deroga.")
        assert "113-A" not in by_id["art-113"]["content"]

    def test_113e_carries_resico_bar_and_fraccion_iv(self, by_id):
        content = by_id["art-113e"]["content"]
        assert "no hubieran excedido de la cantidad de tres millones" in content
        assert "Hasta 3,500,000.00 2.50%" in content
        assert (
            "IV. Perciban los ingresos a que se refieren las fracciones III, IV, V "
            "y VI del artículo 94 de esta Ley." in content
        )

    def test_113c_keeps_wrapped_cross_reference(self, by_id):
        assert "artículo 113-A de esta Ley, mediante declaración" in (
            by_id["art-113c"]["content"]
        )

    def test_27_keeps_fraccion_ix(self, by_id):
        content = by_id["art-27"]["content"]
        assert content.startswith("Artículo 27. Las deducciones autorizadas")
        assert (
            "IX. Que tratándose de honorarios o gratificaciones a administradores, "
            "comisarios, directores," in content
        )
        assert "VIII. Que tratándose de pagos" in content
        assert "X. Que en los casos de asistencia técnica" in content

    def test_lowercase_cross_reference_is_not_an_article(self, by_id):
        assert "art-143" not in by_id
        assert "artículo 143 de la presente Ley" in by_id["art-27"]["content"]

    @pytest.mark.parametrize(
        "art_id,number,opening",
        [
            ("art-82bis", "82-Bis", "Artículo 82-Bis. Las instituciones autorizadas"),
            ("art-82ter", "82-Ter", "Artículo 82-Ter. Se deroga."),
            ("art-82quater", "82-Quáter", "Artículo 82-Quáter. Para los efectos"),
        ],
    )
    def test_latin_suffix_articles(self, by_id, art_id, number, opening):
        assert by_id[art_id]["number"] == number
        assert by_id[art_id]["content"].startswith(opening)


class TestSuffixPatterns:
    @pytest.mark.parametrize(
        "line,base,suffix",
        [
            ("Artículo 82-Bis. Texto.", "82", "Bis"),
            ("Artículo 82-Ter. Se deroga.", "82", "Ter"),
            ("Artículo 82-Quáter. Texto.", "82", "Quáter"),
            ("Artículo 5 Bis. Texto.", "5", "Bis"),
            ("Artículo 5o. Bis 1.- Texto.", "5o.", "Bis 1"),
            ("Artículo 9 Ter.- Texto.", "9", "Ter"),
            ("Artículo 113-E. Texto.", "113", "E"),
            ("ARTÍCULO 27-A.- Texto.", "27", "A"),
            ("ARTICULO 12-BIS.- Texto.", "12", "BIS"),
        ],
    )
    def test_suffix_is_captured(self, line, base, suffix):
        match = _first(line)
        assert match is not None
        assert match.lastindex and match.lastindex >= 2
        assert match.group(1) == base
        assert match.group(2) == suffix

    @pytest.mark.parametrize(
        "line",
        [
            "Artículo 5 Tercero del Decreto.",  # "Ter" must not match "Tercero"
            "Artículo 27-Apartado B.",  # "A" must stand alone
        ],
    )
    def test_suffix_needs_a_word_boundary(self, line):
        match = _first(line)
        assert match is not None
        assert not (match.lastindex and match.lastindex >= 2)
