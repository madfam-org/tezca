#!/usr/bin/env python3
"""
Fix Law Registry Data Quality Issues

This script:
1. Generates missing 'slug' fields from 'id' 
2. Sets default publication_date for laws without dates
3. Validates all required fields
4. Creates backup before modifying
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

def generate_slug(law_id):
    """Generate URL-safe slug from law ID."""
    return law_id.lower().strip()

def fix_registry():
    registry_path = Path("data/law_registry.json")
    
    # Backup
    backup_path = registry_path.with_suffix('.json.bak')
    shutil.copy2(registry_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    
    # Load
    with open(registry_path, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    
    laws = registry['federal_laws']
    fixed_count = 0
    
    for law in laws:
        modified = False
        
        # Fix 1: Generate slug if missing
        if 'slug' not in law or not law['slug']:
            law['slug'] = generate_slug(law['id'])
            modified = True
        
        # Fix 2: Set default publication_date if missing
        if 'publication_date' not in law or not law['publication_date']:
            # Use a placeholder that indicates "unknown"
            # This should be updated manually or via scraping later
            law['publication_date'] = "1900-01-01"  # Placeholder for unknown
            modified = True
        
        # Fix 3: Ensure all core fields exist with defaults
        defaults = {
            'status': 'discovered',
            'priority': 3,
            'tier': 'general',
            'category': 'federal'
        }
        
        for key, default_value in defaults.items():
            if key not in law or not law[key]:
                law[key] = default_value
                modified = True
        
        if modified:
            fixed_count += 1
    
    # Save
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Fixed {fixed_count} laws")
    print(f"✅ Updated registry: {registry_path}")
    
    # Validation Report
    print("\n📊 Validation Report:")
    print(f"   Total laws: {len(laws)}")
    
    issues = []
    for law in laws:
        required_fields = ['id', 'name', 'slug', 'url', 'publication_date']
        for field in required_fields:
            if field not in law or not law[field]:
                issues.append(f"{law['id']}: missing {field}")
    
    if issues:
        print(f"   ⚠️  Issues found: {len(issues)}")
        for issue in issues[:10]:  # Show first 10
            print(f"      - {issue}")
    else:
        print(f"   ✅ All laws have required fields")

if __name__ == "__main__":
    fix_registry()
