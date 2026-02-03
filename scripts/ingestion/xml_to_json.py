#!/usr/bin/env python3
"""
XML to JSON converter for law viewer.
Parses Akoma Ntoso XML files and extracts articles for web display.
"""

import json
import sys
from pathlib import Path
from lxml import etree

def parse_law_xml(xml_path: Path) -> dict:
    """Parse Akoma Ntoso XML and extract articles."""
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    
    # Define namespace
    ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
    
    # Extract metadata
    law_name = xml_path.stem.replace('mx-fed-', '').replace('-v2', '')
    
    # Extract all articles
    articles = []
    
    # Regular articles
    for article in root.xpath('//akn:article', namespaces=ns):
        art_id = article.get('id', '')
        
        # Get article number
        num_elem = article.find('akn:num', namespaces=ns)
        num = num_elem.text if num_elem is not None else art_id
        
        # Get article content
        content_parts = []
        for elem in article.xpath('.//akn:p | .//akn:item', namespaces=ns):
            text = ''.join(elem.itertext()).strip()
            if text:
                content_parts.append(text)
        
        content = '\n\n'.join(content_parts) if content_parts else ''
        
        # Determine if it's a TRANSITORIO
        is_transitorio = 'trans-' in art_id.lower() or 'transitorio' in num.lower()
        
        articles.append({
            'id': art_id,
            'number': num,
            'content': content,
            'type': 'transitorio' if is_transitorio else 'article'
        })
    
    return {
        'law_id': law_name,
        'articles': articles,
        'total_articles': len([a for a in articles if a['type'] == 'article']),
        'total_transitorios': len([a for a in articles if a['type'] == 'transitorio'])
    }


def main():
    """Convert all XML files to JSON."""
    base_dir = Path(__file__).parent.parent
    xml_dir = base_dir / 'data' / 'federal'
    output_dir = base_dir / 'viewer_data'
    output_dir.mkdir(exist_ok=True)
    
    xml_files = list(xml_dir.glob('*-v2.xml'))
    print(f"Converting {len(xml_files)} XML files to JSON...")
    
    for xml_file in xml_files:
        try:
            law_data = parse_law_xml(xml_file)
            output_file = output_dir / f"{law_data['law_id']}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(law_data, f, ensure_ascii=False, indent=2)
            
            print(f"  ✅ {law_data['law_id']}: {law_data['total_articles']} articles, {law_data['total_transitorios']} transitorios")
        except Exception as e:
            print(f"  ❌ Error processing {xml_file.name}: {e}")
    
    print(f"\n✅ Conversion complete! Files saved to {output_dir}")


if __name__ == "__main__":
    main()
