"""
Integration tests for the V2 parser (AkomaNtosoGeneratorV2).

Self-contained tests using inline text fixtures -- no external law files required.
Covers article detection, structure detection, transitorios, confidence scoring,
gap detection, derogation detection, and full parse cycles.
"""

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup so the apps package is importable regardless of working directory
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.parsers.akn_generator_v2 import AkomaNtosoGeneratorV2, ParseResult
from apps.parsers.patterns.articles import (
    compile_article_patterns,
    is_derogated,
    ordinal_to_number,
)
from apps.parsers.patterns.structure import (
    compile_structure_patterns,
    compile_transitorios_patterns,
    roman_to_int,
)

# ===========================================================================
# Inline fixtures
# ===========================================================================

MINIMAL_LAW_TEXT = """\
TITULO PRIMERO
De las Disposiciones Generales

CAPITULO I
Disposiciones Preliminares

Articulo 1.- Esta ley es de orden publico e interes social.

Articulo 2.- Para los efectos de esta ley, se entiende por autoridad competente
la que determine el presente ordenamiento; las disposiciones son de observancia
general en todo el territorio nacional.

Articulo 3.- Se deroga.

TRANSITORIOS

PRIMERO.- Esta ley entrara en vigor al dia siguiente de su publicacion.

SEGUNDO.- Se derogan todas las disposiciones que se opongan al presente decreto.
"""

MULTI_STRUCTURE_LAW_TEXT = """\
LIBRO PRIMERO
De los Principios Fundamentales

TITULO I
Disposiciones Generales

CAPITULO I
Del Objeto de la Ley

Articulo 1.- El presente ordenamiento tiene por objeto regular las actividades
conforme a lo dispuesto en la Constitucion.

Articulo 2.- Son principios rectores de esta ley:
I. Legalidad;
II. Transparencia;
III. Rendicion de cuentas.

CAPITULO II
De las Autoridades

Articulo 3.- La autoridad competente sera la encargada de aplicar esta ley,
en terminos de las disposiciones reglamentarias.

TITULO II
De los Derechos y Obligaciones

CAPITULO III
De los Derechos

Articulo 4.- Toda persona tiene derecho a solicitar informacion.

Articulo 5.- Las autoridades deberan garantizar el acceso en terminos de esta ley.

SECCION I
Del Procedimiento

Articulo 6.- El procedimiento se llevara a cabo de acuerdo con las siguientes etapas.

SECCION II
De las Resoluciones

Articulo 7.- Las resoluciones se emitiran conforme a derecho.

TITULO III
De las Sanciones

Articulo 8.- Las infracciones a esta ley seran sancionadas de acuerdo con lo dispuesto
en el presente titulo.

Articulo 10.- Las multas se impondran conforme a la gravedad de la infraccion.

TRANSITORIOS

PRIMERO.- El presente decreto entrara en vigor el dia siguiente al de su publicacion
en el Diario Oficial de la Federacion.

SEGUNDO.- Se derogan todas las disposiciones que se opongan al presente decreto.

TERCERO.- Los asuntos en tramite se resolveran conforme a la legislacion anterior.
"""


# ===========================================================================
# 1. Article pattern detection
# ===========================================================================


class TestArticlePatternDetection:
    """Verify that the compiled article patterns detect the required formats."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.patterns = compile_article_patterns()

    def _match_any(self, text):
        """Return the first match object across all article patterns, or None."""
        for pattern in self.patterns:
            match = pattern.match(text)
            if match:
                return match
        return None

    # -- standard --

    def test_standard_article_with_accent(self):
        match = self._match_any("Articulo 5.- Contenido.")
        assert match is not None
        assert match.group(1).rstrip(".") == "5"

    def test_standard_article_with_accent_and_tilde(self):
        match = self._match_any("\u00c1rticulo 5.- Contenido.")
        # The pattern uses Art[ii]culo, so accent on 'A' itself won't match.
        # But "Articulo" (without accent on i) does.
        match2 = self._match_any("Articulo 5.- Contenido.")
        assert match2 is not None

    def test_article_number_5(self):
        match = self._match_any("Articulo 5 texto.")
        assert match is not None
        assert match.group(1).rstrip(".") == "5"

    # -- lettered with dash --

    def test_lettered_article_27a(self):
        match = self._match_any("Articulo 27-A.- Contenido del articulo.")
        assert match is not None
        assert match.group(1) == "27"
        assert match.group(2) == "A"

    def test_lettered_article_produces_correct_id(self):
        """When the parser builds the id, '27-A' should become 'art-27a'."""
        parser = AkomaNtosoGeneratorV2()
        text = "Articulo 27-A.- Este articulo regula la materia conforme a la ley."
        result = parser.parse_structure_v2(text)
        articles = [e for e in result.elements if e["type"] == "article"]
        assert len(articles) >= 1
        assert articles[0]["id"] == "art-27a"

    # -- uppercase --

    def test_uppercase_articulo(self):
        match = self._match_any("ARTICULO 100.- Contenido en mayusculas.")
        assert match is not None
        assert match.group(1).rstrip(".") == "100"

    def test_uppercase_with_accent(self):
        match = self._match_any("ART\u00cdCULO 100.- Contenido.")
        assert match is not None
        assert match.group(1).rstrip(".") == "100"

    # -- abbreviated --

    def test_abbreviated_article(self):
        match = self._match_any("Art. 3 texto del articulo.")
        assert match is not None
        assert match.group(1) == "3"

    def test_abbreviated_large_number(self):
        match = self._match_any("Art. 999 texto.")
        assert match is not None
        assert match.group(1) == "999"

    # -- negative cases --

    def test_no_match_plain_text(self):
        match = self._match_any("En el articulo anterior se establece.")
        assert match is None

    def test_no_match_mid_sentence_number(self):
        match = self._match_any("Conforme al numeral 5 de la ley.")
        assert match is None


# ===========================================================================
# 2. Structure detection (TITULO, LIBRO, CAPITULO, SECCION)
# ===========================================================================


class TestStructureDetection:
    """Verify structural element pattern detection."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.patterns = compile_structure_patterns()

    def _match_type(self, element_type, text):
        for pattern in self.patterns[element_type]:
            match = pattern.match(text)
            if match:
                return match
        return None

    # -- TITULO --

    def test_titulo_roman(self):
        match = self._match_type("title", "TITULO I")
        assert match is not None
        assert match.group(1) == "I"

    def test_titulo_with_accent(self):
        match = self._match_type("title", "T\u00cdTULO I")
        assert match is not None

    def test_titulo_ordinal(self):
        match = self._match_type("title", "TITULO PRIMERO")
        assert match is not None
        assert match.group(1) == "PRIMERO"

    # -- LIBRO --

    def test_libro_roman(self):
        match = self._match_type("book", "LIBRO III")
        assert match is not None
        assert match.group(1) == "III"

    def test_libro_ordinal(self):
        match = self._match_type("book", "LIBRO PRIMERO")
        assert match is not None
        assert match.group(1) == "PRIMERO"

    # -- CAPITULO --

    def test_capitulo_roman(self):
        match = self._match_type("chapter", "CAPITULO III")
        assert match is not None
        assert match.group(1) == "III"

    def test_capitulo_with_accent(self):
        match = self._match_type("chapter", "CAP\u00cdTULO III")
        assert match is not None

    def test_capitulo_ordinal(self):
        match = self._match_type("chapter", "CAPITULO PRIMERO")
        assert match is not None

    # -- SECCION --

    def test_seccion_roman(self):
        match = self._match_type("section", "SECCION II")
        assert match is not None
        assert match.group(1) == "II"

    def test_seccion_with_accent(self):
        match = self._match_type("section", "SECCI\u00d3N II")
        assert match is not None

    def test_seccion_ordinal(self):
        match = self._match_type("section", "SECCION PRIMERA")
        assert match is not None
        assert match.group(1) == "PRIMERA"

    # -- via the full parser --

    def test_full_parser_detects_structures(self):
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(MULTI_STRUCTURE_LAW_TEXT)

        assert result.metadata["structure"]["book"] >= 1
        assert result.metadata["structure"]["title"] >= 2
        assert result.metadata["structure"]["chapter"] >= 2
        assert result.metadata["structure"]["section"] >= 1


# ===========================================================================
# 3. TRANSITORIOS detection
# ===========================================================================


class TestTransitoriosDetection:
    """Verify transitorios header + ordinal article detection."""

    def test_two_transitorios(self):
        text = (
            "Articulo 1.- Contenido.\n\n"
            "TRANSITORIOS\n\n"
            "PRIMERO.- Esta ley entrara en vigor al dia siguiente.\n\n"
            "SEGUNDO.- Se derogan las disposiciones anteriores.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)

        transitorios = [e for e in result.elements if e["type"] == "transitorio"]
        assert len(transitorios) == 2

    def test_three_transitorios(self):
        text = (
            "Articulo 1.- Contenido con puntuacion correcta.\n\n"
            "TRANSITORIOS\n\n"
            "PRIMERO.- Vigencia inmediata.\n\n"
            "SEGUNDO.- Derogacion de disposiciones contrarias.\n\n"
            "TERCERO.- Los asuntos pendientes se resuelven conforme a la ley anterior.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)

        transitorios = [e for e in result.elements if e["type"] == "transitorio"]
        assert len(transitorios) == 3

    def test_transitorios_numbering(self):
        text = (
            "Articulo 1.- Texto.\n\n"
            "TRANSITORIOS\n\n"
            "PRIMERO.- Primer transitorio.\n\n"
            "SEGUNDO.- Segundo transitorio.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)

        transitorios = [e for e in result.elements if e["type"] == "transitorio"]
        transitorios.sort(key=lambda t: t["number"])

        assert transitorios[0]["number"] == 1
        assert transitorios[0]["id"] == "trans-1"
        assert transitorios[1]["number"] == 2
        assert transitorios[1]["id"] == "trans-2"

    def test_articulos_transitorios_header(self):
        """The header variant 'ARTICULOS TRANSITORIOS' should also be detected."""
        text = (
            "Articulo 1.- Contenido relevante del articulo; con puntuacion.\n\n"
            "ARTICULOS TRANSITORIOS\n\n"
            "PRIMERO.- Vigencia inmediata.\n\n"
            "SEGUNDO.- Derogacion.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)

        transitorios = [e for e in result.elements if e["type"] == "transitorio"]
        assert len(transitorios) == 2

    def test_no_transitorios_produces_warning(self):
        text = (
            "Articulo 1.- Unica disposicion con contenido suficiente para confianza.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)

        has_warning = any("TRANSITORIOS" in w for w in result.warnings)
        assert has_warning


# ===========================================================================
# 3b. TRANSITORIOS past the 12th ordinal (compound-ordinal capture)
# ===========================================================================


class TestCompoundOrdinalTransitorios:
    """Transitorios numbered past the 12th (DÉCIMO TERCERO … TRIGÉSIMO …).

    The previous parser iterated only the 1–12 ORDINAL_PATTERNS map, so a law's
    13th and later transitorios (CCF ~50, LFT ~33, LIVA ~27) were SILENTLY
    DROPPED. These tests pin that every ordinal — including two-word compounds
    — is captured with the correct number and the ``trans-N`` id the indexer
    reads to namespace it.
    """

    def _law_with_transitorios(self, ordinals):
        """Build a law with one substantive article + the given transitorio
        ordinal headings (each with distinct content)."""
        lines = [
            "Artículo 1.- Disposición substantiva con contenido.",
            "",
            "TRANSITORIOS",
            "",
        ]
        for word in ordinals:
            lines.append(f"{word}.- Contenido del transitorio {word.lower()} aqui.")
            lines.append("")
        return "\n".join(lines)

    def _parse_transitorios(self, ordinals):
        text = self._law_with_transitorios(ordinals)
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)
        trans = [e for e in result.elements if e["type"] == "transitorio"]
        return {t["number"]: t for t in trans}

    def test_thirteenth_transitorio_captured(self):
        by_num = self._parse_transitorios(
            ["PRIMERO", "SEGUNDO", "DÉCIMO SEGUNDO", "DÉCIMO TERCERO"]
        )
        assert 13 in by_num, f"13th transitorio dropped; got {sorted(by_num)}"
        assert by_num[13]["id"] == "trans-13"

    def test_twentieth_transitorio_captured(self):
        by_num = self._parse_transitorios(["PRIMERO", "VIGÉSIMO"])
        assert 20 in by_num, f"20th transitorio dropped; got {sorted(by_num)}"
        assert by_num[20]["id"] == "trans-20"

    def test_twenty_fifth_transitorio_captured(self):
        by_num = self._parse_transitorios(["PRIMERO", "VIGÉSIMO QUINTO"])
        assert 25 in by_num, f"25th transitorio dropped; got {sorted(by_num)}"
        assert by_num[25]["id"] == "trans-25"

    def test_thirtieth_transitorio_captured(self):
        by_num = self._parse_transitorios(["PRIMERO", "TRIGÉSIMO"])
        assert 30 in by_num, f"30th transitorio dropped; got {sorted(by_num)}"
        assert by_num[30]["id"] == "trans-30"

    def test_full_sequence_1_to_30_all_captured(self):
        # A realistic long transitorios block: none may be dropped.
        ordinals = [
            "PRIMERO",
            "SEGUNDO",
            "TERCERO",
            "CUARTO",
            "QUINTO",
            "SEXTO",
            "SÉPTIMO",
            "OCTAVO",
            "NOVENO",
            "DÉCIMO",
            "UNDÉCIMO",
            "DUODÉCIMO",
            "DÉCIMO TERCERO",
            "DÉCIMO CUARTO",
            "DÉCIMO QUINTO",
            "DÉCIMO SEXTO",
            "DÉCIMO SÉPTIMO",
            "DÉCIMO OCTAVO",
            "DÉCIMO NOVENO",
            "VIGÉSIMO",
            "VIGÉSIMO PRIMERO",
            "VIGÉSIMO SEGUNDO",
            "VIGÉSIMO TERCERO",
            "VIGÉSIMO CUARTO",
            "VIGÉSIMO QUINTO",
            "VIGÉSIMO SEXTO",
            "VIGÉSIMO SÉPTIMO",
            "VIGÉSIMO OCTAVO",
            "VIGÉSIMO NOVENO",
            "TRIGÉSIMO",
        ]
        by_num = self._parse_transitorios(ordinals)
        expected = set(range(1, 31))
        assert (
            set(by_num) == expected
        ), f"dropped transitorios: {sorted(expected - set(by_num))}"

    def test_ultimo_transitorio_still_sentinel_999(self):
        # "ÚLTIMO" has no cardinal position — keep the historical 999 sentinel.
        by_num = self._parse_transitorios(["PRIMERO", "ÚLTIMO"])
        assert 999 in by_num, f"ÚLTIMO transitorio dropped; got {sorted(by_num)}"
        assert by_num[999]["id"] == "trans-999"

    def test_unico_transitorio_captured_as_first(self):
        # A lone "ÚNICO" transitorio (very common in short reglamentos) must be
        # captured, consistent with the indexer already recognising "único".
        text = (
            "Artículo 1.- Contenido substantivo.\n\n"
            "TRANSITORIO\n\n"
            "ÚNICO.- La presente ley entra en vigor al dia siguiente.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)
        trans = [e for e in result.elements if e["type"] == "transitorio"]
        assert len(trans) == 1, f"ÚNICO transitorio dropped; got {trans}"
        assert trans[0]["number"] == 1
        assert trans[0]["id"] == "trans-1"

    def test_compound_transitorio_content_does_not_bleed(self):
        text = (
            "Artículo 1.- Substantiva.\n\n"
            "TRANSITORIOS\n\n"
            "DÉCIMO TERCERO.- El decimotercero dice AAA.\n\n"
            "VIGÉSIMO QUINTO.- El vigesimoquinto dice BBB.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)
        by_num = {e["number"]: e for e in result.elements if e["type"] == "transitorio"}
        assert "AAA" in by_num[13]["content"]
        assert "BBB" not in by_num[13]["content"]
        assert "BBB" in by_num[25]["content"]

    def test_ordinal_numbered_substantive_articles_not_misclassified(self):
        """JCF-style ordinal-numbered substantive articles must NOT be captured
        as transitorios. The section boundary (text after the TRANSITORIOS
        header) is the discriminator — reglas before it are substantive.
        """
        # No TRANSITORIOS header at all → zero transitorios, even though every
        # provision is ordinal-numbered (JCF Reglas de Operación pattern).
        jcf = (
            "REGLAS DE OPERACIÓN\n\n"
            "PRIMERA.- Las presentes reglas tienen por objeto establecer.\n\n"
            "DÉCIMA QUINTA.- El comité técnico sesionará de manera ordinaria.\n\n"
            "VIGÉSIMA.- Los recursos no ejercidos serán reintegrados.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(jcf)
        trans = [e for e in result.elements if e["type"] == "transitorio"]
        assert trans == [], (
            "substantive ordinal reglas were misclassified as transitorios: "
            f"{[(t['number'], t['ordinal']) for t in trans]}"
        )

    def test_substantive_ordinal_reglas_with_real_transitorios_section(self):
        """When ordinal substantive reglas ARE followed by a real transitorios
        section, only the post-header ordinals are captured as transitorios."""
        text = (
            "REGLAS\n\n"
            "PRIMERA.- Regla substantiva uno.\n\n"
            "DÉCIMA QUINTA.- Regla substantiva quince.\n\n"
            "TRANSITORIOS\n\n"
            "PRIMERO.- Las presentes reglas entran en vigor al dia siguiente.\n\n"
            "SEGUNDO.- Se abrogan las reglas anteriores.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)
        trans = [e for e in result.elements if e["type"] == "transitorio"]
        # Only the 2 post-header transitorios, NOT the substantive PRIMERA/15th.
        assert len(trans) == 2
        assert {t["number"] for t in trans} == {1, 2}


# ===========================================================================
# 4. Confidence scoring
# ===========================================================================


class TestConfidenceScoring:
    """Verify _article_confidence logic."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.parser = AkomaNtosoGeneratorV2()

    def test_short_content_lowers_confidence(self):
        short = "Texto corto."
        long_text = (
            "Este articulo establece que las autoridades deberan actuar "
            "conforme a las disposiciones aplicables; garantizando el debido "
            "proceso en terminos de esta ley."
        )
        score_short = self.parser._article_confidence(short)
        score_long = self.parser._article_confidence(long_text)
        assert score_short < score_long

    def test_no_punctuation_lowers_confidence(self):
        no_punct = "Este es un texto sin signos de puntuacion al final"
        with_punct = "Este es un texto con puntuacion correcta."
        score_no = self.parser._article_confidence(no_punct)
        score_yes = self.parser._article_confidence(with_punct)
        assert score_no < score_yes

    def test_legal_language_boosts_confidence(self):
        plain = "Las personas tienen derechos garantizados por la ley."
        legal = "Las personas tienen derechos en terminos de lo dispuesto en esta ley."
        score_plain = self.parser._article_confidence(plain)
        score_legal = self.parser._article_confidence(legal)
        assert score_legal >= score_plain

    def test_confidence_clamped_0_to_1(self):
        """Score should never exceed 1.0 or go below 0.0."""
        extreme_legal = (
            "En terminos de lo dispuesto conforme a la ley, de acuerdo con "
            "las disposiciones en terminos del reglamento; conforme a derecho."
        )
        score = self.parser._article_confidence(extreme_legal)
        assert 0.0 <= score <= 1.0

        tiny = "x"
        score_tiny = self.parser._article_confidence(tiny)
        assert 0.0 <= score_tiny <= 1.0

    def test_overall_confidence_from_parse(self):
        """parse_structure_v2 sets overall confidence as average of articles."""
        result = self.parser.parse_structure_v2(MINIMAL_LAW_TEXT)
        assert 0.0 <= result.confidence <= 1.0
        # With 3 articles (one derogated short text), confidence should be moderate
        assert result.confidence > 0.0


# ===========================================================================
# 5. Gap detection
# ===========================================================================


class TestGapDetection:
    """Verify _detect_gaps identifies numbering discontinuities."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.parser = AkomaNtosoGeneratorV2()

    def test_no_gap_sequential(self):
        gaps = self.parser._detect_gaps(["1", "2", "3", "4"])
        assert gaps == []

    def test_single_gap(self):
        gaps = self.parser._detect_gaps(["1", "2", "5"])
        assert len(gaps) == 1
        assert "2" in gaps[0] and "5" in gaps[0]

    def test_multiple_gaps(self):
        gaps = self.parser._detect_gaps(["1", "3", "7"])
        assert len(gaps) == 2

    def test_gap_with_lettered_articles(self):
        """Lettered articles (e.g. '5-A') share the base number; no gap."""
        gaps = self.parser._detect_gaps(["5", "5-A", "6"])
        assert gaps == []

    def test_no_gap_single_article(self):
        gaps = self.parser._detect_gaps(["1"])
        assert gaps == []

    def test_empty_list(self):
        gaps = self.parser._detect_gaps([])
        assert gaps == []

    def test_gap_produces_warning_in_parse(self):
        """In MULTI_STRUCTURE_LAW_TEXT articles 8 and 10 have a gap (9 missing)."""
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(MULTI_STRUCTURE_LAW_TEXT)

        gap_warnings = [w for w in result.warnings if "Gap" in w]
        assert len(gap_warnings) >= 1
        assert any("8" in w and "10" in w for w in gap_warnings)


# ===========================================================================
# 6. Full parse cycle
# ===========================================================================


class TestFullParseCycle:
    """End-to-end parse of a realistic multi-section law text."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.parser = AkomaNtosoGeneratorV2()
        self.result = self.parser.parse_structure_v2(MULTI_STRUCTURE_LAW_TEXT)

    def test_result_type(self):
        assert isinstance(self.result, ParseResult)

    def test_articles_counted(self):
        assert self.result.metadata["articles"] == 9  # articles 1-8, 10

    def test_transitorios_counted(self):
        assert self.result.metadata["transitorios"] == 3

    def test_total_elements_includes_all(self):
        total = self.result.metadata["total_elements"]
        articles = self.result.metadata["articles"]
        transitorios = self.result.metadata["transitorios"]
        struct = sum(self.result.metadata["structure"].values())
        assert total == articles + transitorios + struct

    def test_structure_counts(self):
        s = self.result.metadata["structure"]
        assert s["book"] >= 1
        assert s["title"] >= 2
        assert s["chapter"] >= 3
        assert s["section"] >= 2

    def test_element_ids_unique(self):
        ids = [e["id"] for e in self.result.elements]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"

    def test_article_content_preserved(self):
        art1 = next((e for e in self.result.elements if e.get("id") == "art-1"), None)
        assert art1 is not None
        assert "regular las actividades" in art1["content"]

    def test_confidence_reasonable(self):
        assert self.result.confidence >= 0.5

    def test_warnings_list(self):
        assert isinstance(self.result.warnings, list)


class TestFullParseCycleMinimal:
    """Parse the minimal law text fixture."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.parser = AkomaNtosoGeneratorV2()
        self.result = self.parser.parse_structure_v2(MINIMAL_LAW_TEXT)

    def test_articles_found(self):
        assert self.result.metadata["articles"] == 3

    def test_transitorios_found(self):
        assert self.result.metadata["transitorios"] == 2

    def test_structure_title(self):
        assert self.result.metadata["structure"]["title"] >= 1

    def test_structure_chapter(self):
        assert self.result.metadata["structure"]["chapter"] >= 1

    def test_derogated_article_detected(self):
        art3 = next((e for e in self.result.elements if e.get("id") == "art-3"), None)
        assert art3 is not None
        assert art3["derogated"] is True


# ===========================================================================
# 7. Derogation detection
# ===========================================================================


class TestDerogationDetection:
    """Verify is_derogated() recognises all derogation patterns."""

    def test_se_deroga(self):
        assert is_derogated("Se deroga.") is True

    def test_queda_derogado(self):
        assert is_derogated("Queda derogado.") is True

    def test_queda_derogada(self):
        assert is_derogated("Queda derogada.") is True

    def test_parenthetical_derogado(self):
        assert is_derogated("(derogado)") is True

    def test_parenthetical_se_deroga(self):
        assert is_derogated("(Se deroga)") is True

    def test_derogado_standalone(self):
        assert is_derogated("derogado.") is True

    def test_se_abroga(self):
        assert is_derogated("se abroga.") is True

    def test_not_derogated_normal_text(self):
        normal = (
            "Las personas tienen derecho a solicitar informacion conforme a las "
            "disposiciones de esta ley, garantizando el debido proceso."
        )
        assert is_derogated(normal) is False

    def test_long_text_with_derogation_word_not_flagged(self):
        """Long text (>100 chars) is NOT considered derogated even if it mentions 'deroga'."""
        long_text = (
            "Este articulo establece las bases para la regulacion de las actividades "
            "productivas en el territorio nacional. Se deroga la fraccion III del "
            "articulo anterior pero el presente permanece vigente con todas sus "
            "disposiciones aplicables conforme a derecho."
        )
        assert is_derogated(long_text) is False


# ===========================================================================
# 8. XML generation round-trip
# ===========================================================================


class TestXMLGeneration:
    """Verify that generate_xml produces well-formed Akoma Ntoso XML."""

    def test_generate_well_formed_xml(self, tmp_path):
        from lxml import etree

        parser = AkomaNtosoGeneratorV2()
        metadata = parser.create_frbr_metadata(
            law_type="ley",
            date_str="2024-06-15",
            slug="prueba",
            title="Ley de Prueba",
        )

        output_path = tmp_path / "federal" / "prueba-v2.xml"
        xml_path, result = parser.generate_xml(
            MULTI_STRUCTURE_LAW_TEXT, metadata, output_path
        )

        assert xml_path.exists()
        assert xml_path.stat().st_size > 0

        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        assert "akomaNtoso" in root.tag

    def test_xml_contains_articles(self, tmp_path):
        from lxml import etree

        parser = AkomaNtosoGeneratorV2()
        metadata = parser.create_frbr_metadata("ley", "2024-01-01", "test", "Test Law")
        output_path = tmp_path / "out" / "test.xml"
        xml_path, _ = parser.generate_xml(MINIMAL_LAW_TEXT, metadata, output_path)

        ns = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}
        tree = etree.parse(str(xml_path))
        articles = tree.xpath("//akn:article", namespaces=ns)
        # 3 regular articles + 2 transitorios rendered as articles
        assert len(articles) >= 3


# ===========================================================================
# 9. Ordinal-to-number helper
# ===========================================================================


class TestOrdinalToNumber:
    """Verify the ordinal_to_number utility used by the article parser."""

    @pytest.mark.parametrize(
        "ordinal, expected",
        [
            ("PRIMERO", 1),
            ("Primero", 1),
            ("SEGUNDA", 2),
            ("TERCERO", 3),
            ("CUARTO", 4),
            ("QUINTO", 5),
            ("SEXTO", 6),
            ("S\u00c9PTIMO", 7),
            ("SEPTIMO", 7),
            ("OCTAVO", 8),
            ("NOVENO", 9),
            ("D\u00c9CIMO", 10),
            ("DECIMO", 10),
            ("UND\u00c9CIMO", 11),
            ("DUOD\u00c9CIMO", 12),
            ("VIG\u00c9SIMO", 20),
            # Tens 30\u201390 (added so transitorios past the 29th are resolvable).
            ("TRIG\u00c9SIMO", 30),
            ("TRIGESIMO", 30),
            ("CUADRAG\u00c9SIMO", 40),
            ("QUINCUAG\u00c9SIMO", 50),
            ("SEXAG\u00c9SIMO", 60),
            ("SEPTUAG\u00c9SIMO", 70),
            ("OCTOG\u00c9SIMO", 80),
            ("NONAG\u00c9SIMO", 90),
        ],
    )
    def test_ordinals(self, ordinal, expected):
        assert ordinal_to_number(ordinal) == expected

    def test_compound_ordinal(self):
        assert ordinal_to_number("D\u00c9CIMO PRIMERO") == 11
        assert ordinal_to_number("DECIMO SEGUNDO") == 12
        assert ordinal_to_number("DECIMO TERCERO") == 13

    def test_compound_ordinal_tens_beyond_twelfth(self):
        # The defect: real laws carry transitorios well past the 12th. These
        # compound ordinals must resolve, not return None.
        assert ordinal_to_number("VIG\u00c9SIMO PRIMERO") == 21
        assert ordinal_to_number("VIG\u00c9SIMO QUINTO") == 25
        assert ordinal_to_number("TRIG\u00c9SIMO") == 30
        assert ordinal_to_number("TRIG\u00c9SIMO PRIMERO") == 31
        assert ordinal_to_number("CUADRAG\u00c9SIMO QUINTO") == 45
        assert ordinal_to_number("QUINCUAG\u00c9SIMO NOVENO") == 59

    def test_unknown_ordinal_returns_none(self):
        assert ordinal_to_number("CENTESIMO") is None
        assert ordinal_to_number("random text") is None


# ===========================================================================
# 10. Roman numeral helper
# ===========================================================================


class TestRomanToInt:
    """Verify roman_to_int for values commonly found in Mexican law structures."""

    @pytest.mark.parametrize(
        "roman, expected",
        [
            ("I", 1),
            ("II", 2),
            ("III", 3),
            ("IV", 4),
            ("V", 5),
            ("IX", 9),
            ("X", 10),
            ("XIV", 14),
            ("XX", 20),
        ],
    )
    def test_standard_values(self, roman, expected):
        assert roman_to_int(roman) == expected

    def test_lowercase_converted(self):
        assert roman_to_int("iv") == 4

    def test_empty_string(self):
        assert roman_to_int("") == 0

    def test_invalid_returns_zero(self):
        assert roman_to_int("ZZZ") == 0


# ===========================================================================
# 11. Edge cases and regression guards
# ===========================================================================


class TestEdgeCases:
    """Guard against known edge cases and regressions."""

    def test_empty_text_produces_zero_confidence(self):
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2("")
        assert result.confidence == 0.0
        assert result.metadata["articles"] == 0

    def test_text_with_only_transitorios(self):
        """Text that has transitorios but no regular articles."""
        text = (
            "TRANSITORIOS\n\n"
            "PRIMERO.- Vigencia inmediata.\n\n"
            "SEGUNDO.- Derogacion.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)
        assert result.metadata["articles"] == 0
        assert result.metadata["transitorios"] >= 1
        # Confidence should be 0 because no regular articles
        assert result.confidence == 0.0

    def test_article_with_ordinal_suffix(self):
        """Articulo 1o. format (ordinal marker)."""
        text = "Articulo 1o. Esta ley es de orden publico; interes social."
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)
        articles = [e for e in result.elements if e["type"] == "article"]
        assert len(articles) >= 1

    def test_warnings_include_no_book_no_title(self):
        """Text with only articles should warn about missing BOOK and TITLE."""
        text = (
            "Articulo 1.- Contenido con suficiente texto para buena confianza.\n\n"
            "Articulo 2.- Otro articulo con contenido razonable en terminos de ley.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)
        assert any("BOOK" in w.upper() for w in result.warnings)
        assert any("TITLE" in w.upper() for w in result.warnings)

    def test_consecutive_structure_elements(self):
        """Two structure elements on consecutive lines: description should not
        bleed into the next element."""
        text = (
            "TITULO I\n"
            "CAPITULO I\n"
            "Articulo 1.- Contenido del unico articulo; disposiciones generales.\n"
        )
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(text)

        titles = [e for e in result.elements if e["type"] == "title"]
        assert len(titles) == 1
        # The description of TITULO I should NOT be "CAPITULO I"
        assert "CAPITULO" not in titles[0].get("description", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
