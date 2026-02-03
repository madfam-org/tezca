#!/usr/bin/env python3
"""
Test parser v2 on IVA law.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'apps'))

from parsers.akn_generator_v2 import AkomaNtosoGeneratorV2

def test_iva():
    """Test v2 parser on Ley del IVA."""
    
    print("=" * 70)
    print("TESTING PARSER V2: Ley del IVA")
    print("=" * 70)
    
    # Load extracted text
    text_file = Path("data/raw/iva_extracted.txt")
    if not text_file.exists():
        print(f"❌ Text file not found: {text_file}")
        return
    
    print("\n📖 Loading extracted text...")
    text = text_file.read_text(encoding='utf-8')
    
    # Create v2 generator
    generator = AkomaNtosoGeneratorV2()
    
    # Metadata
    metadata = generator.create_frbr_metadata(
        law_type='ley',
        date_str='1978-12-29',
        slug='iva',
        title='Ley del Impuesto al Valor Agregado'
    )
    
    # Generate XML
    output_path = Path("data/federal/mx-fed-iva-v2.xml")
    output_path, result = generator.generate_xml(text, metadata, output_path)
    
    print(f"\n🎉 V2 generation complete!")
    print(f"   Output: {output_path}")
    
    # Compare with v1
    print("\n" + "=" * 70)
    print("COMPARISON: V1 vs V2")
    print("=" * 70)
    
    from lxml import etree
    
    v1_file = Path("data/federal/mx-fed-iva.xml")
    if v1_file.exists():
        v1_tree = etree.parse(str(v1_file))
        v1_root = v1_tree.getroot()
        
        ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
        
        v1_articles = len(v1_root.findall('.//akn:article', ns))
        v1_chapters = len(v1_root.findall('.//akn:chapter', ns))
        v1_titles = len(v1_root.findall('.//akn:title', ns))
        
        v2_articles = result.metadata['articles']
        v2_chapters = result.metadata['structure']['chapter']
        v2_titles = result.metadata['structure']['title']
        
        print(f"Articles:  V1={v1_articles}  V2={v2_articles}  Change={v2_articles-v1_articles:+d}")
        print(f"Chapters:  V1={v1_chapters}  V2={v2_chapters}  Change={v2_chapters-v1_chapters:+d}")
        print(f"Titles:    V1={v1_titles}  V2={v2_titles}  Change={v2_titles-v1_titles:+d}")
        print(f"Transitorios: V2={result.metadata['transitorios']}")
        
        if v2_articles >= v1_articles and v2_titles >= v1_titles:
            print("\n✅ V2 IMPROVEMENT CONFIRMED")
        else:
            print("\n⚠️  V2 may have regressions - review parser")
    
    return result

if __name__ == "__main__":
    test_iva()
