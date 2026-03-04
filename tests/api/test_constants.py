"""Tests for shared constants."""

from apps.api.constants import DOMAIN_MAP


class TestDomainMap:
    """Validate DOMAIN_MAP structure and SCIAN-aligned entries."""

    VALID_CATEGORIES = {
        "civil",
        "penal",
        "fiscal",
        "mercantil",
        "laboral",
        "administrativo",
        "constitucional",
    }

    def test_all_values_are_valid_categories(self):
        """Every category in DOMAIN_MAP is a known legal category."""
        for domain, categories in DOMAIN_MAP.items():
            for cat in categories:
                assert (
                    cat in self.VALID_CATEGORIES
                ), f"DOMAIN_MAP['{domain}'] contains unknown category '{cat}'"

    def test_generic_domains_present(self):
        """Backward-compatible generic domains exist."""
        for key in (
            "finance",
            "criminal",
            "labor",
            "civil",
            "administrative",
            "constitutional",
        ):
            assert key in DOMAIN_MAP, f"Missing generic domain '{key}'"

    def test_scian_domains_present(self):
        """SCIAN 2023-aligned domains exist."""
        for key in (
            "manufacturing",
            "commerce",
            "foreign_trade",
            "financial_services",
            "professional_services",
        ):
            assert key in DOMAIN_MAP, f"Missing SCIAN domain '{key}'"

    def test_manufacturing_categories(self):
        """SCIAN 31-33 manufacturing maps to laboral+administrativo+mercantil."""
        assert set(DOMAIN_MAP["manufacturing"]) == {
            "laboral",
            "administrativo",
            "mercantil",
        }

    def test_commerce_categories(self):
        """SCIAN 43+46 commerce maps to mercantil+fiscal+administrativo."""
        assert set(DOMAIN_MAP["commerce"]) == {"mercantil", "fiscal", "administrativo"}

    def test_foreign_trade_categories(self):
        """Foreign trade maps to fiscal+mercantil+administrativo."""
        assert set(DOMAIN_MAP["foreign_trade"]) == {
            "fiscal",
            "mercantil",
            "administrativo",
        }

    def test_financial_services_categories(self):
        """SCIAN 52 financial services maps to fiscal+mercantil."""
        assert set(DOMAIN_MAP["financial_services"]) == {"fiscal", "mercantil"}

    def test_professional_services_categories(self):
        """SCIAN 54 professional services maps to civil+administrativo+laboral."""
        assert set(DOMAIN_MAP["professional_services"]) == {
            "civil",
            "administrativo",
            "laboral",
        }

    def test_no_empty_domain_values(self):
        """No domain maps to an empty list."""
        for domain, categories in DOMAIN_MAP.items():
            assert len(categories) > 0, f"DOMAIN_MAP['{domain}'] is empty"
