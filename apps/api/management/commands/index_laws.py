"""
Management command to index ALL laws (Federal & State) in Elasticsearch.
Parses V2 XML to extract rich hierarchy (Book, Title, Chapter).

Usage:
    python manage.py index_laws --all
    python manage.py index_laws --law-id federal_ley_123
"""

import re
from pathlib import Path
from lxml import etree
from django.core.management.base import BaseCommand
from elasticsearch import Elasticsearch, helpers
from apps.api.models import Law

# Elasticsearch config
ES_HOST = "http://elasticsearch:9200"
INDEX_NAME = "articles"

NS = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}

class Command(BaseCommand):
    help = 'Index laws in Elasticsearch with V2 hierarchy structure'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--all', action='store_true', help='Index all laws')
        group.add_argument('--law-id', type=str, help='Index specific law by official_id')
        
        parser.add_argument('--dry-run', action='store_true', help='No ES writes')
        parser.add_argument('--batch_size', type=int, default=500, help='Batch size')
        parser.add_argument('--limit', type=int, help='Limit number of laws to process')

    def _get_element_metadata(self, element, tag_name):
        """Extract num and heading from an ancestor tag (e.g., chapter)."""
        # Find the specific ancestor
        ancestor = element.xpath(f"ancestor::akn:{tag_name}", namespaces=NS)
        if not ancestor:
            return None
        
        node = ancestor[0]
        num = node.find('akn:num', NS)
        heading = node.find('akn:heading', NS)
        
        return {
            'num': num.text.strip() if num is not None and num.text else "",
            'heading': heading.text.strip() if heading is not None and heading.text else ""
        }

    def extract_articles_from_xml(self, xml_content, law_official_id):
        """Parse XML and extract articles with hierarchy."""
        try:
            root = etree.fromstring(xml_content.encode('utf-8'))
        except Exception as e:
            self.stderr.write(f"XML Parse Error for {law_official_id}: {e}")
            return []

        articles = []
        
        # Find all articles
        article_nodes = root.xpath('//akn:article', namespaces=NS)
        
        for node in article_nodes:
            # Basic Article Info
            eid = node.get('eId')
            num = node.find('akn:num', NS)
            content = node.find('akn:content', NS)
            
            if content is None:
                continue
                
            # Get text content recursively
            text_content = "".join(content.itertext()).strip()
            
            article_data = {
                'article_id': num.text.strip() if num is not None else eid,
                'eId': eid,
                'text': text_content,
                'book': self._get_element_metadata(node, 'book'),
                'title': self._get_element_metadata(node, 'title'),
                'chapter': self._get_element_metadata(node, 'chapter'),
                'part': self._get_element_metadata(node, 'part'),
                'section': self._get_element_metadata(node, 'section'),
            }
            articles.append(article_data)
            
        return articles

    def index_law(self, law, es, dry_run=False):
        """Index a single law."""
        version = law.versions.last() # Get latest
        if not version or not version.xml_file_path:
            return 0
            
        xml_path = Path('/app/' + version.xml_file_path)
        if not xml_path.exists():
            # Try relative to repo root if /app/ fails (local dev vs docker)
            if not xml_path.exists():
                # Fallback for local run
                xml_path = Path.cwd() / version.xml_file_path
                
        if not xml_path.exists():
            self.stdout.write(self.style.WARNING(f"XML not found for {law.official_id}: {xml_path}"))
            return 0

        # Read XML
        text = xml_path.read_text(encoding='utf-8')
        
        # Extract Structure
        extracted_articles = self.extract_articles_from_xml(text, law.official_id)
        
        if dry_run:
            self.stdout.write(f"Dry run: Would index {len(extracted_articles)} articles for {law.official_id}")
            return len(extracted_articles)

        # Prepare ES Docs
        actions = []
        for art in extracted_articles:
            
            # Format hierarchy for display/search
            hierarchy_breadcrumbs = []
            if art['title']: hierarchy_breadcrumbs.append(f"{art['title']['num']} {art['title']['heading']}")
            if art['chapter']: hierarchy_breadcrumbs.append(f"{art['chapter']['num']} {art['chapter']['heading']}")
            
            doc = {
                '_index': INDEX_NAME,
                '_source': {
                    'law_id': law.official_id,
                    'law_name': law.name,
                    'article': art['article_id'],
                    'text': art['text'],
                    'category': law.category,
                    'tier': law.tier,
                    'status': law.status,
                    
                    # Structural Fields
                    'book': art['book']['heading'] if art['book'] else None,
                    'title': art['title']['heading'] if art['title'] else None,
                    'chapter': art['chapter']['heading'] if art['chapter'] else None,
                    'hierarchy': hierarchy_breadcrumbs,
                    
                    'publication_date': version.publication_date.isoformat() if version.publication_date else None,
                    'tags': [law.tier, law.category.lower() if law.category else 'unknown']
                }
            }
            actions.append(doc)
            
        if actions:
            helpers.bulk(es, actions)
            
        return len(actions)

    def handle(self, *args, **options):
        # Connect ES
        if not options['dry_run']:
            es = Elasticsearch([ES_HOST])
            if not es.ping():
                self.stderr.write("Elasticsearch offline")
                return
        else:
            es = None

        # Select Laws
        if options['law_id']:
            laws = Law.objects.filter(official_id=options['law_id'])
        else:
            laws = Law.objects.all()

        if options.get('limit'):
            laws = laws[:options['limit']]

        total = laws.count()
        self.stdout.write(f"Indexing {total} laws...")

        count = 0
        total_articles = 0
        
        for law in laws:
            try:
                n = self.index_law(law, es, options['dry_run'])
                total_articles += n
                count += 1
                if count % 10 == 0:
                    self.stdout.write(f"Processed {count}/{total} laws...")
            except Exception as e:
                self.stderr.write(f"Error indexing {law.official_id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Done! Indexed {total_articles} articles from {count} laws."))
