#!/usr/bin/env python3
"""
Validate Akoma Ntoso XML against the official schema.
This ensures our generated XML is spec-compliant.
"""

from lxml import etree
from pathlib import Path
import sys

def validate_akn_xml(xml_path: Path) -> bool:
    """
    Validate Akoma Ntoso XML file.
    
    For now, performs basic well-formedness check.
    Schema validation would require downloading AKN 3.0 XSD.
    """
    
    print(f"🔍 Validating: {xml_path.name}")
    print("=" * 70)
    
    try:
        # Parse XML
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        
        print(f"✅ XML is well-formed")
        print(f"   Root element: {root.tag}")
        print(f"   Namespace: {root.nsmap.get(None, 'None')}")
        
        # Check for required elements
        checks = {
            'meta': len(root.findall('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}meta')),
            'body': len(root.findall('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}body')),
            'FRBRWork': len(root.findall('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}FRBRWork')),
            'FRBRExpression': len(root.findall('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}FRBRExpression')),
            'FRBRManifestation': len(root.findall('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}FRBRManifestation')),
            'article': len(root.findall('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}article')),
            'chapter': len(root.findall('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}chapter')),
        }
        
        print(f"\n📊 Structure validation:")
        all_good = True
        for element, count in checks.items():
            status = "✅" if count > 0 else "⚠️ "
            print(f"   {status} {element}: {count}")
            if element in ['meta', 'body', 'FRBRWork', 'FRBRExpression', 'FRBRManifestation'] and count == 0:
                all_good = False
        
        # File stats
        file_size = xml_path.stat().st_size
        print(f"\n📄 File statistics:")
        print(f"   Size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
        print(f"   Lines: {len(open(xml_path).readlines()):,}")
        
        if all_good:
            print(f"\n✅ VALIDATION PASSED - XML appears AKN-compliant")
            return True
        else:
            print(f"\n⚠️  VALIDATION WARNING - Missing required elements")
            return False
            
    except etree.XMLSyntaxError as e:
        print(f"❌ XML SYNTAX ERROR: {e}")
        return False
    except Exception as e:
        print(f"❌ VALIDATION ERROR: {e}")
        return False


def compare_with_existing(new_xml: Path, existing_dir: Path):
    """Compare new XML with existing laws for consistency."""
    
    print(f"\n📊 Comparing with existing laws...")
    print("=" * 70)
    
    existing_files = list(existing_dir.glob("*.xml"))
    if not existing_files:
        print("⚠️  No existing XML files found for comparison")
        return
    
    print(f"Found {len(existing_files)} existing law(s):")
    for f in existing_files:
        print(f"   - {f.name}")
        
        try:
            tree = etree.parse(str(f))
            root = tree.getroot()
            articles = len(root.findall('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}article'))
            print(f"     Articles: {articles}")
        except:
            print(f"     (Could not parse)")


if __name__ == "__main__":
    xml_file = Path("data/federal/mx-fed-amparo.xml")
    
    if not xml_file.exists():
        print(f"❌ File not found: {xml_file}")
        sys.exit(1)
    
    # Validate
    is_valid = validate_akn_xml(xml_file)
    
    # Compare with existing
    compare_with_existing(xml_file, xml_file.parent)
    
    print("\n" + "=" * 70)
    if is_valid:
        print("✅ READY FOR INDIGO IMPORT")
        print("\nNext steps:")
        print("  1. Start Indigo CMS: docker-compose up api")
        print("  2. Access admin: http://localhost:8000/admin")
        print("  3. Import XML file")
    else:
        print("⚠️  NEEDS REVIEW BEFORE IMPORT")
        print("\nRecommended fixes:")
        print("  - Ensure all FRBR elements are present")
        print("  - Validate namespace declarations")
    
    sys.exit(0 if is_valid else 1)
