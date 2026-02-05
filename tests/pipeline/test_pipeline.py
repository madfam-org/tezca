"""
Integration tests for end-to-end pipeline.
"""

import pytest
import sys
from pathlib import Path


from parsers.pipeline import IngestionPipeline
from parsers.quality import QualityCalculator


@pytest.mark.integration
class TestPipelineIntegration:
    """Test complete ingestion pipeline."""
    
    def test_pipeline_initialization(self, temp_data_dir):
        """Test pipeline initializes correctly."""
        pipeline = IngestionPipeline(data_dir=temp_data_dir, skip_download=True)
        
        assert pipeline.data_dir == temp_data_dir
        assert pipeline.pdf_dir.exists()
        assert pipeline.xml_dir.exists()
    
    def test_quality_calculation(self, sample_law_text, temp_data_dir):
        """Test quality metrics calculation."""
        from parsers.akn_generator_v2 import AkomaNtosoGeneratorV2
        
        # Generate XML
        parser = AkomaNtosoGeneratorV2()
        metadata = parser.create_frbr_metadata('ley', '2020-01-01', 'test', 'Test')
        xml_path = temp_data_dir / 'test.xml'
        parser.generate_xml(sample_law_text, metadata, xml_path)
        
        # Calculate quality
        calc = QualityCalculator()
        metrics = calc.calculate(
            xml_path=xml_path,
            law_name='Test Law',
            law_slug='test',
            articles_expected=3,
            parse_time=1.0
        )
        
        assert metrics.overall_score > 0
        assert metrics.grade in ['A', 'B', 'C', 'D', 'F']
        assert metrics.articles_found >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
