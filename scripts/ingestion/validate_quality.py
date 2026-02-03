#!/usr/bin/env python3
"""
Validate quality of ingested laws.
Checks article counts and parse success.
"""

import json
import argparse
from pathlib import Path
from lxml import etree

def load_registry():
    """Load the law registry."""
    with open('data/law_registry.json', 'r') as f:
        return json.load(f)

def validate_law(law_id, expected_articles):
    """Validate a single law."""
    xml_path = Path(f'data/federal/mx-fed-{law_id}-v2.xml')
    
    if not xml_path.exists():
        return False, f"XML file not found: {xml_path}"
    
    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
        
        # Count articles
        articles = root.xpath('//akn:article', namespaces=ns)
        count = len(articles)
        
        # Calculate deviation
        diff = abs(count - expected_articles)
        percent_diff = (diff / expected_articles) * 100 if expected_articles > 0 else 0
        
        status = "✅ PASS"
        if percent_diff > 10:
            status = "⚠️ WARN"
        if percent_diff > 50:
            status = "❌ FAIL"
            
        return True, {
            "id": law_id,
            "status": status,
            "actual": count,
            "expected": expected_articles,
            "diff": diff,
            "percent": percent_diff
        }
        
    except Exception as e:
        return False, f"Parse error: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='Validate law quality')
    parser.add_argument('--laws', help='Comma-separated law IDs')
    parser.add_argument('--priority', type=int, help='Priority level to validate')
    args = parser.parse_args()
    
    registry = load_registry()
    laws_to_validate = []
    
    if args.laws:
        ids = args.laws.split(',')
        laws_to_validate = [l for l in registry['federal_laws'] if l['id'] in ids]
    elif args.priority:
        laws_to_validate = [l for l in registry['federal_laws'] if l.get('priority') == args.priority]
    else:
        # Default: validate active/ingested laws
        laws_to_validate = registry['federal_laws']

    print(f"Validating {len(laws_to_validate)} laws...")
    print("-" * 60)
    print(f"{'ID':<10} | {'Status':<10} | {'Actual':<8} | {'Expected':<8} | {'Diff %':<8}")
    print("-" * 60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for law in laws_to_validate:
        law_id = law['id']
        expected = law['expected_articles']
        
        success, result = validate_law(law_id, expected)
        
        if success:
            if isinstance(result, str): # Error in validation logic (shouldn't happen with success=True in my code structure above, wait)
                 # Ah, wait. I returned (False, msg) for errors.
                 pass
            
            # Check if result is dict
            if isinstance(result, dict):
                print(f"{result['id']:<10} | {result['status']:<10} | {result['actual']:<8} | {result['expected']:<8} | {result['percent']:.1f}%")
                if "FAIL" in result['status']:
                    failed += 1
                elif "WARN" in result['status']:
                     passed += 1 # Count warnings as pass for now
                else:
                    passed += 1
        else:
            # File not found or parse error
            if "not found" in result:
                # expected if not yet ingested
                skipped += 1
            else:
                print(f"{law_id:<10} | ❌ ERROR  | {result}")
                failed += 1
                
    print("-" * 60)
    print(f"Summary: {passed} Passed, {failed} Failed, {skipped} Skipped")

if __name__ == '__main__':
    main()
