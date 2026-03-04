"""Test fixtures and mock API responses."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from helpers.api_client import close_client
from helpers.config import TEZCA_API_URL

BASE = TEZCA_API_URL


@pytest.fixture(autouse=True)
async def _cleanup_client():
    """Close the shared httpx client after each test."""
    yield
    await close_client()


@pytest.fixture()
def mock_api():
    """Provide a respx mock router scoped to the Tezca API base URL."""
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        yield router


# --- Sample response data ---

SEARCH_RESPONSE = {
    "results": [
        {
            "id": "amparo_art1",
            "law_id": "amparo",
            "law_name": "Ley de Amparo",
            "article": "Art. 1",
            "snippet": "El juicio de amparo tiene por objeto resolver...",
            "score": 12.5,
            "date": "2024-06-01",
            "tier": "federal",
            "law_type": "legislative",
            "state": None,
            "hierarchy": ["Título Primero"],
        }
    ],
    "total": 1,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "facets": {
        "by_tier": [{"key": "federal", "count": 1}],
        "by_category": [{"key": "constitucional", "count": 1}],
    },
}

LAW_DETAIL_RESPONSE = {
    "id": "amparo",
    "name": "Ley de Amparo, Reglamentaria de los artículos 103 y 107",
    "short_name": "Ley de Amparo",
    "category": "constitucional",
    "tier": "federal",
    "law_type": "legislative",
    "state": None,
    "status": "vigente",
    "source_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LAmp.pdf",
    "versions": [
        {
            "publication_date": "2024-06-01",
            "valid_from": "2024-06-01",
            "valid_to": None,
            "change_summary": "Reforma artículos 5, 17 y 128",
        }
    ],
    "articles": 271,
    "has_cross_refs": True,
    "degraded": False,
}

LAW_ARTICLES_RESPONSE = {
    "law_id": "amparo",
    "law_name": "Ley de Amparo",
    "total": 2,
    "page": 1,
    "page_size": 500,
    "articles": [
        {"article_id": "Art. 1", "text": "El juicio de amparo tiene por objeto..."},
        {"article_id": "Art. 2", "text": "El juicio de amparo se tramitará..."},
    ],
}

STRUCTURE_RESPONSE = {
    "law_id": "amparo",
    "structure": [
        {
            "label": "Título Primero",
            "children": [
                {"label": "Capítulo I", "children": []},
                {"label": "Capítulo II", "children": []},
            ],
        }
    ],
}

LAW_LIST_RESPONSE = {
    "count": 2,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": "amparo",
            "name": "Ley de Amparo",
            "tier": "federal",
            "law_type": "legislative",
            "category": "constitucional",
            "status": "vigente",
        },
        {
            "id": "codigo_civil_federal",
            "name": "Código Civil Federal",
            "tier": "federal",
            "law_type": "legislative",
            "category": "civil",
            "status": "vigente",
        },
    ],
}

RELATED_RESPONSE = {
    "law_id": "amparo",
    "related": [
        {
            "law_id": "codigo_penal_federal",
            "name": "Código Penal Federal",
            "tier": "federal",
            "category": "penal",
            "state": None,
            "score": 5.0,
        }
    ],
}

CROSS_REFS_STATS_RESPONSE = {
    "statistics": {
        "total_outgoing": 47,
        "total_incoming": 120,
        "most_referenced_laws": [{"slug": "constitucion_politica", "count": 15}],
        "most_citing_laws": [{"slug": "codigo_civil_federal", "count": 8}],
    }
}

ARTICLE_REFS_RESPONSE = {
    "outgoing": [
        {
            "text": "el artículo 5 de la Constitución",
            "targetLawSlug": "constitucion_politica",
            "targetArticle": "5",
            "confidence": 0.95,
        }
    ],
    "incoming": [],
    "total_outgoing": 1,
    "total_incoming": 0,
}

JUDICIAL_SEARCH_RESPONSE = {
    "total": 1,
    "page": 1,
    "page_size": 20,
    "query": "amparo",
    "results": [
        {
            "id": 1,
            "registro": "2028741",
            "epoca": "11a",
            "instancia": "Primera Sala",
            "materia": "civil",
            "tipo": "jurisprudencia",
            "rubro": "COSA JUZGADA. CONCEPTO Y ALCANCE.",
            "ponente": "Ministro X",
            "fecha_publicacion": "2024-03-15",
        }
    ],
}

JUDICIAL_DETAIL_RESPONSE = {
    "id": 1,
    "registro": "2028741",
    "epoca": "11a",
    "instancia": "Primera Sala",
    "materia": "civil",
    "tipo": "jurisprudencia",
    "rubro": "COSA JUZGADA. CONCEPTO Y ALCANCE.",
    "texto": "La cosa juzgada es la autoridad...",
    "precedentes": "Contradicción de tesis 123/2023",
    "ponente": "Ministro X",
    "fuente": "Semanario Judicial de la Federación",
    "fecha_publicacion": "2024-03-15",
}

JUDICIAL_STATS_RESPONSE = {
    "total": 5123,
    "by_tipo": {"jurisprudencia": 3000, "tesis_aislada": 2123},
    "by_materia": {"civil": 1200, "penal": 900},
    "by_epoca": {"11a": 4000, "10a": 1123},
}

CATEGORIES_RESPONSE = [
    {"category": "civil", "count": 1200, "label": "Derecho Civil"},
    {"category": "penal", "count": 890, "label": "Derecho Penal"},
]

STATES_RESPONSE = {"states": ["Aguascalientes", "Baja California", "Jalisco"]}

STATS_RESPONSE = {
    "total_laws": 23322,
    "federal_count": 2078,
    "state_count": 8664,
    "municipal_count": 2239,
    "total_articles": 917443,
    "federal_coverage": 98.5,
    "state_coverage": 94.2,
    "total_coverage": 96.1,
    "last_update": "2024-11-15",
    "recent_laws": [],
}

COVERAGE_RESPONSE = {
    "total_laws": 23322,
    "overall_pct": 96.1,
    "tiers": [
        {
            "id": "federal_laws",
            "name": {"es": "Leyes federales", "en": "Federal laws"},
            "have": 2078,
            "universe": 336,
            "pct": 98.5,
        }
    ],
}

SUGGEST_RESPONSE = {
    "suggestions": [
        {"id": "amparo", "name": "Ley de Amparo", "tier": "federal"},
    ]
}

SEARCH_WITHIN_RESPONSE = {
    "law_id": "amparo",
    "query": "suspensión",
    "total": 1,
    "results": [
        {"article_id": "Art. 128", "snippet": "...suspensión del acto...", "score": 2.1}
    ],
}
