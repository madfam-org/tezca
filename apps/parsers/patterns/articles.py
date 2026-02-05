"""
Article patterns for Mexican laws.
Handles standard articles, lettered articles (27-A), ordinal articles, and other variations.
"""

import re
from typing import List, Pattern, Tuple, Optional

def compile_article_patterns() -> List[Pattern]:
    """
    Compile list of regex patterns for article detection.
    
    Returns:
        List of compiled regex objects
    """
    patterns = [
        # Standard: Artículo 5, Artículo 5., Artículo 1o
        r'^Art[íi]culo\s+(\d+[o\.]?)',
        
        # Lettered with dash: Artículo 27-A
        r'^Art[íi]culo\s+(\d+)-([A-Z])\.?',
        
        # Lettered with space: Artículo 27 A
        r'^Art[íi]culo\s+(\d+)\s+([A-Z])\.?',
        
        # Uppercase: ARTICULO 5
        r'^ART[ÍI]CULO\s+(\d+[o\.]?)',
        
        # Abbreviated: Art. 5
        r'^Art\.\s+(\d+)',
        
        # Municipal ordinal articles: Primero., Segundo., Tercero., etc.
        r'^(PRIMER[OA]|Primer[oa])\.?\s*-?\s*',
        r'^(SEGUND[OA]|Segund[oa])\.?\s*-?\s*',
        r'^(TERCER[OA]|Tercer[oa])\.?\s*-?\s*',
        r'^(CUART[OA]|Cuart[oa])\.?\s*-?\s*',
        r'^(QUINT[OA]|Quint[oa])\.?\s*-?\s*',
        r'^(SEXT[OA]|Sext[oa])\.?\s*-?\s*',
        r'^(S[ÉE]PTIM[OA]|S[ée]ptim[oa])\.?\s*-?\s*',
        r'^(OCTAV[OA]|Octav[oa])\.?\s*-?\s*',
        r'^(NOVEN[OA]|Noven[oa])\.?\s*-?\s*',
        r'^(D[ÉE]CIM[OA]|D[ée]cim[oa])\.?\s*-?\s*',
        r'^(UND[ÉE]CIM[OA]|Und[ée]cim[oa])\.?\s*-?\s*',
        r'^(DUOD[ÉE]CIM[OA]|Duod[ée]cim[oa])\.?\s*-?\s*',
        r'^(DECIM[OA]\s+PRIMER[OA]|D[ée]cim[oa]\s+primer[oa])\.?\s*-?\s*',
        r'^(DECIM[OA]\s+SEGUND[OA]|D[ée]cim[oa]\s+segund[oa])\.?\s*-?\s*',
        r'^(DECIM[OA]\s+TERCER[OA]|D[ée]cim[oa]\s+tercer[oa])\.?\s*-?\s*',
        r'^(VIGESIM[OA]|Vig[ée]sim[oa])\.?\s*-?\s*',
    ]
    
    return [re.compile(p, re.MULTILINE) for p in patterns]


# Mapping from Spanish ordinals to numbers
ORDINAL_TO_NUMBER = {
    'PRIMERO': 1, 'PRIMERA': 1, 'Primero': 1, 'Primera': 1, 'primero': 1, 'primera': 1,
    'SEGUNDO': 2, 'SEGUNDA': 2, 'Segundo': 2, 'Segunda': 2, 'segundo': 2, 'segunda': 2,
    'TERCERO': 3, 'TERCERA': 3, 'Tercero': 3, 'Tercera': 3, 'tercero': 3, 'tercera': 3,
    'CUARTO': 4, 'CUARTA': 4, 'Cuarto': 4, 'Cuarta': 4, 'cuarto': 4, 'cuarta': 4,
    'QUINTO': 5, 'QUINTA': 5, 'Quinto': 5, 'Quinta': 5, 'quinto': 5, 'quinta': 5,
    'SEXTO': 6, 'SEXTA': 6, 'Sexto': 6, 'Sexta': 6, 'sexto': 6, 'sexta': 6,
    'SÉPTIMO': 7, 'SÉPTIMA': 7, 'Séptimo': 7, 'Séptima': 7,
    'SEPTIMO': 7, 'SEPTIMA': 7, 'Septimo': 7, 'Septima': 7, 'séptimo': 7, 'séptima': 7,
    'OCTAVO': 8, 'OCTAVA': 8, 'Octavo': 8, 'Octava': 8, 'octavo': 8, 'octava': 8,
    'NOVENO': 9, 'NOVENA': 9, 'Noveno': 9, 'Novena': 9, 'noveno': 9, 'novena': 9,
    'DÉCIMO': 10, 'DÉCIMA': 10, 'Décimo': 10, 'Décima': 10,
    'DECIMO': 10, 'DECIMA': 10, 'Decimo': 10, 'Decima': 10, 'décimo': 10, 'décima': 10,
    'UNDÉCIMO': 11, 'UNDÉCIMA': 11, 'Undécimo': 11, 'Undécima': 11,
    'UNDECIMO': 11, 'UNDECIMA': 11, 'Undecimo': 11, 'Undecima': 11,
    'DUODÉCIMO': 12, 'DUODÉCIMA': 12, 'Duodécimo': 12, 'Duodécima': 12,
    'DUODECIMO': 12, 'DUODECIMA': 12, 'Duodecimo': 12, 'Duodecima': 12,
    'VIGÉSIMO': 20, 'VIGÉSIMA': 20, 'Vigésimo': 20, 'Vigésima': 20,
    'VIGESIMO': 20, 'VIGESIMA': 20, 'Vigesimo': 20, 'Vigesima': 20,
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
    clean = ordinal.strip().rstrip('.-')
    
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
    r'Se\s+deroga',
    r'Queda\s+derogad[oa]',
    r'\(derogad[oa]\)',
    r'\(Se\s+deroga\)',
    r'^derogad[oa]\.?$',
    r'^se\s+abroga\.?$',
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
