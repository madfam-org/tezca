"""
Unit tests for parser V2.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'apps'))

from parsers.akn_generator_v2 import AkomaNtosoGeneratorV2


class TestParserBasics:
    """Test basic parser functionality."""
    
    def test_parse_single_article(self, sample_law_text):
        """Test parsing a single article."""
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(sample_law_text)
        
        assert result.metadata['total_elements'] >= 3
        assert result.metadata['articles'] >= 3
    
    def test_parse_with_title(self, sample_law_text):
        """Test parsing with TÍTULO."""
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(sample_law_text)
        
        assert result.metadata['structure']['title'] >= 1
    
    def test_parse_with_chapter(self, sample_law_text):
        """Test parsing with CAPÍTULO."""
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(sample_law_text)
        
        assert result.metadata['structure']['chapter'] >= 1
    
    def test_parse_transitorios(self, sample_law_text):
        """Test parsing TRANSITORIOS section."""
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(sample_law_text)
        
        # Should detect at least 2 transitorios
        transitorios_count = sum(1 for e in result.elements if e['type'] == 'transitorio')
        assert transitorios_count >= 2
    
    def test_confidence_score(self, sample_law_text):
        """Test confidence scoring."""
        parser = AkomaNtosoGeneratorV2()
        result = parser.parse_structure_v2(sample_law_text)
        
        assert 0 <= result.confidence <= 1
        assert result.confidence > 0.5  # Should be reasonably confident


class TestXMLGeneration:
    """Test XML generation."""
    
    def test_generate_xml(self, sample_law_text, temp_data_dir):
        """Test complete XML generation."""
        parser = AkomaNtosoGeneratorV2()
        
        metadata = parser.create_frbr_metadata(
            law_type='ley',
            date_str='2020-01-01',
            slug='test',
            title='Test Law'
        )
        
        output_path = temp_data_dir / 'federal' / 'test.xml'
        xml_path, result = parser.generate_xml(sample_law_text, metadata, output_path)
        
        assert xml_path.exists()
        assert xml_path.stat().st_size > 0
        assert result.metadata['articles'] >= 3
    
    def test_xml_well_formed(self, sample_law_text, temp_data_dir):
        """Test that generated XML is well-formed."""
        from lxml import etree
        
        parser = AkomaNtosoGeneratorV2()
        metadata = parser.create_frbr_metadata('ley', '2020-01-01', 'test', 'Test')
        output_path = temp_data_dir / 'federal' / 'test.xml'
        
        xml_path, _ = parser.generate_xml(sample_law_text, metadata, output_path)
        
        # Parse XML to verify it's well-formed
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        
        assert root is not None
        assert 'akomaNtoso' in root.tag


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
