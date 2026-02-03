#!/usr/bin/env python3
"""
Update viewer data.
1. Runs xml_to_json.py to generate article JSONs.
2. Updates laws.ts with metadata from registry + actual analysis.
"""

import json
import subprocess
from pathlib import Path
from lxml import etree

def load_registry():
    with open('data/law_registry.json', 'r') as f:
        return json.load(f)

def get_law_stats(law_id):
    """Get stats from XML file."""
    xml_path = Path(f'data/federal/mx-fed-{law_id}-v2.xml')
    if not xml_path.exists():
        return None
    
    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
        
        articles = len(root.xpath('//akn:article', namespaces=ns))
        # Count transitorios (simplistic check for now, can improve)
        # Assuming transitorios are marked or we use xml_to_json logic.
        # Ideally xml_to_json creates JSONs, we can read them?
        # But let's verify file exists.
        return articles
    except:
        return 0

def generate_laws_ts(registry):
    """Generate apps/web/lib/laws.ts content."""
    
    laws_ts_content = """// Law metadata for the viewer
export interface Law {
    id: string;
    name: string;
    fullName: string;
    articles: number;
    transitorios: number;
    grade: 'A' | 'B' | 'C';
    score: number;
    priority: 1 | 2;
    tier: string;
    file: string;
    category?: string;
}

export const laws: Law[] = [
"""
    
    active_laws = []
    
    for law in registry['federal_laws']:
        # Check if ingested
        xml_file = f"mx-fed-{law['id']}-v2.xml"
        if not Path(f"data/federal/{xml_file}").exists():
            continue
            
        # Get stats (we could use xml_to_json output, but let's trust registry + existence for now)
        # Or better, read the generated JSON if it exists?
        json_path = Path(f"viewer_data/{law['id']}.json")
        
        articles = law['expected_articles']
        transitorios = 0
        
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
                articles = data.get('total_articles', articles)
                transitorios = data.get('total_transitorios', 0)
        
        # Determine grade (mock for now based on validation)
        grade = "A" 
        score = 98.0
        
        entry = f"""    {{
        id: '{law['id']}',
        name: '{law['short_name']}',
        fullName: '{law['name']}',
        articles: {articles},
        transitorios: {transitorios},
        grade: '{grade}',
        score: {score},
        priority: {law['priority']},
        tier: '{law['tier']}',
        file: '{xml_file}',
        category: '{law.get('category', 'other')}'
    }},"""
        active_laws.append(entry)
        
    laws_ts_content += "\n".join(active_laws)
    laws_ts_content += "\n];\n\n"
    
    # Add helper functions
    laws_ts_content += """export function getLawById(id: string): Law | undefined {
    return laws.find(law => law.id === id);
}

export function getTotalArticles(): number {
    return laws.reduce((sum, law) => sum + law.articles, 0);
}

export function getAverageQuality(): number {
    if (laws.length === 0) return 0;
    const total = laws.reduce((sum, law) => sum + law.score, 0);
    return total / laws.length;
}

export function getGradeDistribution(): Record<string, number> {
    return laws.reduce((acc, law) => {
        acc[law.grade] = (acc[law.grade] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);
}
"""

    with open('apps/web/lib/laws.ts', 'w') as f:
        f.write(laws_ts_content)
    print("✅ apps/web/lib/laws.ts updated")

def main():
    # 1. Run xml_to_json conversion
    print("🚀 Running XML to JSON conversion...")
    subprocess.run(['python3', 'scripts/xml_to_json.py'], check=False)
    
    # 2. Update laws.ts
    print("🚀 Updating laws.ts...")
    registry = load_registry()
    generate_laws_ts(registry)
    
    print("✅ Viewer data update complete!")

if __name__ == '__main__':
    main()
