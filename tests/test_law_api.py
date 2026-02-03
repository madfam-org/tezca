import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.api.models import Law, LawVersion
from datetime import date
from unittest.mock import patch, MagicMock

@pytest.mark.django_db
class TestLawApi:
    def setup_method(self):
        self.client = APIClient()
        
        # Create test laws
        self.law_federal = Law.objects.create(
            official_id='federal_law',
            name='Ley Federal',
            tier='federal',
            category='ley'
        )
        LawVersion.objects.create(
            law=self.law_federal,
            publication_date=date(2024, 1, 1),
            dof_url='http://dof.gob.mx/nota_detalle.php?codigo=123'
        )

        self.law_state = Law.objects.create(
            official_id='colima_codigo_civil',
            name='Código Civil de Colima',
            tier='state',
            category='codigo'
        )

    def test_law_detail(self):
        """Test retrieving law detail metadata."""
        url = reverse('law-detail', args=[self.law_federal.official_id])
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert response.data['id'] == 'federal_law'
        assert response.data['versions'][0]['dof_url'] == 'http://dof.gob.mx/nota_detalle.php?codigo=123'
    
    def test_law_detail_not_found(self):
        """Test 404 for non-existent law."""
        url = reverse('law-detail', args=['nonexistent'])
        response = self.client.get(url)
        assert response.status_code == 404

    def test_law_detail_state_extraction(self):
        """Test that state name is extracted from official_id."""
        url = reverse('law-detail', args=[self.law_state.official_id])
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert response.data['state'] == 'Colima'

    @patch('apps.api.law_views.Elasticsearch')
    def test_law_articles(self, mock_es_class):
        """Test retrieving law articles."""
        # Mock Elasticsearch response
        mock_es = mock_es_class.return_value
        mock_es.search.return_value = {
            'hits': {
                'hits': [
                    {'_source': {'article': '1', 'text': 'Artículo 1...'}},
                    {'_source': {'article': '2', 'text': 'Artículo 2...'}}
                ]
            }
        }
        
        url = reverse('law-articles', args=[self.law_federal.official_id])
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert response.data['total'] == 2
        assert response.data['articles'][0]['article_id'] == '1'
        assert len(response.data['articles']) == 2
        
        # Verify ES call
        mock_es_class.assert_called_once()

    def test_states_list(self):
        """Test verifying state list generation."""
        # ensure we have at least one state law from setup
        url = reverse('states-list')
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert 'states' in response.data
        assert 'Colima' in response.data['states']
