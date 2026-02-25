"""
Municipal Scraper Configuration

Centralized configuration for all municipality scrapers.
Each municipality has its own config with base URLs, selectors, and metadata.
"""

from typing import Any, Dict, List

MUNICIPALITY_CONFIGS: Dict[str, Dict[str, Any]] = {
    # Tier 0 - Capital
    "cdmx": {
        "name": "Ciudad de México",
        "state": "Ciudad de México",
        "base_url": "https://data.consejeria.cdmx.gob.mx/",
        "catalog_type": "html",
        "tier": 0,
        "population": 9_209_944,
        "selectors": {
            "catalog_path": "/index.php/leyes/leyes",
            "law_links": "a",
            "title": "td",
        },
        "status": "implemented",
    },
    # Tier 1 - Major Cities
    "guadalajara": {
        "name": "Guadalajara",
        "state": "Jalisco",
        "base_url": "https://transparencia.guadalajara.gob.mx/",
        "catalog_type": "html",
        "tier": 1,
        "population": 1_495_189,
        "selectors": {
            "catalog_path": "/Losreglamentosfederalesestatalesymunicipales",
            "law_links": 'a:contains("Reglamento")',
            "title": ".title",
        },
        "status": "partial",  # Needs enhancement
    },
    "monterrey": {
        "name": "Monterrey",
        "state": "Nuevo León",
        "base_url": "https://www.monterrey.gob.mx/",
        "catalog_type": "html",
        "tier": 1,
        "population": 1_142_194,
        "selectors": {
            "catalog_path": "/transparencia/Oficial_/Normatividad.html",
            "law_links": "a",
            "title": "td",  # Placeholder, need to check HTML
        },
        "status": "stub",  # Needs implementation
    },
    "puebla": {
        "name": "Puebla",
        "state": "Puebla",
        "base_url": "https://www.pueblacapital.gob.mx/",
        "catalog_type": "html",
        "tier": 1,
        "population": 1_692_181,
        "selectors": {
            "catalog_path": "/transparencia/normatividad",
            "law_links": "a.law-link",
        },
        "status": "planned",
    },
    "tijuana": {
        "name": "Tijuana",
        "state": "Baja California",
        "base_url": "https://www.tijuana.gob.mx/",
        "catalog_type": "html",
        "tier": 1,
        "population": 1_810_645,
        "selectors": {
            "catalog_path": "/transparencia",
        },
        "status": "planned",
    },
    "leon": {
        "name": "León",
        "state": "Guanajuato",
        "base_url": "https://www.leon.gob.mx/",
        "catalog_type": "html",
        "tier": 1,
        "population": 1_721_626,
        "selectors": {
            "catalog_path": "/transparencia",
        },
        "status": "planned",
    },
    # Tier 2 - Expansion Cities (next 15 by population)
    "juarez": {
        "name": "Ciudad Juárez",
        "state": "Chihuahua",
        "base_url": "https://www.juarez.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 1_512_354,
        "selectors": {"catalog_path": "/transparencia/normatividad"},
        "status": "planned",
    },
    "zapopan": {
        "name": "Zapopan",
        "state": "Jalisco",
        "base_url": "https://www.zapopan.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 1_476_491,
        "selectors": {"catalog_path": "/transparencia"},
        "status": "planned",
    },
    "merida": {
        "name": "Mérida",
        "state": "Yucatán",
        "base_url": "https://www.merida.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 995_129,
        "selectors": {"catalog_path": "/transparencia/normatividad"},
        "status": "planned",
    },
    "cancun": {
        "name": "Cancún (Benito Juárez)",
        "state": "Quintana Roo",
        "base_url": "https://www.benitojuarez.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 888_797,
        "selectors": {"catalog_path": "/transparencia"},
        "status": "planned",
    },
    "aguascalientes": {
        "name": "Aguascalientes",
        "state": "Aguascalientes",
        "base_url": "https://www.ags.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 863_893,
        "selectors": {"catalog_path": "/transparencia/normatividad"},
        "status": "planned",
    },
    "san_luis_potosi": {
        "name": "San Luis Potosí",
        "state": "San Luis Potosí",
        "base_url": "https://www.slp.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 824_229,
        "selectors": {"catalog_path": "/transparencia"},
        "status": "planned",
    },
    "hermosillo": {
        "name": "Hermosillo",
        "state": "Sonora",
        "base_url": "https://www.hermosillo.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 812_229,
        "selectors": {"catalog_path": "/transparencia/normatividad"},
        "status": "planned",
    },
    "chihuahua": {
        "name": "Chihuahua",
        "state": "Chihuahua",
        "base_url": "https://www.municipiochihuahua.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 878_062,
        "selectors": {"catalog_path": "/transparencia"},
        "status": "planned",
    },
    "queretaro": {
        "name": "Querétaro",
        "state": "Querétaro",
        "base_url": "https://www.municipiodequeretaro.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 801_940,
        "selectors": {"catalog_path": "/transparencia/normatividad"},
        "status": "planned",
    },
    "morelia": {
        "name": "Morelia",
        "state": "Michoacán",
        "base_url": "https://www.morelia.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 743_275,
        "selectors": {"catalog_path": "/transparencia"},
        "status": "planned",
    },
    "saltillo": {
        "name": "Saltillo",
        "state": "Coahuila",
        "base_url": "https://www.saltillo.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 823_128,
        "selectors": {"catalog_path": "/transparencia/normatividad"},
        "status": "planned",
    },
    "toluca": {
        "name": "Toluca",
        "state": "Estado de México",
        "base_url": "https://www.toluca.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 873_536,
        "selectors": {"catalog_path": "/transparencia"},
        "status": "planned",
    },
    "culiacan": {
        "name": "Culiacán",
        "state": "Sinaloa",
        "base_url": "https://culiacan.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 808_416,
        "selectors": {"catalog_path": "/transparencia/normatividad"},
        "status": "planned",
    },
    "villahermosa": {
        "name": "Villahermosa (Centro)",
        "state": "Tabasco",
        "base_url": "https://www.villahermosa.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 684_847,
        "selectors": {"catalog_path": "/transparencia"},
        "status": "planned",
    },
    "acapulco": {
        "name": "Acapulco",
        "state": "Guerrero",
        "base_url": "https://www.acapulco.gob.mx/",
        "catalog_type": "html",
        "tier": 2,
        "population": 779_566,
        "selectors": {"catalog_path": "/transparencia/normatividad"},
        "status": "planned",
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
        if tier is not None and config.get("tier") != tier:
            continue
        if status is not None and config.get("status") != status:
            continue
        results.append(muni_id)
    return results


def get_tier1_municipalities() -> List[str]:
    """Get all tier 1 (major city) municipality identifiers."""
    return list_municipalities(tier=1)


def get_tier2_municipalities() -> List[str]:
    """Get all tier 2 (expansion city) municipality identifiers."""
    return list_municipalities(tier=2)
