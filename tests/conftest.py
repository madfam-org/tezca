"""
Shared pytest fixtures for testing.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys

# Add apps to path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / 'apps'))
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_law_text():
    """Sample law text with basic structure."""
    return """
TÍTULO PRIMERO
De las Disposiciones Generales

CAPÍTULO I
Disposiciones Generales

Artículo 1.- Esta es una ley de prueba.

Artículo 2.- Las disposiciones de esta ley son de orden público.

I. Primera fracción.
II. Segunda fracción.

Artículo 3.- Se deroga.

TRANSITORIOS

PRIMERO.- Esta ley entrará en vigor el día siguiente al de su publicación.

SEGUNDO.- Se derogan todas las disposiciones que se opongan al presente decreto.
""".strip()


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    (data_dir / "raw" / "pdfs").mkdir(parents=True)
    (data_dir / "federal").mkdir(parents=True)
    (data_dir / "logs").mkdir(parents=True)
    return data_dir


@pytest.fixture
def sample_law_metadata():
    """Sample law metadata."""
    return {
        'id': 'test-law',
        'name': 'Ley de Prueba',
        'short_name': 'Ley de Prueba',
        'type': 'ley',
        'slug': 'test',
        'expected_articles': 3,
        'publication_date': '2020-01-01',
        'source': 'chamber',
        'url': 'https://example.com/test.pdf',
        'priority': 1,
        'tier': 'test',
        'status': 'active'
    }


@pytest.fixture
def basic_akn_xml():
    """Minimal valid Akoma Ntoso XML."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
  <act name="test">
    <meta>
      <identification source="#source">
        <FRBRWork>
          <FRBRthis value="/mx/act/2020/test"/>
          <FRBRuri value="/mx/act/2020/test"/>
          <FRBRdate date="2020-01-01" name="Generation"/>
        </FRBRWork>
      </identification>
    </meta>
    <body>
      <article id="art-1">
        <num>Artículo 1</num>
        <content>
          <p>Test content.</p>
        </content>
      </article>
    </body>
  </act>
</akomaNtoso>'''
