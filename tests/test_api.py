import os
import django
from django.conf import settings

# Configure settings before setup
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.indigo.settings')
    django.setup()

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

@pytest.mark.skip(reason="Calculation engine not installed")
class CalculationApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('calculate')

    def test_calculate_gross_income(self):
        """Test that the API correctly calculates gross income via OpenFisca."""
        payload = {
            "period": "2024-01",
            "income_cash": 20000.0,
            "income_goods": 5000.0,
            "is_resident": True
        }
        
        response = self.client.post(self.url, payload, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['gross_income'], 25000.0)
        self.assertEqual(response.data['isr_obligation'], True)

    def test_invalid_input(self):
        """Test API validation."""
        payload = {
            "period": "invalid-date"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 400)
