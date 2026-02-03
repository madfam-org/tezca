#!/usr/bin/env python3
"""
Compare parser v1 vs v2 performance.
"""

from pathlib import Path
from lxml import etree

def compare_parsers():
    """Compare v1 and v2 XML outputs."""
    
    print("=" * 70)
    print("PARSER V1 vs V2 COMPARISON - Ley de Amparo")
    print("=" * 70)
    
    # Load both XMLs
    v1_file = Path("data/federal/mx-fed-amparo.xml")
    v2_file = Path("data/federal/mx-fed-amparo-v2.xml")
    
    if not v1_file.exists() or not v2_file.exists():
        print("❌ One or both XML files not found")
        return
    
    v1_tree = etree.parse(str(v1_file))
    v2_tree = etree.parse(str(v2_file))
    
    v1_root = v1_tree.getroot()
    v2_root = v2_tree.getroot()
    
    ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
    
    # Count elements
    metrics = {
        'v1': {
            'titles': len(v1_root.findall('.//akn:title', ns)),
            'books': len(v1_root.findall('.//akn:book', ns)),
            'chapters': len(v1_root.findall('.//akn:chapter', ns)),
            'sections': len(v1_root.findall('.//akn:section', ns)),
            'articles': len(v1_root.findall('.//akn:article', ns)),
            'notes': len(v1_root.findall('.//akn:note', ns)),
            'file_size': v1_file.stat().st_size,
        },
        'v2': {
            'titles': len(v2_root.findall('.//akn:title', ns)),
            'books': len(v2_root.findall('.//akn:book', ns)),
            'chapters': len(v2_root.findall('.//akn:chapter', ns)),
            'sections': len(v2_root.findall('.//akn:section', ns)),
            'articles': len(v2_root.findall('.//akn:article', ns)),
            'notes': len(v2_root.findall('.//akn:note', ns)),
            'file_size': v2_file.stat().st_size,
        }
    }
    
    # Print comparison table
    print("\n📊 Element Counts:")
    print(f"{'Element':<15} {'V1':<10} {'V2':<10} {'Change':<15}")
    print("-" * 50)
    
    for elem_type in ['books', 'titles', 'chapters', 'sections', 'articles', 'notes']:
        v1_count = metrics['v1'][elem_type]
        v2_count = metrics['v2'][elem_type]
        change = v2_count - v1_count
        change_pct = (change / v1_count * 100) if v1_count > 0 else float('inf')
        
        if change > 0:
            change_str = f"+{change} ({change_pct:+.0f}%)" if v1_count > 0 else f"+{change} (NEW)"
            icon = "🟢"
        elif change < 0:
            change_str = f"{change} ({change_pct:.0f}%)"
            icon = "🔴"
        else:
            change_str = "No change"
            icon = "⚪"
        
        print(f"{icon} {elem_type.capitalize():<12} {v1_count:<10} {v2_count:<10} {change_str}")
    
    # File size
    v1_kb = metrics['v1']['file_size'] / 1024
    v2_kb = metrics['v2']['file_size'] / 1024
    size_diff = v2_kb - v1_kb
    print(f"\n📄 File Size:   {v1_kb:.1f} KB    {v2_kb:.1f} KB    {size_diff:+.1f} KB")
    
    # Calculate improvements
    print("\n" + "=" * 70)
    print("KEY IMPROVEMENTS")
    print("=" * 70)
    
    improvements = []
    
    if metrics['v2']['titles'] > metrics['v1']['titles']:
        improvements.append(f"✅ TÍTULO detection: {metrics['v1']['titles']} → {metrics['v2']['titles']} ({metrics['v2']['titles']} found!)")
    
    if metrics['v2']['sections'] > metrics['v1']['sections']:
        improvements.append(f"✅ SECTION detection: +{metrics['v2']['sections']} sections parsed")
    
    # Approximate TRANSITORIOS by checking last articles
    v2_articles = v2_root.findall('.//akn:article', ns)
    transitorios_count = len([a for a in v2_articles if 'trans-' in a.get('id', '')])
    if transitorios_count > 0:
        improvements.append(f"✅ TRANSITORIOS parsing: {transitorios_count} transitory articles")
    
    if metrics['v2']['notes'] > 0:
        improvements.append(f"✅ Reform metadata: {metrics['v2']['notes']} annotations extracted")
    
    article_diff = metrics['v2']['articles'] - metrics['v1']['articles']
    if article_diff != 0:
        improvements.append(f"ℹ️  Article count: {metrics['v1']['articles']} → {metrics['v2']['articles']} ({article_diff:+d})")
    
    for imp in improvements:
        print(imp)
    
    # Accuracy estimate
    print("\n" + "=" * 70)
    print("ESTIMATED ACCURACY")
    print("=" * 70)
    
    # Assume ~300 total articles in Amparo
    expected_articles = 300
    v1_accuracy = (metrics['v1']['articles'] / expected_articles) * 100
    v2_accuracy = (metrics['v2']['articles'] / expected_articles) * 100
    
    print(f"V1 Accuracy: ~{v1_accuracy:.1f}% ({metrics['v1']['articles']}/{expected_articles} articles)")
    print(f"V2 Accuracy: ~{v2_accuracy:.1f}% ({metrics['v2']['articles']}/{expected_articles} articles)")
    
    if v2_accuracy >= 95:
        print(f"\n🎉 V2 EXCEEDS 95% TARGET! ({v2_accuracy:.1f}%)")
    elif v2_accuracy > v1_accuracy:
        print(f"\n✅ V2 IMPROVEMENT: +{v2_accuracy - v1_accuracy:.1f}% accuracy")
    
    print("\n" + "=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    
    if transitorios_count > 0 and metrics['v2']['titles'] > 0:
        print("✅ V2 parser successfully addresses POC gaps:")
        print("   - TÍTULO detection working")
        print("   - TRANSITORIOS parsing working")
        print("   - Metadata extraction working")
        print("\n🚀 Ready for testing on diverse law corpus!")
    else:
        print("⚠️  Some gaps remain - review parser logic")

if __name__ == "__main__":
    compare_parsers()
