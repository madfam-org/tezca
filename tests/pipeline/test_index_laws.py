import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# 1. Setup paths

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
        cmd = Command()
        cmd.stdout = MagicMock()
        cmd.stderr = MagicMock()
        cmd.style = MagicMock() # Also style is used for warnings
        return cmd

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
        assert art2['title'] is None
        assert art2['chapter'] is None

    def test_handle_indexing_municipality(self, command):
        """Verify municipality field is added to ES document."""
        # Mock Law object
        mock_law = MagicMock()
        mock_law.official_id = "reglamento_gdl"
        mock_law.name = "Reglamento GDL"
        mock_law.category = "Reglamento"
        mock_law.tier = "municipal"
        mock_law.municipality = "Guadalajara"
        mock_law.status = "active"
        
        # Mock Version
        mock_version = MagicMock()
        mock_version.xml_file_path = "path/to/xml"
        mock_version.publication_date.isoformat.return_value = "2023-01-01"
        mock_law.versions.order_by.return_value.first.return_value = mock_version
        
        # Mock QuerySet
        from apps.api.models import Law
        mock_qs = MagicMock()
        mock_qs.__iter__.return_value = iter([mock_law])
        mock_qs.count.return_value = 1
        # Also need slicing support if used, but here limit is None so loop iterates
        # But wait, code does: if options.get('limit'): laws = laws[:limit]
        # Slicing a MagicMock return another MagicMock by default, which is fine unless we iterate it
        # If limit is None, we just iterate mock_qs
        Law.objects.filter.return_value = mock_qs
        
        # Mock Path/File Operations
        with MagicMock() as mock_path_cls:
            # We need to mock Path.cwd() / ...
            mock_cwd = MagicMock()
            mock_xml_file = MagicMock()
            mock_xml_file.exists.return_value = True
            mock_xml_file.read_text.return_value = MINIMAL_V2_XML
            
            mock_cwd.__truediv__.return_value = mock_xml_file
            
            # Patch Path in the command module
            with pytest.MonkeyPatch.context() as m:
                m.setattr("pathlib.Path.cwd", lambda: mock_cwd)
                
                # Mock helpers.bulk
                mock_helpers = MagicMock()
                sys.modules['elasticsearch.helpers'] = mock_helpers
                from apps.api.management.commands import index_laws
                m.setattr(index_laws, 'helpers', mock_helpers)

                # Run handle
                command.handle(law_id="reglamento_gdl", dry_run=False, limit=None)
                
                # Verify bulk called
                assert mock_helpers.bulk.called
                call_args = mock_helpers.bulk.call_args
                actions = call_args[0][1]
                
                # Check first doc
                doc = actions[0]
                assert doc['_source']['municipality'] == "Guadalajara"
                assert doc['_source']['tier'] == "municipal"
