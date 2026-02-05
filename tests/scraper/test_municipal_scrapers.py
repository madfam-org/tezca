"""
Tests for municipal scraper framework

Tests the base scraper class, configuration system, and registry.
"""

import pytest
from apps.scraper.municipal.base import MunicipalScraper
from apps.scraper.municipal.config import get_config, list_municipalities, get_tier1_municipalities
from apps.scraper.municipal import get_scraper, list_available_scrapers


class TestConfiguration:
    """Test the configuration system."""
    
    def test_get_config_valid_municipality(self):
        """Test retrieving a valid municipality configuration."""
        config = get_config('guadalajara')
        
        assert config is not None
        assert config['name'] == 'Guadalajara'
        assert config['state'] == 'Jalisco'
        assert config['tier'] == 1
        assert 'base_url' in config
        assert 'selectors' in config
    
    def test_get_config_invalid_municipality(self):
        """Test that invalid municipality raises error."""
        with pytest.raises(ValueError, match="No configuration found"):
            get_config('invalid_municipality')
    
    def test_list_municipalities(self):
        """Test listing all municipalities."""
        all_munis = list_municipalities()
        
        assert len(all_munis) > 0
        assert 'guadalajara' in all_munis
        assert 'monterrey' in all_munis
        assert 'cdmx' in all_munis
    
    def test_list_municipalities_by_tier(self):
        """Test filtering municipalities by tier."""
        tier1 = list_municipalities(tier=1)
        tier0 = list_municipalities(tier=0)
        
        assert len(tier1) >= 5  # At least 5 tier 1 cities
        assert len(tier0) >= 1  # CDMX
        assert 'guadalajara' in tier1
        assert 'cdmx' in tier0
    
    def test_get_tier1_municipalities(self):
        """Test tier 1 helper function."""
        tier1 = get_tier1_municipalities()
        
        expected = ['guadalajara', 'monterrey', 'puebla', 'tijuana', 'leon']
        for city in expected:
            assert city in tier1


class TestBaseScraperClass:
    """Test the MunicipalScraper base class."""
    
    def test_initialization_with_config(self):
        """Test initialization using config dictionary."""
        config = get_config('guadalajara')
        scraper = MunicipalScraper(config=config)
        
        assert scraper.municipality == 'Guadalajara'
        assert scraper.base_url == config['base_url']
        assert scraper.state == 'Jalisco'
        assert scraper.session is not None
    
    def test_initialization_legacy(self):
        """Test backward-compatible initialization."""
        scraper = MunicipalScraper(
            municipality='Test Municipality',
            base_url='https://example.com'
        )
        
        assert scraper.municipality == 'Test Municipality'
        assert scraper.base_url == 'https://example.com'
        assert scraper.state is None
    
    def test_normalize_url_relative(self):
        """Test URL normalization for relative URLs."""
        scraper = MunicipalScraper(
            municipality='Test',
            base_url='https://example.com/'
        )
        
        normalized = scraper.normalize_url('/path/to/law')
        assert normalized == 'https://example.com/path/to/law'
    
    def test_normalize_url_absolute(self):
        """Test URL normalization for absolute URLs."""
        scraper = MunicipalScraper(
            municipality='Test',
            base_url='https://example.com/'
        )
        
        normalized = scraper.normalize_url('https://other.com/law')
        assert normalized == 'https://other.com/law'
    
    def test_is_pdf(self):
        """Test PDF detection."""
        scraper = MunicipalScraper(
            municipality='Test',
            base_url='https://example.com/'
        )
        
        assert scraper.is_pdf('https://example.com/law.pdf') is True
        assert scraper.is_pdf('https://example.com/law.PDF') is True
        assert scraper.is_pdf('https://example.com/law.html') is False
        assert scraper.is_pdf('https://example.com/law') is False
    
    def test_validate_law_data_valid(self):
        """Test validation of valid law data."""
        scraper = MunicipalScraper(
            municipality='Test',
            base_url='https://example.com/'
        )
        
        law = {
            'name': 'Test Regulation',
            'url': 'https://example.com/regulation.pdf',
            'municipality': 'Test Municipality'
        }
        
        assert scraper.validate_law_data(law) is True
    
    def test_validate_law_data_missing_fields(self):
        """Test validation fails with missing fields."""
        scraper = MunicipalScraper(
            municipality='Test',
            base_url='https://example.com/'
        )
        
        # Missing 'url'
        law_missing_url = {
            'name': 'Test Regulation',
            'municipality': 'Test Municipality'
        }
        assert scraper.validate_law_data(law_missing_url) is False
        
        # Missing 'name'
        law_missing_name = {
            'url': 'https://example.com/regulation.pdf',
            'municipality': 'Test Municipality'
        }
        assert scraper.validate_law_data(law_missing_name) is False
    
    def test_validate_law_data_invalid_url(self):
        """Test validation fails with invalid URL."""
        scraper = MunicipalScraper(
            municipality='Test',
            base_url='https://example.com/'
        )
        
        law = {
            'name': 'Test Regulation',
            'url': 'not-a-valid-url',
            'municipality': 'Test Municipality'
        }
        
        assert scraper.validate_law_data(law) is False
    
    def test_extract_category(self):
        """Test category extraction from law names."""
        scraper = MunicipalScraper(
            municipality='Test',
            base_url='https://example.com/'
        )
        
        assert scraper.extract_category('Reglamento de Tránsito') == 'Reglamento'
        assert scraper.extract_category('Código Civil') == 'Código'
        assert scraper.extract_category('Ley de Transparencia') == 'Ley'
        assert scraper.extract_category('Decreto 123/2024') == 'Decreto'
        assert scraper.extract_category('Acuerdo Municipal') == 'Otro'


class TestScraperRegistry:
    """Test the scraper registry and factory functions."""
    
    def test_get_scraper_valid(self):
        """Test getting a valid scraper instance."""
        scraper = get_scraper('guadalajara')
        
        assert scraper is not None
        assert scraper.municipality == 'Guadalajara'
        assert hasattr(scraper, 'scrape_catalog')
    
    def test_get_scraper_invalid(self):
        """Test that invalid scraper raises error."""
        with pytest.raises(ValueError, match="No scraper registered"):
            get_scraper('invalid_city')
    
    def test_get_scraper_case_insensitive(self):
        """Test scraper factory is case-insensitive."""
        scraper1 = get_scraper('guadalajara')
        scraper2 = get_scraper('Guadalajara')
        scraper3 = get_scraper('GUADALAJARA')
        
        assert scraper1.municipality == scraper2.municipality == scraper3.municipality
    
    def test_list_available_scrapers(self):
        """Test listing scraper availability status."""
        scrapers = list_available_scrapers()
        
        assert isinstance(scrapers, dict)
        assert 'guadalajara' in scrapers
        assert 'monterrey' in scrapers
        
        # Check status values are valid
        valid_statuses = ['implemented', 'partial', 'stub', 'planned', 'not_implemented']
        for status in scrapers.values():
            assert status in valid_statuses


class TestTier1Scrapers:
    """Integration tests for tier 1 city scrapers."""
    
    @pytest.mark.parametrize('city', [
        'guadalajara',
        'monterrey',
        'puebla',
        'tijuana',
        'leon'
    ])
    def test_scraper_initialization(self, city):
        """Test that all tier 1 scrapers initialize correctly."""
        scraper = get_scraper(city)
        
        assert scraper is not None
        assert scraper.base_url is not None
        assert scraper.municipality is not None
        assert scraper.state is not None
        assert hasattr(scraper, 'scrape_catalog')
        assert hasattr(scraper, 'scrape_law_content')
    
    @pytest.mark.parametrize('city', [
        'guadalajara',
        'monterrey',
        'puebla',
        'tijuana',
        'leon'
    ])
    def test_scraper_has_state(self, city):
        """Test that scrapers have correct state assignment."""
        scraper = get_scraper(city)
        
        # Map expected states
        state_mapping = {
            'guadalajara': 'Jalisco',
            'monterrey': 'Nuevo León',
            'puebla': 'Puebla',
            'tijuana': 'Baja California',
            'leon': 'Guanajuato'
        }
        
        assert scraper.state == state_mapping[city]
