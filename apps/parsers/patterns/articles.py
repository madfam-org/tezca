"""
Article patterns for Mexican laws.
Handles standard articles, lettered articles (27-A), and other variations.
"""

import re
from typing import List, Pattern

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
    ]
    
    return [re.compile(p, re.MULTILINE) for p in patterns]


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
