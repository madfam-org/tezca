import os
import sys
import glob
from lxml import etree
from elasticsearch import Elasticsearch, helpers

# Configuration
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
INDEX_LAWS = "laws"
INDEX_ARTICLES = "articles"

def connect_es():
    return Elasticsearch(hosts=[ES_HOST])

def create_indices(es):
    # Laws Index
    if not es.indices.exists(index=INDEX_LAWS):
        es.indices.create(index=INDEX_LAWS, body={
            "mappings": {
                "properties": {
                    "id": { "type": "keyword" },
                    "name": { "type": "text", "analyzer": "spanish" },
                    "category": { "type": "keyword" },
                    "status": { "type": "keyword" },
                    "total_articles": { "type": "integer" }
                }
            }
        })
        print(f"Created index: {INDEX_LAWS}")

    # Articles Index
    if not es.indices.exists(index=INDEX_ARTICLES):
        es.indices.create(index=INDEX_ARTICLES, body={
            "settings": {
                "analysis": {
                    "analyzer": {
                        "spanish_legal": {
                            "type": "spanish",
                            "stopwords": "_spanish_"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "law_id": { "type": "keyword" },
                    "article_id": { "type": "keyword" },
                    "order": { "type": "integer" },
                    "text": { 
                        "type": "text", 
                        "analyzer": "spanish_legal" 
                    },
                    "tags": { "type": "keyword" }
                }
            }
        })
        print(f"Created index: {INDEX_ARTICLES}")

def parse_law(xml_path):
    """Parse XML and yield actions for bulk indexing."""
    tree = etree.parse(xml_path)
    root = tree.getroot()
    ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
    
    law_id = os.path.basename(xml_path).replace('mx-fed-', '').replace('-v2.xml', '')
    
    # 1. Index Law Metadata
    law_title = "Unknown Law"
    meta = root.find(".//akn:identification", ns)
    if meta is not None:
        work = meta.find(".//akn:FRBRWork", ns)
        if work is not None:
            title_node = work.find(".//akn:FRBRname", ns)
            if title_node is not None:
                law_title = title_node.get("value")

    articles = root.findall(".//akn:article", ns)
    
    # Yield Law Document
    yield {
        "_index": INDEX_LAWS,
        "_id": law_id,
        "id": law_id,
        "name": law_title,
        "category": "federal", # Placeholder, should come from registry
        "status": "active",
        "total_articles": len(articles)
    }

    # 2. Index Articles
    for idx, art in enumerate(articles):
        art_id = art.get("eId")
        
        # Num
        num_node = art.find("akn:num", ns)
        art_num = num_node.text.strip() if num_node is not None else "Unknown"
        
        # Content
        # Use itertext to capture all text (including paragraphs, lists, etc.)
        # We replace the num to avoid duplication if we want, or just keep it.
        # Simple approach: all text.
        text = "".join(art.itertext()).strip()
        
        if not text:
            continue
            
        # Simple tagging
        tags = []
        lower_text = text.lower()
        if "multa" in lower_text or "sancion" in lower_text:
            tags.append("sancion")
        if "impuesto" in lower_text:
            tags.append("fiscal")
        if "prisión" in lower_text:
            tags.append("penal")

        yield {
            "_index": INDEX_ARTICLES,
            "_id": f"{law_id}-{art_id}",
            "law_id": law_id,
            "article_id": art_id,
            "order": idx,
            "text": text,
            "tags": tags
        }

def main():
    try:
        es = connect_es()
        if not es.ping():
            print(f"❌ Could not connect to Elasticsearch at {ES_HOST}")
            return
            
        print("✅ Connected to Elasticsearch")
        create_indices(es)
        
        # Find all XMLs
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data/federal")
        xml_files = glob.glob(os.path.join(data_dir, "mx-fed-*-v2.xml"))
        
        print(f"Found {len(xml_files)} law files to index.")
        
        total_indexed = 0
        for xml in xml_files:
            print(f"Indexing {os.path.basename(xml)}...")
            actions = list(parse_law(xml))
            if actions:
                helpers.bulk(es, actions)
                total_indexed += len(actions)
            
        print(f"🚀 Indexing Complete. Total documents: {total_indexed}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
