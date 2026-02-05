"""
Metadata extraction patterns for Mexican legal documents.

Patterns for extracting reform annotations, dates, and other metadata.
"""

import re
from typing import List, Dict, Pattern, Optional
from datetime import datetime

# Reform/amendment patterns
REFORM_ACTIONS = [
    'reformad[oa]',
    'adicionad[oa]',
    'derogad[oa]',
    'abrogad[oa]',
    'modificad[oa]',
    'sustitu[íi]d[oa]',
]

# DOF date pattern: DD-MM-YYYY
DOF_DATE_PATTERN = r'(\d{2}-\d{2}-\d{4})'

# Combined reform pattern
REFORM_PATTERN = (
    r'(Art[íi]culo|Fracci[óo]n|P[áa]rrafo|Inciso|Cap[íi]tulo|T[íi]tulo)\s+'
    f'({"|".join(REFORM_ACTIONS)})\s+'
    f'DOF\s+{DOF_DATE_PATTERN}'
)

def compile_reform_pattern() -> Pattern:
    """Compile reform metadata pattern."""
    return re.compile(REFORM_PATTERN, re.IGNORECASE)


def extract_reforms(text: str) -> tuple[str, List[Dict]]:
    """
    Extract reform metadata from text.
    
    Returns:
        (cleaned_text, reforms)
        - cleaned_text: Text with reform annotations removed
        - reforms: List of reform metadata dicts
    """
    pattern = compile_reform_pattern()
    reforms = []
    
    for match in pattern.finditer(text):
        reforms.append({
            'element': match.group(1),      # Artículo, Fracción, etc.
            'action': match.group(2),       # reformada, adicionada, etc.
            'dof_date': match.group(3),     # DD-MM-YYYY
            'full_text': match.group(0)
        })
    
    # Remove reform annotations from content
    cleaned_text = pattern.sub('', text)
    
    return cleaned_text, reforms


def parse_dof_date(date_str: str) -> datetime:
    """
    Parse DOF date string to datetime.
    
    Args:
        date_str: Date in DD-MM-YYYY format
    
    Returns:
        datetime object
    """
    return datetime.strptime(date_str, '%d-%m-%Y')


# Effective date patterns
EFFECTIVE_DATE_PATTERNS = [
    r'entrar[áa]\s+en\s+vigor\s+(?:el\s+d[íi]a\s+)?(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
    r'entra\s+en\s+vigor\s+a\s+partir\s+del?\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
    r'vigencia\s+a\s+partir\s+del?\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
]

SPANISH_MONTHS = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def extract_effective_date(text: str) -> Optional[datetime]:
    """
    Extract law effective date from transitory articles.
    
    Returns:
        datetime object or None if not found
    """
    for pattern in EFFECTIVE_DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            day = int(match.group(1))
            month_name = match.group(2).lower()
            year = int(match.group(3))
            
            month = SPANISH_MONTHS.get(month_name)
            if month:
                return datetime(year, month, day)
    
    return None


# Citation/cross-reference patterns
CROSS_REFERENCE_PATTERNS = [
    r'en\s+t[ée]rminos\s+del?\s+art[íi]culo\s+(\d+[A-Z]?)',
    r'conforme\s+al?\s+art[íi]culo\s+(\d+[A-Z]?)',
    r'de\s+acuerdo\s+con\s+el\s+art[íi]culo\s+(\d+[A-Z]?)',
    r'lo\s+dispuesto\s+en\s+el\s+art[íi]culo\s+(\d+[A-Z]?)',
]

def extract_cross_references(text: str) -> List[Dict]:
    """
    Extract article cross-references.
    
    Returns:
        List of cross-reference dicts
    """
    references = []
    
    for pattern in CROSS_REFERENCE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            references.append({
                'article': match.group(1),
                'context': match.group(0),
                'type': 'article_reference'
            })
    
    return references
