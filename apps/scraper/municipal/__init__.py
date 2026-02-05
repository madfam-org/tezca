"""
Municipal Scraper Registry

Central registry for all municipal scrapers.
Provides factory functions to instantiate scrapers.
"""

from typing import Dict, Type, Optional
from .base import MunicipalScraper
from .config import get_config, list_municipalities, MUNICIPALITY_CONFIGS

# Import all scraper implementations
from .cdmx import CDMXScraper
from .guadalajara import GuadalajaraScraper
from .monterrey import MonterreyScraper
from .puebla import PueblaScraper
from .tijuana import TijuanaScraper
from .leon import LeonScraper

# Registry mapping municipality IDs to scraper classes
SCRAPERS: Dict[str, Type[MunicipalScraper]] = {
    'cdmx': CDMXScraper,
    'guadalajara': GuadalajaraScraper,
    'monterrey': MonterreyScraper,
    'puebla': PueblaScraper,
    'tijuana': TijuanaScraper,
    'leon': LeonScraper,
}


def get_scraper(municipality: str) -> MunicipalScraper:
    """
    Factory function to get a scraper instance for a municipality.
    
    Args:
        municipality: Municipality identifier (e.g., 'guadalajara', 'monterrey')
        
    Returns:
        Instantiated scraper object
        
    Raises:
        ValueError: If municipality is not registered
    """
    municipality = municipality.lower()
    
    scraper_class = SCRAPERS.get(municipality)
    if not scraper_class:
        raise ValueError(
            f"No scraper registered for municipality '{municipality}'. "
            f"Available scrapers: {', '.join(SCRAPERS.keys())}"
        )
    
    return scraper_class()


def list_available_scrapers() -> Dict[str, str]:
    """
    List all available scrapers with their status.
    
    Returns:
        Dict mapping municipality ID to status
    """
    result = {}
    for muni_id in MUNICIPALITY_CONFIGS.keys():
        if muni_id in SCRAPERS:
            config = get_config(muni_id)
            result[muni_id] = config.get('status', 'unknown')
        else:
            result[muni_id] = 'not_implemented'
    return result


def get_implemented_scrapers() -> list[str]:
    """
    Get list of municipalities with implemented scrapers.
    
    Returns:
        List of municipality IDs with working scrapers
    """
    return [
        muni_id for muni_id, status in list_available_scrapers().items()
        if status in ['implemented', 'partial']
    ]
