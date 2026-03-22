"""Tests for shared constants."""

from apps.api.constants import DOMAIN_MAP


class TestDomainMap:
    """Validate DOMAIN_MAP structure and SCIAN-aligned entries."""

    # Valid categories match actual production DB values (English branch names
    # + document types). See CLAUDE.md constants section.
    VALID_CATEGORIES = {
        "civil",
        "criminal",
        "fiscal",
        "financial",
        "commercial",
        "labor",
        "administrative",
        "constitutional",
        "constitucion",
        "environmental",
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
        """SCIAN 31-33 manufacturing maps to labor+administrative+commercial."""
        assert set(DOMAIN_MAP["manufacturing"]) == {
            "labor",
            "administrative",
            "commercial",
        }

    def test_commerce_categories(self):
        """SCIAN 43+46 commerce maps to commercial+fiscal+administrative."""
        assert set(DOMAIN_MAP["commerce"]) == {
            "commercial",
            "fiscal",
            "administrative",
        }

    def test_foreign_trade_categories(self):
        """Foreign trade maps to fiscal+commercial+administrative."""
        assert set(DOMAIN_MAP["foreign_trade"]) == {
            "fiscal",
            "commercial",
            "administrative",
        }

    def test_financial_services_categories(self):
        """SCIAN 52 financial services maps to fiscal+financial+commercial."""
        assert set(DOMAIN_MAP["financial_services"]) == {
            "fiscal",
            "financial",
            "commercial",
        }

    def test_professional_services_categories(self):
        """SCIAN 54 professional services maps to civil+administrative+labor."""
        assert set(DOMAIN_MAP["professional_services"]) == {
            "civil",
            "administrative",
            "labor",
        }

    def test_consumer_domains_present(self):
        """Consumer-facing composite domains exist."""
        for key in ("training", "customs", "safety"):
            assert key in DOMAIN_MAP, f"Missing consumer domain '{key}'"

    def test_training_categories(self):
        """Training domain maps to labor+administrative."""
        assert set(DOMAIN_MAP["training"]) == {"labor", "administrative"}

    def test_customs_categories(self):
        """Customs domain maps to fiscal+commercial+administrative."""
        assert set(DOMAIN_MAP["customs"]) == {
            "fiscal",
            "commercial",
            "administrative",
        }

    def test_safety_categories(self):
        """Safety domain maps to labor+administrative+environmental."""
        assert set(DOMAIN_MAP["safety"]) == {
            "labor",
            "administrative",
            "environmental",
        }

    def test_no_empty_domain_values(self):
        """No domain maps to an empty list."""
        for domain, categories in DOMAIN_MAP.items():
            assert len(categories) > 0, f"DOMAIN_MAP['{domain}'] is empty"
