"""
Municipal Scraper Registry

Central registry for all municipal scrapers.
Provides factory functions to instantiate scrapers.
"""

from typing import Dict, Optional, Type

from .base import MunicipalScraper

# Import all scraper implementations
from .cdmx import CDMXScraper
from .config import (
    MUNICIPALITY_CONFIGS,
    get_config,
    get_tier2_municipalities,
    list_municipalities,
)
from .generic import GenericMunicipalScraper
from .guadalajara import GuadalajaraScraper
from .leon import LeonScraper
from .monterrey import MonterreyScraper
from .puebla import PueblaScraper
from .tijuana import TijuanaScraper

# Registry mapping municipality IDs to scraper classes
SCRAPERS: Dict[str, Type[MunicipalScraper]] = {
    "cdmx": CDMXScraper,
    "guadalajara": GuadalajaraScraper,
    "monterrey": MonterreyScraper,
    "puebla": PueblaScraper,
    "tijuana": TijuanaScraper,
    "leon": LeonScraper,
}


def get_scraper(municipality: str) -> MunicipalScraper:
    """
    Factory function to get a scraper instance for a municipality.

    Falls back to GenericMunicipalScraper for configured municipalities
    that do not have a dedicated scraper class.

    Args:
        municipality: Municipality identifier (e.g., 'guadalajara', 'merida')

    Returns:
        Instantiated scraper object

    Raises:
        ValueError: If municipality is not in MUNICIPALITY_CONFIGS
    """
    municipality = municipality.lower()

    # Use dedicated scraper if available
    scraper_class = SCRAPERS.get(municipality)
    if scraper_class:
        return scraper_class()

    # Fall back to generic scraper for configured municipalities
    if municipality in MUNICIPALITY_CONFIGS:
        return GenericMunicipalScraper(city_key=municipality)

    raise ValueError(
        f"No configuration found for municipality '{municipality}'. "
        f"Available: {', '.join(MUNICIPALITY_CONFIGS.keys())}"
    )


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
            result[muni_id] = config.get("status", "unknown")
        else:
            result[muni_id] = "not_implemented"
    return result


def get_implemented_scrapers() -> list[str]:
    """
    Get list of municipalities with implemented scrapers.

    Returns:
        List of municipality IDs with working scrapers
    """
    return [
        muni_id
        for muni_id, status in list_available_scrapers().items()
        if status in ["implemented", "partial"]
    ]
