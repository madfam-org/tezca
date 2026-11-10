"""RMF segmentation by rule number: specific rules resolve to their own text.

Fixture: ``tests/fixtures/rmf/rmf_2026_compilada_3a_rm_excerpt.jsonl`` — line
records (text, font style, alignment, page) read with
``apps.parsers.rmf.lines.extract_lines`` from SAT's compiled RMF 2026 through
the Tercera RMRMF:

    https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/documentos2026/rmf/
    compiladas/Compilado_Tercera_Modificacion_a_la-Resolucion_Miscelanea_
    Fiscal_para_2026.pdf
    SHA-256 0cbabc7a9a31d04a7dee50b129db7237f2e66649f9aca5685e40bf38ff28dde0

Excerpt, in document order and unedited: the opening lines of the Glosario
(p. 7); Título 2 and Capítulo 2.12 headings with the derogated rule 2.12.4
(compiler note + "Se deroga.") and rule 2.12.5 (p. 288); Título 3 heading;
all of Capítulo 3.13 "Del Régimen Simplificado de Confianza" (pp. 542–558);
Capítulo 3.23 "De las disposiciones transitorias de la Ley del ISR" up to rule
3.23.1; and the Transitorios to the end of the document (pp. 849–859),
including the blocks of the Primera, Segunda and Tercera RMRMF.

RESICO numbering, checked in the source: in the RMF 2026 both regimes sit in
Capítulo 3.13 — personas físicas 3.13.1–3.13.15 and following, personas
morales 3.13.16 (pagos provisionales), 3.13.27 (dejan de tributar) and
3.13.31 (en liquidación). Capítulo 3.21 is "De los estímulos fiscales"; it
holds no RESICO rules in 2026.
"""

from pathlib import Path

import pytest

from apps.parsers.rmf.lines import (
    ALIGN_HANGING,
    ALIGN_INSET,
    STYLE_BOLD,
    STYLE_ITALIC,
    SourceLine,
    load_jsonl,
)
from apps.parsers.rmf.segmenter import segment, validate

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "rmf"
    / "rmf_2026_compilada_3a_rm_excerpt.jsonl"
)


@pytest.fixture(scope="module")
def doc():
    return segment(load_jsonl(FIXTURE))


def test_parse_is_clean(doc):
    assert validate(doc) == []
    assert doc.warnings == []


def test_rule_numbers_in_document_order(doc):
    assert [r.number for r in doc.rules()] == [
        "2.12.4",
        "2.12.5",
        *[f"3.13.{n}" for n in range(1, 36)],
        "3.23.1",
    ]


def test_resico_personas_fisicas_inscripcion_3_13_1(doc):
    rule = doc.rule("3.13.1")
    assert rule.title == (
        "Opción para presentar el aviso de inscripción en el RFC en el "
        "Régimen Simplificado de Confianza"
    )
    assert (rule.titulo, rule.capitulo) == ("3", "3.13")
    assert rule.paragraphs == [
        "Para los efectos de los artículos 27, apartados A, fracción I y B, "
        "fracción I del CFF, 113-E y 113-G, fracción I de la Ley del ISR, las "
        "personas físicas que soliciten su inscripción en el RFC para tributar "
        "en el Régimen Simplificado de Confianza, deberán realizarlo conforme a "
        "la ficha de trámite 1/CFF “Solicitud de inscripción en el RFC de "
        "personas físicas”, contenida en el Anexo 2."
    ]
    assert rule.references == "LISR 113-E, 113-G, CFF 27"


def test_resico_personas_fisicas_pago_mensual_3_13_7(doc):
    rule = doc.rule("3.13.7")
    assert rule.title == (
        "Pagos mensuales del Régimen Simplificado de Confianza de personas físicas"
    )
    assert rule.paragraphs[0].startswith(
        "Para los efectos del artículo 113-E, quinto párrafo de la Ley del ISR, "
        "las personas físicas que tributen en el Régimen Simplificado de "
        "Confianza, deberán presentar el pago mensual a través de la "
        "declaración “ISR simplificado de confianza. Personas físicas”, a más "
        "tardar el día 17 del mes inmediato posterior"
    )
    assert "será definitivo" in rule.paragraphs[2]
    assert (
        rule.references == "LISR 113-E, 113-J, CFF 31, RMF 2.8.3.1., 3.13.20., 3.13.21."
    )
    # Its own text only: the next rule's epígrafe is not glued on.
    assert "Cumplimiento de obligaciones" not in rule.text


def test_resico_personas_morales_pagos_provisionales_3_13_16(doc):
    rule = doc.rule("3.13.16")
    assert rule.title == (
        "Pagos provisionales del Régimen Simplificado de Confianza de las "
        "personas morales"
    )
    # The quoted declaration name holds a period; it must not split the paragraph.
    assert rule.paragraphs[0] == (
        "Para los efectos del artículo 211 de la Ley del ISR, las personas "
        "morales del Régimen Simplificado de Confianza, deberán presentar los "
        "pagos provisionales mensuales a cuenta del impuesto del ejercicio a "
        "través de la presentación de la declaración “ISR de confianza. "
        "Personas Morales”, a más tardar el día 17 del mes inmediato siguiente "
        "al que corresponda el pago, conforme a lo establecido en la regla 2.8.3.1."
    )
    assert len(rule.paragraphs) == 6
    assert rule.references == "LISR 211, CFF 17-D, 31, RMF 2.8.3.1."


def test_resico_personas_morales_salida_3_13_27(doc):
    rule = doc.rule("3.13.27")
    assert rule.title == (
        "Contribuyentes que dejan de tributar en el Régimen Simplificado de "
        "Confianza de Personas Morales"
    )
    assert "$35’000,000.00 (treinta y cinco millones de pesos 00/100 M.N.)" in (
        rule.paragraphs[0]
    )
    assert rule.references == "LISR 206, 212, 214, CFF 27"


def test_resico_retencion_exception_3_13_26(doc):
    """The withholding exception Money Moves cites: personas morales need not
    withhold the 1.25% from exempt primary-sector personas físicas."""
    rule = doc.rule("3.13.26")
    assert "quedarán relevadas de efectuar la retención del 1.25%" in rule.text
    assert rule.references == "LISR 113-E, 113-J"


def test_derogated_rule_keeps_its_number_and_compiler_note(doc):
    rule = doc.rule("2.12.4")
    assert rule.derogada
    assert rule.paragraphs == ["Se deroga."]
    assert (
        rule.title
        == "Formalidades para el ofrecimiento de la garantía del interés fiscal"
    )
    assert rule.notes[0] == "Regla 2.12.4."
    assert rule.notes[1].startswith("- Derogada en la Primera RMRMF para 2026")
    # The bold "2.12.4. Se deroga." line is not absorbed into 2.12.5's epígrafe.
    assert (
        doc.rule("2.12.5").title
        == "Formalidades para la expedición del billete de depósito"
    )


def test_rule_under_disposiciones_transitorias_chapter_is_a_rule(doc):
    rule = doc.rule("3.23.1")
    assert rule.capitulo == "3.23"
    assert rule.title.startswith("Deducción de los excedentes de las reservas")


def test_base_transitorios(doc):
    base = [t for t in doc.transitorios if t.block == 1]
    assert [t.number for t in base] == list(range(1, 30))
    assert doc.transitorio(1).paragraphs == [
        "La presente Resolución entrará en vigor el 1o. de enero de 2026 y "
        "estará vigente hasta el 31 de diciembre de 2026."
    ]
    # Compound ordinal printed as bold "Décimo" + "Primero. …" on two lines.
    assert doc.transitorio(11).ordinal == "Décimo Primero"
    assert doc.transitorio(11).text.startswith("Para los efectos de la regla 2.7.1.21.")
    vigesimo_noveno = doc.transitorio(29)
    assert vigesimo_noveno.ordinal == "Vigésimo Noveno"
    assert vigesimo_noveno.notes[1].startswith("- Adicionado en la Segunda RMRMF")
    assert vigesimo_noveno.notes[1].endswith("el 24 de septiembre de 2026.")


def test_modification_blocks_and_their_transitorios(doc):
    assert [(m.block, m.label.split(",")[0]) for m in doc.modifications] == [
        (2, "Primera Modificación de la Resolución Miscelánea Fiscal para 2026"),
        (3, "Segunda Modificación de la Resolución Miscelánea Fiscal para 2026"),
        (4, "Tercera Modificación de la Resolución Miscelánea Fiscal para 2026"),
    ]
    primera = doc.transitorio(1, block=2)
    assert primera.ordinal == "Único"
    assert primera.text.startswith(
        "La presente resolución entrará en vigor a partir del día siguiente al "
        "de su publicación en el DOF."
    )
    assert doc.transitorio(1, block=4).text == (
        "La presente resolución entrará en vigor a partir del 31 de diciembre de 2026."
    )


def test_glossary_opening(doc):
    assert doc.glossary[0].startswith(
        "Para una mejor comprensión de lo establecido en la presente Resolución"
    )


def test_line_wrapped_lettered_article_is_rejoined():
    """DOF edition (p. 427–428): rule 3.13.7 wraps "artículo 113-" / "E de la
    Ley del ISR". The citation must read "113-E", not "113- E"; a spaced dash
    stays punctuation."""
    lines = [
        SourceLine(
            "Para una mejor comprensión de lo establecido en la presente "
            "Resolución y sus Anexos, se compila el siguiente glosario de "
            "acrónimos y definiciones:"
        ),
        SourceLine("Título 3. Impuesto sobre la renta", STYLE_BOLD, ALIGN_INSET),
        SourceLine(
            "Capítulo 3.13. Del Régimen Simplificado de Confianza",
            STYLE_BOLD,
            ALIGN_INSET,
        ),
        SourceLine(
            "Pagos mensuales del Régimen Simplificado de Confianza de personas físicas",
            STYLE_BOLD,
        ),
        SourceLine(
            "3.13.7. Para los efectos del artículo 113-E, quinto párrafo de la Ley "
            "del ISR, las personas físicas que",
            align=ALIGN_HANGING,
        ),
        SourceLine(
            "ingresos que perciban por las actividades a que se refiere el primer "
            "párrafo del artículo 113-"
        ),
        SourceLine(
            "E de la Ley del ISR en el ejercicio y que estén amparados por los CFDI "
            "efectivamente"
        ),
        SourceLine("cobrados, en la parte proporcional -"),
        SourceLine("que de los mismos les correspondan"),
        SourceLine("LISR 113-E, 113-J, CFF 31", STYLE_ITALIC),
    ]
    rule = segment(lines).rule("3.13.7")
    assert "del artículo 113-E de la Ley del ISR en el ejercicio" in rule.text
    assert "proporcional - que de los mismos" in rule.text
    assert rule.references == "LISR 113-E, 113-J, CFF 31"
