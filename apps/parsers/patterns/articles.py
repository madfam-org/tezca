"""
Article patterns for Mexican laws.
Handles standard articles, lettered articles (27-A), ordinal articles, and other variations.
"""

import re
from typing import List, Optional, Pattern, Tuple


def compile_article_patterns() -> List[Pattern]:
    """
    Compile list of regex patterns for article detection.

    Patterns ordered from most specific to least specific so that
    ``_try_patterns`` returns the best match first.

    Returns:
        List of compiled regex objects
    """
    patterns = [
        # Bis with optional number: Artículo 5 Bis, Artículo 5o. Bis 1
        r"^Art[íi]culo\s+(\d+[o]?\.?)\s+(Bis\s*\d*)",
        # Lettered with dash: Artículo 27-A, Artículo 45-A.
        r"^Art[íi]culo\s+(\d+)-([A-Z])\.?",
        # Standard: Artículo 5, Artículo 5., Artículo 1o.-, Artículo 5o
        r"^Art[íi]culo\s+(\d+[o]?\.?)",
        # Uppercase Bis: ARTICULO 5 Bis
        r"^ART[ÍI]CULO\s+(\d+[o]?\.?)\s+(Bis\s*\d*)",
        # Uppercase: ARTICULO 5
        r"^ART[ÍI]CULO\s+(\d+[o]?\.?)",
        # Abbreviated: Art. 5
        r"^Art\.\s+(\d+)",
    ]

    return [re.compile(p, re.MULTILINE) for p in patterns]


def compile_ordinal_article_patterns() -> List[Pattern]:
    """
    Compile ordinal article patterns for municipal regulations.

    Separated from main article patterns because ordinals (Primero, Segundo)
    collide with TRANSITORIOS entries in federal/state laws.
    """
    patterns = [
        r"^(PRIMER[OA]|Primer[oa])\.?\s*-?\s*",
        r"^(SEGUND[OA]|Segund[oa])\.?\s*-?\s*",
        r"^(TERCER[OA]|Tercer[oa])\.?\s*-?\s*",
        r"^(CUART[OA]|Cuart[oa])\.?\s*-?\s*",
        r"^(QUINT[OA]|Quint[oa])\.?\s*-?\s*",
        r"^(SEXT[OA]|Sext[oa])\.?\s*-?\s*",
        r"^(S[ÉE]PTIM[OA]|S[ée]ptim[oa])\.?\s*-?\s*",
        r"^(OCTAV[OA]|Octav[oa])\.?\s*-?\s*",
        r"^(NOVEN[OA]|Noven[oa])\.?\s*-?\s*",
        r"^(D[ÉE]CIM[OA]|D[ée]cim[oa])\.?\s*-?\s*",
        r"^(UND[ÉE]CIM[OA]|Und[ée]cim[oa])\.?\s*-?\s*",
        r"^(DUOD[ÉE]CIM[OA]|Duod[ée]cim[oa])\.?\s*-?\s*",
        r"^(DECIM[OA]\s+PRIMER[OA]|D[ée]cim[oa]\s+primer[oa])\.?\s*-?\s*",
        r"^(DECIM[OA]\s+SEGUND[OA]|D[ée]cim[oa]\s+segund[oa])\.?\s*-?\s*",
        r"^(DECIM[OA]\s+TERCER[OA]|D[ée]cim[oa]\s+tercer[oa])\.?\s*-?\s*",
        r"^(VIGESIM[OA]|Vig[ée]sim[oa])\.?\s*-?\s*",
    ]

    return [re.compile(p, re.MULTILINE) for p in patterns]


# Mapping from Spanish ordinals to numbers
ORDINAL_TO_NUMBER = {
    "PRIMERO": 1,
    "PRIMERA": 1,
    "Primero": 1,
    "Primera": 1,
    "primero": 1,
    "primera": 1,
    "SEGUNDO": 2,
    "SEGUNDA": 2,
    "Segundo": 2,
    "Segunda": 2,
    "segundo": 2,
    "segunda": 2,
    "TERCERO": 3,
    "TERCERA": 3,
    "Tercero": 3,
    "Tercera": 3,
    "tercero": 3,
    "tercera": 3,
    "CUARTO": 4,
    "CUARTA": 4,
    "Cuarto": 4,
    "Cuarta": 4,
    "cuarto": 4,
    "cuarta": 4,
    "QUINTO": 5,
    "QUINTA": 5,
    "Quinto": 5,
    "Quinta": 5,
    "quinto": 5,
    "quinta": 5,
    "SEXTO": 6,
    "SEXTA": 6,
    "Sexto": 6,
    "Sexta": 6,
    "sexto": 6,
    "sexta": 6,
    "SÉPTIMO": 7,
    "SÉPTIMA": 7,
    "Séptimo": 7,
    "Séptima": 7,
    "SEPTIMO": 7,
    "SEPTIMA": 7,
    "Septimo": 7,
    "Septima": 7,
    "séptimo": 7,
    "séptima": 7,
    "OCTAVO": 8,
    "OCTAVA": 8,
    "Octavo": 8,
    "Octava": 8,
    "octavo": 8,
    "octava": 8,
    "NOVENO": 9,
    "NOVENA": 9,
    "Noveno": 9,
    "Novena": 9,
    "noveno": 9,
    "novena": 9,
    "DÉCIMO": 10,
    "DÉCIMA": 10,
    "Décimo": 10,
    "Décima": 10,
    "DECIMO": 10,
    "DECIMA": 10,
    "Decimo": 10,
    "Decima": 10,
    "décimo": 10,
    "décima": 10,
    "UNDÉCIMO": 11,
    "UNDÉCIMA": 11,
    "Undécimo": 11,
    "Undécima": 11,
    "UNDECIMO": 11,
    "UNDECIMA": 11,
    "Undecimo": 11,
    "Undecima": 11,
    "DUODÉCIMO": 12,
    "DUODÉCIMA": 12,
    "Duodécimo": 12,
    "Duodécima": 12,
    "DUODECIMO": 12,
    "DUODECIMA": 12,
    "Duodecimo": 12,
    "Duodecima": 12,
    "VIGÉSIMO": 20,
    "VIGÉSIMA": 20,
    "Vigésimo": 20,
    "Vigésima": 20,
    "VIGESIMO": 20,
    "VIGESIMA": 20,
    "Vigesimo": 20,
    "Vigesima": 20,
    # Tens 30–90. Real codes carry long transitorio blocks (CCF ~50, LFT ~33,
    # LIVA ~27); without these the compound parser caps at 29 and every higher
    # transitorio is silently dropped. The compound handler in
    # ordinal_to_number() combines these with a unit (e.g. TRIGÉSIMO PRIMERO=31).
    "TRIGÉSIMO": 30,
    "TRIGÉSIMA": 30,
    "Trigésimo": 30,
    "Trigésima": 30,
    "TRIGESIMO": 30,
    "TRIGESIMA": 30,
    "Trigesimo": 30,
    "Trigesima": 30,
    "CUADRAGÉSIMO": 40,
    "CUADRAGÉSIMA": 40,
    "Cuadragésimo": 40,
    "Cuadragésima": 40,
    "CUADRAGESIMO": 40,
    "CUADRAGESIMA": 40,
    "Cuadragesimo": 40,
    "Cuadragesima": 40,
    "QUINCUAGÉSIMO": 50,
    "QUINCUAGÉSIMA": 50,
    "Quincuagésimo": 50,
    "Quincuagésima": 50,
    "QUINCUAGESIMO": 50,
    "QUINCUAGESIMA": 50,
    "Quincuagesimo": 50,
    "Quincuagesima": 50,
    "SEXAGÉSIMO": 60,
    "SEXAGÉSIMA": 60,
    "Sexagésimo": 60,
    "Sexagésima": 60,
    "SEXAGESIMO": 60,
    "SEXAGESIMA": 60,
    "Sexagesimo": 60,
    "Sexagesima": 60,
    "SEPTUAGÉSIMO": 70,
    "SEPTUAGÉSIMA": 70,
    "Septuagésimo": 70,
    "Septuagésima": 70,
    "SEPTUAGESIMO": 70,
    "SEPTUAGESIMA": 70,
    "Septuagesimo": 70,
    "Septuagesima": 70,
    "OCTOGÉSIMO": 80,
    "OCTOGÉSIMA": 80,
    "Octogésimo": 80,
    "Octogésima": 80,
    "OCTOGESIMO": 80,
    "OCTOGESIMA": 80,
    "Octogesimo": 80,
    "Octogesima": 80,
    "NONAGÉSIMO": 90,
    "NONAGÉSIMA": 90,
    "Nonagésimo": 90,
    "Nonagésima": 90,
    "NONAGESIMO": 90,
    "NONAGESIMA": 90,
    "Nonagesimo": 90,
    "Nonagesima": 90,
}


def ordinal_to_number(ordinal: str) -> Optional[int]:
    """
    Convert Spanish ordinal (e.g., 'Primero', 'SEGUNDO') to number.

    Args:
        ordinal: Spanish ordinal word

    Returns:
        Number if found, None otherwise
    """
    # Clean up the ordinal
    clean = ordinal.strip().rstrip(".-")

    # Direct lookup
    if clean in ORDINAL_TO_NUMBER:
        return ORDINAL_TO_NUMBER[clean]

    # Handle compound ordinals like "DÉCIMO PRIMERO"
    parts = clean.split()
    if len(parts) == 2:
        base = ORDINAL_TO_NUMBER.get(parts[0], 0)
        unit = ORDINAL_TO_NUMBER.get(parts[1], 0)
        if base and unit:
            return base + unit

    return None


# Derogation patterns
DEROGATION_PATTERNS = [
    r"Se\s+deroga",
    r"Queda\s+derogad[oa]",
    r"\(derogad[oa]\)",
    r"\(Se\s+deroga\)",
    r"^derogad[oa]\.?$",
    r"^se\s+abroga\.?$",
]


def is_derogated(text: str) -> bool:
    """
    Check if article content indicates it is derogated.
    """
    # Check for short content that matches derogation patterns
    if len(text.strip()) < 100:
        for pattern in DEROGATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                return True

    return False
