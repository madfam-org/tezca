"""
Unit tests for pattern matching.
"""

import pytest
import re
import sys
from pathlib import Path

# Add apps to path

from apps.parsers.patterns.structure import (
    compile_structure_patterns,
    roman_to_int
)
from apps.parsers.patterns.articles import compile_article_patterns
from apps.parsers.patterns.metadata import (
    compile_reform_pattern,
    extract_reforms
)


class TestArticlePatterns:
    """Test article pattern matching."""
    
    def test_standard_article(self):
        """Test standard article format 'Artículo 5'."""
        patterns = compile_article_patterns()
        text = "Artículo 5.- Este es el contenido."
        
        matched = False
        for pattern in patterns:
            match = pattern.match(text)
            if match:
                assert match.group(1).rstrip('.') == "5"
                matched = True
                break
        
        assert matched, "Should match standard article format"
    
    def test_lettered_article(self):
        """Test lettered article 'Artículo 5-A'."""
        patterns = compile_article_patterns()
        text = "Artículo 5-A.- Contenido del artículo."
        
        matched = False
        for pattern in patterns:
            match = pattern.match(text)
            if match and match.lastindex >= 2:
                assert match.group(1) == "5"
                assert match.group(2) == "A"
                matched = True
                break
        
        assert matched, "Should match lettered article format"
    
    def test_uppercase_article(self):
        """Test uppercase ARTÍCULO."""
        patterns = compile_article_patterns()
        text = "ARTÍCULO 10.- Contenido en mayúsculas."
        
        matched = False
        for pattern in patterns:
            match = pattern.match(text)
            if match:
                assert match.group(1).rstrip('.') == "10"
                matched = True
                break
        
        assert matched, "Should match uppercase article"
    
    def test_article_with_number_in_text(self):
        """Test article doesn't match random numbers."""
        patterns = compile_article_patterns()
        text = "En el año 2020, se estableció que..."
        
        matched = False
        for pattern in patterns:
            if pattern.match(text):
                matched = True
                break
        
        assert not matched, "Should not match text with just numbers"


class TestStructurePatterns:
    """Test structure pattern matching."""
    
    def test_title_pattern(self):
        """Test TÍTULO pattern."""
        patterns = compile_structure_patterns()
        text = "TÍTULO PRIMERO\nDe las Disposiciones Generales"
        
        matched = False
        for pattern in patterns['title']:
            match = pattern.match(text)
            if match:
                matched = True
                break
        
        assert matched, "Should match TÍTULO pattern"
    
    def test_chapter_pattern(self):
        """Test CAPÍTULO pattern."""
        patterns = compile_structure_patterns()
        text = "CAPÍTULO I\nDisposiciones Generales"
        
        matched = False
        for pattern in patterns['chapter']:
            match = pattern.match(text)
            if match:
                matched = True
                break
        
        assert matched, "Should match CAPÍTULO pattern"
    
    def test_book_pattern(self):
        """Test LIBRO pattern."""
        patterns = compile_structure_patterns()
        text = "LIBRO PRIMERO"
        
        matched = False
        for pattern in patterns['book']:
            match = pattern.match(text)
            if match:
                matched = True
                break
        
        assert matched, "Should match LIBRO pattern"


class TestRomanNumerals:
    """Test Roman numeral conversion."""
    
    def test_basic_roman_numerals(self):
        """Test basic Roman numeral conversion."""
        assert roman_to_int("I") == 1
        assert roman_to_int("V") == 5
        assert roman_to_int("X") == 10
        assert roman_to_int("L") == 50
    
    def test_compound_roman_numerals(self):
        """Test compound Roman numerals."""
        assert roman_to_int("IV") == 4
        assert roman_to_int("IX") == 9
        assert roman_to_int("XL") == 40
        assert roman_to_int("XC") == 90
    
    def test_complex_roman_numerals(self):
        """Test complex Roman numerals."""
        assert roman_to_int("MCMXC") == 1990
        assert roman_to_int("MMXXIV") == 2024
    
    def test_invalid_roman_numeral(self):
        """Test invalid Roman numeral returns 0."""
        assert roman_to_int("ABC") == 0
        assert roman_to_int("") == 0


class TestMetadataPatterns:
    """Test metadata extraction patterns."""
    
    def test_reform_pattern_basic(self):
        """Test basic reform pattern."""
        pattern = compile_reform_pattern()
        text = "Artículo reformado DOF 13-03-2025"
        
        match = pattern.search(text)
        assert match is not None
        assert "reformado" in match.group(0).lower()
    
    def test_extract_reforms(self):
        """Test reform extraction."""
        text = """
        Artículo 5.- Contenido del artículo.
        
        Fracción reformada DOF 13-03-2025
        Párrafo adicionado DOF 01-01-2024
        """
        
        cleaned_text, reforms = extract_reforms(text)
        
        assert len(reforms) >= 1
        assert "reformada" in reforms[0]['action'].lower() or "adicionado" in reforms[0]['action'].lower()
        assert len(cleaned_text) < len(text)  # Should remove reform annotations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
