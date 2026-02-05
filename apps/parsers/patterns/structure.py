"""
Pattern library for Mexican legal document structure.

Reusable regex patterns for parsing different structural elements.
"""

import re
from typing import List, Pattern

# Article patterns moved to articles.py


# Structure patterns (Titles, Books, Chapters)
TITLE_PATTERNS = [
    r'^T[ÍI]TULO\s+([IVX]+)',                   # TÍTULO I, II, III
    r'^T[ÍI]TULO\s+(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|SÉPTIMO|OCTAVO|NOVENO|DÉCIMO)',
    r'^Título\s+([IVX]+)',                       # Title case
]

BOOK_PATTERNS = [
    r'^LIBRO\s+([IVX]+)',                       # LIBRO I, II, III
    r'^LIBRO\s+(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO)',
]

PART_PATTERNS = [
    r'^PARTE\s+([IVX]+)',
    r'^PARTE\s+(PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA)',
]

CHAPTER_PATTERNS = [
    r'^CAP[ÍI]TULO\s+([IVX]+)',                 # CAPÍTULO I, II, III
    r'^CAP[ÍI]TULO\s+(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|SÉPTIMO|OCTAVO|NOVENO|DÉCIMO)',
    r'^Capítulo\s+([IVX]+)',                     # Title case
]

SECTION_PATTERNS = [
    r'^SECCI[ÓO]N\s+([IVX]+)',
    r'^SECCI[ÓO]N\s+(PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA)',
]

def compile_structure_patterns() -> dict:
    """Compile all structure patterns."""
    return {
        'title': [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in TITLE_PATTERNS],
        'book': [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in BOOK_PATTERNS],
        'part': [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in PART_PATTERNS],
        'chapter': [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in CHAPTER_PATTERNS],
        'section': [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in SECTION_PATTERNS],
    }


# Transitory article patterns
TRANSITORIOS_HEADER = [
    r'^\s*ART[ÍI]CULOS?\s+TRANSITORIOS?\s*$',
    r'^\s*TRANSITORIOS?\s*$',
    r'^\s*DISPOSICIONES?\s+TRANSITORIAS?\s*$',
]

ORDINAL_PATTERNS = {
    'PRIMER[OA]': 1,
    'SEGUND[OA]': 2,
    'TERCER[OA]': 3,
    'CUART[OA]': 4,
    'QUINT[OA]': 5,
    'SEXT[OA]': 6,
    'S[ÉE]PTIM[OA]': 7,
    'OCTAV[OA]': 8,
    'NOVEN[OA]': 9,
    'D[ÉE]CIM[OA]': 10,
    'UND[ÉE]CIM[OA]': 11,
    'DUOD[ÉE]CIM[OA]': 12,
    '[ÚU]LTIM[OA]': 999,  # Special case for last
}

def compile_transitorios_patterns() -> dict:
    """Compile transitory article patterns."""
    return {
        'header': [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in TRANSITORIOS_HEADER],
        'ordinals': {k: re.compile(f'^({k})\\.-', re.IGNORECASE | re.MULTILINE) 
                     for k in ORDINAL_PATTERNS.keys()}
    }


# Roman numeral conversion
ROMAN_NUMERALS = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
    'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
    'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
    'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19, 'XX': 20,
}

def roman_to_int(s: str) -> int:
    """Convert roman numeral to integer."""
    if not s:
        return 0
    s = s.upper()
    roman = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    for i in range(len(s)):
        if s[i] not in roman:
            return 0
        if i + 1 < len(s) and roman.get(s[i+1], 0) > roman[s[i]]:
            result -= roman[s[i]]
        else:
            result += roman[s[i]]
    return result


# Fraction/subdivision patterns
FRACTION_PATTERNS = [
    r'^\s*([IVX]+)\.',                          # Roman: I., II., III.
    r'^\s*([a-z])\)',                           # Lowercase letter: a), b), c)
    r'^\s*(\d+)\)',                             # Number: 1), 2), 3)
]

def compile_fraction_patterns() -> List[Pattern]:
    """Compile fraction patterns."""
    return [re.compile(p, re.MULTILINE) for p in FRACTION_PATTERNS]
