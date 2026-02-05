"""
Law registry management.

Central repository for law metadata including URLs, expected counts, and priorities.
"""

from pathlib import Path
from typing import List, Dict, Optional
import json


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
    
    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize law registry.
        
        Args:
            registry_path: Path to law_registry.json file.
                          Defaults to data/law_registry.json
        """
        if registry_path is None:
            registry_path = Path(__file__).parent.parent.parent.parent / 'data' / 'law_registry.json'
        
        self.registry_path = Path(registry_path)
        self.data = self._load_registry()
        self.laws = self.data.get('federal_laws', [])
    
    def _load_registry(self) -> Dict:
        """Load registry from JSON file."""
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Registry not found: {self.registry_path}")
        
        with open(self.registry_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
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
            if law['id'] == law_id:
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
        return [law.copy() for law in self.laws if law.get('priority') == priority]
    
    def filter_by_tier(self, tier: str) -> List[Dict]:
        """
        Get laws by tier/category.
        
        Args:
            tier: Law tier (e.g., 'fiscal', 'constitutional', 'labor')
        
        Returns:
            List of law metadata dicts
        """
        return [law.copy() for law in self.laws if law.get('tier') == tier]
    
    def filter_by_status(self, status: str = 'active') -> List[Dict]:
        """
        Get laws by status.
        
        Args:
            status: Law status ('active', 'deprecated', etc.)
        
        Returns:
            List of law metadata dicts
        """
        return [law.copy() for law in self.laws if law.get('status') == status]
    
    def get_ids(self) -> List[str]:
        """Get list of all law IDs."""
        return [law['id'] for law in self.laws]
    
    def count(self) -> int:
        """Get total number of laws."""
        return len(self.laws)
    
    def summary(self) -> Dict:
        """Get registry summary statistics."""
        return {
            'total_laws': len(self.laws),
            'by_priority': {
                1: len(self.filter_by_priority(1)),
                2: len(self.filter_by_priority(2)),
            },
            'by_tier': self._count_by_field('tier'),
            'by_status': self._count_by_field('status'),
        }
    
    def _count_by_field(self, field: str) -> Dict[str, int]:
        """Count laws grouped by field value."""
        counts = {}
        for law in self.laws:
            value = law.get(field, 'unknown')
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
    for tier, count in summary['by_tier'].items():
        print(f"    {tier}: {count}")
    
    # List all laws
    print(f"\nAll laws ({registry.count()}):")
    for law in registry.all():
        print(f"  [{law['id']:10}] {law['short_name']:40} (Tier: {law['tier']}, Priority: {law['priority']})")
    
    # Test filters
    print(f"\nPriority 1 laws:")
    for law in registry.filter_by_priority(1):
        print(f"  • {law['short_name']}")
    
    print(f"\nFiscal laws:")
    for law in registry.filter_by_tier('fiscal'):
        print(f"  • {law['short_name']}")


if __name__ == "__main__":
    main()
