import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# 1. Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))

# 2. Mock Django BEFORE importing the command
# This is necessary because the environment lacks Django
mock_django = MagicMock()
mock_base_command = MagicMock()
class BaseCommand:
    def add_arguments(self, parser): pass
    def handle(self, *args, **kwargs): pass

mock_django.core.management.base.BaseCommand = BaseCommand
sys.modules['django'] = mock_django
sys.modules['django.core'] = mock_django.core
sys.modules['django.core.management'] = mock_django.core.management
sys.modules['django.core.management.base'] = mock_django.core.management.base

# Mock Elasticsearch
mock_es = MagicMock()
sys.modules['elasticsearch'] = mock_es

# Mock apps.api.models
mock_models = MagicMock()
sys.modules['apps.api.models'] = mock_models

# 3. Now import the command
from apps.api.management.commands.index_laws import Command

MINIMAL_V2_XML = """<?xml version="1.0" encoding="UTF-8"?>
<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
    <act name="law">
        <body>
            <book eId="book_1">
                <num>LIBRO PRIMERO</num>
                <heading>Disposiciones Generales</heading>
                <title eId="title_1">
                    <num>TÍTULO I</num>
                    <heading>Del Ámbito de Validez</heading>
                    <chapter eId="chapter_1">
                        <num>CAPÍTULO I</num>
                        <heading>Objeto de la Ley</heading>
                        <article eId="art_1">
                            <num>Artículo 1.</num>
                            <heading>Objeto</heading>
                            <content>
                                <p>La presente ley es de orden público.</p>
                            </content>
                        </article>
                    </chapter>
                </title>
            </book>
            <article eId="art_2">
                <num>Artículo 2.</num>
                <content>
                    <p>Artículo suelto fuera de jerarquía.</p>
                </content>
            </article>
        </body>
    </act>
</akomaNtoso>
"""

class TestIndexLawsCommand:
    
    @pytest.fixture
    def command(self):
        return Command()

    def test_extract_articles_hierarchy(self, command):
        """Verify extraction of Book/Title/Chapter structure."""
        articles = command.extract_articles_from_xml(MINIMAL_V2_XML, "test_law")
        
        assert len(articles) == 2
        
        # Test Article 1 (Deep Hierarchy)
        art1 = articles[0]
        assert art1['article_id'] == "Artículo 1."
        assert "orden público" in art1['text']
        
        # Check hierarchy matches
        assert art1['book']['num'] == "LIBRO PRIMERO"
        assert art1['book']['heading'] == "Disposiciones Generales"
        
        assert art1['title']['num'] == "TÍTULO I"
        assert art1['title']['heading'] == "Del Ámbito de Validez"
        
        assert art1['chapter']['num'] == "CAPÍTULO I"
        assert art1['chapter']['heading'] == "Objeto de la Ley"
        
    def test_extract_articles_flat(self, command):
        """Verify extraction of an article with no hierarchy."""
        articles = command.extract_articles_from_xml(MINIMAL_V2_XML, "test_law")
        art2 = articles[1]
        
        assert art2['article_id'] == "Artículo 2."
        assert art2['book'] is None
        assert art2['title'] is None
        assert art2['chapter'] is None
