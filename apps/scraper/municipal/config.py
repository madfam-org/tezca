"""
Municipal Scraper Configuration

Centralized configuration for all municipality scrapers.
Each municipality has its own config with base URLs, selectors, and metadata.
"""

from typing import Dict, Any, List

MUNICIPALITY_CONFIGS: Dict[str, Dict[str, Any]] = {
    # Tier 0 - Capital
    'cdmx': {
        'name': 'Ciudad de México',
        'state': 'Ciudad de México',
        'base_url': 'https://data.consejeria.cdmx.gob.mx/',
        'catalog_type': 'html',
        'tier': 0,
        'population': 9_209_944,
        'selectors': {
            'catalog_path': '/index.php/leyes/leyes',
            'law_links': 'a',
            'title': 'td',
        },
        'status': 'implemented'
    },
    
    # Tier 1 - Major Cities
    'guadalajara': {
        'name': 'Guadalajara',
        'state': 'Jalisco',
        'base_url': 'https://transparencia.guadalajara.gob.mx/',
        'catalog_type': 'html',
        'tier': 1,
        'population': 1_495_189,
        'selectors': {
            'catalog_path': '/Losreglamentosfederalesestatalesymunicipales',
            'law_links': 'a:contains("Reglamento")',
            'title': '.title',
        },
        'status': 'partial'  # Needs enhancement
    },
    
    'monterrey': {
        'name': 'Monterrey',
        'state': 'Nuevo León',
        'base_url': 'https://www.monterrey.gob.mx/',
        'catalog_type': 'html',
        'tier': 1,
        'population': 1_142_194,
        'selectors': {
            'catalog_path': '/transparencia/Oficial_/Normatividad.html',
            'law_links': 'a',
            'title': 'td', # Placeholder, need to check HTML
        },
        'status': 'stub'  # Needs implementation
    },
    
    'puebla': {
        'name': 'Puebla',
        'state': 'Puebla',
        'base_url': 'https://www.pueblacapital.gob.mx/',
        'catalog_type': 'html',
        'tier': 1,
        'population': 1_692_181,
        'selectors': {
            'catalog_path': '/transparencia/normatividad',
            'law_links': 'a.law-link',
        },
        'status': 'planned'
    },
    
    'tijuana': {
        'name': 'Tijuana',
        'state': 'Baja California',
        'base_url': 'https://www.tijuana.gob.mx/',
        'catalog_type': 'html',
        'tier': 1,
        'population': 1_810_645,
        'selectors': {
            'catalog_path': '/transparencia',
        },
        'status': 'planned'
    },
    
    'leon': {
        'name': 'León',
        'state': 'Guanajuato',
        'base_url': 'https://www.leon.gob.mx/',
        'catalog_type': 'html',
        'tier': 1,
        'population': 1_721_626,
        'selectors': {
            'catalog_path': '/transparencia',
        },
        'status': 'planned'
    },
}

def get_config(municipality: str) -> Dict[str, Any]:
    """Get configuration for a specific municipality."""
    config = MUNICIPALITY_CONFIGS.get(municipality.lower())
    if not config:
        raise ValueError(f"No configuration found for municipality: {municipality}")
    return config

def list_municipalities(tier: int = None, status: str = None) -> List[str]:
    """
    List all configured municipalities, optionally filtered by tier or status.
    
    Args:
        tier: Filter by tier (0, 1, 2, etc.)
        status: Filter by status ('implemented', 'partial', 'stub', 'planned')
    
    Returns:
        List of municipality identifiers
    """
    results = []
    for muni_id, config in MUNICIPALITY_CONFIGS.items():
        if tier is not None and config.get('tier') != tier:
            continue
        if status is not None and config.get('status') != status:
            continue
        results.append(muni_id)
    return results

def get_tier1_municipalities() -> List[str]:
    """Get all tier 1 (major city) municipality identifiers."""
    return list_municipalities(tier=1)
