import os
import sys
import glob
from lxml import etree
from elasticsearch import Elasticsearch

# Configuration
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
INDEX_NAME = "laws"

def connect_es():
    return Elasticsearch(hosts=[ES_HOST])

def create_index(es):
    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME, body={
            "mappings": {
                "properties": {
                    "law_id": {"type": "keyword"},
                    "law_title": {"type": "text"},
                    "article_id": {"type": "keyword"},
                    "article_num": {"type": "keyword"},
                    "text": {"type": "text", "analyzer": "spanish"},
                    "tags": {"type": "keyword"}
                }
            }
        })
        print(f"Created index: {INDEX_NAME}")

def parse_and_index(es, xml_path):
    print(f"Indexing {xml_path}...")
    tree = etree.parse(xml_path)
    root = tree.getroot()
    
    # Namespaces (Akoma Ntoso usually has one, but assuming simple parse for now or handling namespaces)
    ns = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
    
    # Extract Law Title (Naive)
    law_title = "Unknown Law"
    meta = root.find(".//akn:identification", ns)
    if meta is not None:
        work = meta.find(".//akn:FRBRWork", ns)
        if work is not None:
            title_node = work.find(".//akn:FRBRname", ns)
            if title_node is not None:
                law_title = title_node.get("value")

    # Extract Articles
    # This matches generic 'article' tags in AKN
    articles = root.findall(".//akn:article", ns)
    
    actions = []
    
    for art in articles:
        art_id = art.get("eId")
        
        # Num
        num_node = art.find("akn:num", ns)
        art_num = num_node.text.strip() if num_node is not None else "Unknown"
        
        # Content (Flatten text)
        content_node = art.find("akn:content", ns)
        text = "".join(content_node.itertext()).strip() if content_node is not None else ""
        
        doc = {
            "law_id": os.path.basename(xml_path),
            "law_title": law_title,
            "article_id": art_id,
            "article_num": art_num,
            "text": text,
            "tags": [] # Placeholder for future NLP
        }
        
        # Index document
        es.index(index=INDEX_NAME, id=f"{law_title}-{art_id}", document=doc)
        
    print(f"Indexed {len(articles)} articles from {law_title}")

def main():
    try:
        es = connect_es()
        if not es.ping():
            print(f"Could not connect to Elasticsearch at {ES_HOST}")
            return
            
        create_index(es)
        
        # Find all XMLs
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "data/federal")
        xml_files = glob.glob(os.path.join(data_dir, "*.xml"))
        
        for xml in xml_files:
            parse_and_index(es, xml)
            
        print("Indexing Complete.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
