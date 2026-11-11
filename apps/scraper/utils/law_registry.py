"""
Law registry management.

Central repository for law metadata including URLs, expected counts, and priorities.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from apps.scraper.utils.law_name import normalize_law_name, normalize_short_name


class LawRegistry:
    """
    Manage law metadata registry.

    Usage:
        registry = LawRegistry()

        # Get all laws
        all_laws = registry.all()

        # Get by ID
        amparo = registry.get_by_id('amparo')

        # Filter by priority
        priority_1 = registry.filter_by_priority(1)

        # Filter by tier
        fiscal_laws = registry.filter_by_tier('fiscal')
    """

    def __init__(
        self, registry_path: Optional[Path] = None, include_reglamentos: bool = False
    ):
        """
        Initialize law registry.

        Args:
            registry_path: Path to law_registry.json file.
                          Defaults to data/law_registry.json
            include_reglamentos: Also load discovered_reglamentos.json entries.
        """
        if registry_path is None:
            registry_path = (
                Path(__file__).parent.parent.parent.parent
                / "data"
                / "law_registry.json"
            )

        self.registry_path = Path(registry_path)
        self.data = self._load_registry()
        self.laws = [
            self._clean_names(law) for law in self.data.get("federal_laws", [])
        ]

        if include_reglamentos:
            self.laws.extend(self._load_reglamentos())

    def _load_registry(self) -> Dict:
        """Load registry from JSON file."""
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Registry not found: {self.registry_path}")

        with open(self.registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _clean_names(law: Dict) -> Dict:
        """Strip Diputados-catalog debris from an entry's name fields.

        287 registry entries were merged from the catalog with the index
        cell's whole text as the name ("<title> \\t DOF 20/03/2025 \\t Nueva
        reforma"). Normalising on load means every consumer — the pipeline,
        ``DatabaseSaver``, ``sync_law_status`` — sees the clean title without
        rewriting the JSON file. Idempotent; clean entries are untouched.
        """
        raw_name = law.get("name")
        if not isinstance(raw_name, str):
            return law
        clean = normalize_law_name(raw_name)
        if clean == raw_name:
            return law
        cleaned = dict(law)
        cleaned["name"] = clean
        if "short_name" in law:
            cleaned["short_name"] = normalize_short_name(law["short_name"], raw_name)
        return cleaned

    def _load_reglamentos(self) -> List[Dict]:
        """Load discovered reglamentos and normalise to registry format."""
        reglamentos_path = self.registry_path.parent / "discovered_reglamentos.json"
        if not reglamentos_path.exists():
            return []

        with open(reglamentos_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        entries = []
        for item in raw:
            entries.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "short_name": item["name"][:60],
                    "type": "reglamento",
                    "slug": item["id"],
                    "expected_articles": 0,
                    "publication_date": "",
                    "source": "chamber",
                    "url": item["url"],
                    "priority": 2,
                    "tier": "federal",
                    "status": "active",
                    "category": "reglamento",
                }
            )
        return entries

    def all(self) -> List[Dict]:
        """Get all laws in registry."""
        return self.laws.copy()

    def get_by_id(self, law_id: str) -> Optional[Dict]:
        """
        Get law by ID.

        Args:
            law_id: Law identifier (e.g., 'amparo', 'iva')

        Returns:
            Law metadata dict or None if not found
        """
        for law in self.laws:
            if law["id"] == law_id:
                return law.copy()
        return None

    def filter_by_priority(self, priority: int) -> List[Dict]:
        """
        Get laws by priority level.

        Args:
            priority: Priority level (1=highest)

        Returns:
            List of law metadata dicts
        """
        return [law.copy() for law in self.laws if law.get("priority") == priority]

    def filter_by_tier(self, tier: str) -> List[Dict]:
        """
        Get laws by tier/category.

        Args:
            tier: Law tier (e.g., 'fiscal', 'constitutional', 'labor')

        Returns:
            List of law metadata dicts
        """
        return [law.copy() for law in self.laws if law.get("tier") == tier]

    def filter_by_category(self, category: str) -> List[Dict]:
        """
        Get laws by category.

        Args:
            category: Law category (e.g., 'reglamento', 'constitutional', 'fiscal')

        Returns:
            List of law metadata dicts
        """
        return [law.copy() for law in self.laws if law.get("category") == category]

    def filter_by_status(self, status: str = "active") -> List[Dict]:
        """
        Get laws by status.

        Args:
            status: Law status ('active', 'deprecated', etc.)

        Returns:
            List of law metadata dicts
        """
        return [law.copy() for law in self.laws if law.get("status") == status]

    def get_ids(self) -> List[str]:
        """Get list of all law IDs."""
        return [law["id"] for law in self.laws]

    def count(self) -> int:
        """Get total number of laws."""
        return len(self.laws)

    def summary(self) -> Dict:
        """Get registry summary statistics."""
        return {
            "total_laws": len(self.laws),
            "by_priority": {
                1: len(self.filter_by_priority(1)),
                2: len(self.filter_by_priority(2)),
            },
            "by_tier": self._count_by_field("tier"),
            "by_status": self._count_by_field("status"),
        }

    def _count_by_field(self, field: str) -> Dict[str, int]:
        """Count laws grouped by field value."""
        counts = {}
        for law in self.laws:
            value = law.get(field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts


def main():
    """Test law registry."""

    print("📚 Law Registry\n")

    registry = LawRegistry()

    print(f"Total laws: {registry.count()}")
    print(f"Registry path: {registry.registry_path}\n")

    # Summary
    summary = registry.summary()
    print("Summary:")
    print(f"  Priority 1: {summary['by_priority'][1]}")
    print(f"  Priority 2: {summary['by_priority'][2]}")
    print(f"\n  By tier:")
    for tier, count in summary["by_tier"].items():
        print(f"    {tier}: {count}")

    # List all laws
    print(f"\nAll laws ({registry.count()}):")
    for law in registry.all():
        print(
            f"  [{law['id']:10}] {law['short_name']:40} (Tier: {law['tier']}, Priority: {law['priority']})"
        )

    # Test filters
    print(f"\nPriority 1 laws:")
    for law in registry.filter_by_priority(1):
        print(f"  • {law['short_name']}")

    print(f"\nFiscal laws:")
    for law in registry.filter_by_tier("fiscal"):
        print(f"  • {law['short_name']}")


if __name__ == "__main__":
    main()
