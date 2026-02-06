"""
Management command to index ALL laws (Federal, State, Municipal) in Elasticsearch.
Parses V2 AKN XML to extract rich hierarchy (Book, Title, Chapter).
Falls back to raw text indexing for laws without AKN XML.

Usage:
    python manage.py index_laws --all
    python manage.py index_laws --all --create-indices
    python manage.py index_laws --law-id federal_ley_123
    python manage.py index_laws --all --tier state
"""

import re
from pathlib import Path

from django.core.management.base import BaseCommand
from elasticsearch import Elasticsearch, helpers
from lxml import etree

from apps.api.models import Law
from apps.api.utils.paths import ES_HOST, resolve_data_path_or_none

INDEX_LAWS = "laws"
INDEX_ARTICLES = "articles"

NS = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}


class Command(BaseCommand):
    help = "Index laws in Elasticsearch with V2 hierarchy structure"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--all", action="store_true", help="Index all laws")
        group.add_argument(
            "--law-id", type=str, help="Index specific law by official_id"
        )

        parser.add_argument("--dry-run", action="store_true", help="No ES writes")
        parser.add_argument("--batch-size", type=int, default=500, help="Batch size")
        parser.add_argument("--limit", type=int, help="Limit number of laws to process")
        parser.add_argument(
            "--create-indices",
            action="store_true",
            help="Create ES indices if they don't exist",
        )
        parser.add_argument(
            "--tier",
            type=str,
            choices=["federal", "state", "municipal", "all"],
            default="all",
            help="Filter by law tier (default: all)",
        )

    def _create_indices(self, es):
        """Create Elasticsearch indices with proper mappings."""
        # Laws index
        if not es.indices.exists(index=INDEX_LAWS):
            es.indices.create(
                index=INDEX_LAWS,
                body={
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {"type": "text", "analyzer": "spanish"},
                            "category": {"type": "keyword"},
                            "tier": {"type": "keyword"},
                            "state": {"type": "keyword"},
                            "municipality": {"type": "keyword"},
                            "publication_date": {"type": "date"},
                            "status": {"type": "keyword"},
                            "total_articles": {"type": "integer"},
                        }
                    }
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Created index: {INDEX_LAWS}"))

        # Articles index
        if not es.indices.exists(index=INDEX_ARTICLES):
            es.indices.create(
                index=INDEX_ARTICLES,
                body={
                    "settings": {
                        "analysis": {
                            "analyzer": {
                                "spanish_legal": {
                                    "type": "spanish",
                                    "stopwords": "_spanish_",
                                }
                            }
                        }
                    },
                    "mappings": {
                        "properties": {
                            "law_id": {"type": "keyword"},
                            "law_name": {"type": "text", "analyzer": "spanish"},
                            "article": {"type": "keyword"},
                            "text": {"type": "text", "analyzer": "spanish"},
                            "category": {"type": "keyword"},
                            "tier": {"type": "keyword"},
                            "state": {"type": "keyword"},
                            "municipality": {"type": "keyword"},
                            "book": {"type": "text"},
                            "title": {"type": "text"},
                            "chapter": {"type": "text"},
                            "hierarchy": {"type": "keyword"},
                            "publication_date": {"type": "date"},
                            "tags": {"type": "keyword"},
                        }
                    },
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Created index: {INDEX_ARTICLES}"))

    def _get_element_metadata(self, element, tag_name):
        """Extract num and heading from an ancestor tag (e.g., chapter)."""
        ancestor = element.xpath(f"ancestor::akn:{tag_name}", namespaces=NS)
        if not ancestor:
            return None

        node = ancestor[0]
        num = node.find("akn:num", NS)
        heading = node.find("akn:heading", NS)

        return {
            "num": num.text.strip() if num is not None and num.text else "",
            "heading": (
                heading.text.strip() if heading is not None and heading.text else ""
            ),
        }

    def _extract_article_text(self, node):
        """Extract article text preserving paragraph structure.

        - Extracts from <p> elements (semantic paragraphs) instead of raw itertext()
        - Skips <note> children (reform notices like "Artículo reformado DOF 07-06-2024")
        - Strips duplicated article number from paragraph body
        - Rejoins mid-sentence line breaks while preserving intentional breaks
        - Joins paragraphs with double newline for clear visual separation
        """
        paragraphs = []
        for p_elem in node.xpath(".//akn:p", namespaces=NS):
            # Skip <p> inside <note> (reform notices)
            if any(anc.tag.endswith("note") for anc in p_elem.iterancestors()):
                continue
            raw = "".join(p_elem.itertext()).strip()
            if not raw:
                continue
            # Remove repeated article number from paragraph start
            cleaned = re.sub(r"^(?:Art[ií]culo|ARTÍCULO)\s+\d+[\w\s]*\.\s*", "", raw)
            # Rejoin mid-sentence hard line breaks (column wraps from PDF)
            cleaned = re.sub(
                r"(?<=[a-záéíóúñü,;])\n(?=[a-záéíóúñü])",
                " ",
                cleaned,
                flags=re.IGNORECASE,
            )
            # Collapse multiple spaces
            cleaned = re.sub(r" {2,}", " ", cleaned)
            paragraphs.append(cleaned.strip())

        if not paragraphs:
            # Fallback for articles without <p> elements
            raw = "".join(node.itertext()).strip()
            num_el = node.find("akn:num", namespaces=NS)
            if num_el is not None and num_el.text:
                raw = raw.replace(num_el.text.strip(), "", 1).strip()
            return raw

        return "\n\n".join(paragraphs)

    def extract_articles_from_xml(self, xml_content, law_official_id):
        """Parse AKN XML and extract articles with hierarchy."""
        try:
            root = etree.fromstring(xml_content.encode("utf-8"))
        except Exception as e:
            self.stderr.write(f"XML Parse Error for {law_official_id}: {e}")
            return []

        articles = []
        article_nodes = root.xpath("//akn:article", namespaces=NS)

        for node in article_nodes:
            eid = node.get("eId")
            num = node.find("akn:num", NS)

            # Clean article_id: strip "Artículo " prefix and trailing period
            raw_num = num.text.strip() if num is not None and num.text else eid
            article_id = (
                re.sub(r"^(?:Art[ií]culo|ARTÍCULO)\s*", "", raw_num).rstrip(".").strip()
            )

            # Extract structured text
            text_content = self._extract_article_text(node)

            if not text_content:
                continue

            article_data = {
                "article_id": article_id,
                "eId": eid,
                "text": text_content,
                "book": self._get_element_metadata(node, "book"),
                "title": self._get_element_metadata(node, "title"),
                "chapter": self._get_element_metadata(node, "chapter"),
                "part": self._get_element_metadata(node, "part"),
                "section": self._get_element_metadata(node, "section"),
            }
            articles.append(article_data)

        return articles

    def _index_law_doc(self, law, version, article_count, es, dry_run=False):
        """Index the law-level document into the laws index."""
        if dry_run:
            return

        doc = {
            "_index": INDEX_LAWS,
            "_id": law.official_id,
            "_source": {
                "id": law.official_id,
                "name": law.name,
                "category": law.category or "unknown",
                "tier": law.tier or "federal",
                "state": law.state or "",
                "municipality": law.municipality or "",
                "publication_date": (
                    version.publication_date.isoformat()
                    if version.publication_date
                    else None
                ),
                "status": "active",
                "total_articles": article_count,
            },
        }
        helpers.bulk(es, [doc])

    def _index_raw_text(self, law, version, text, es, dry_run=False):
        """Index raw text as a single article (degraded but searchable)."""
        if dry_run:
            self.stdout.write(
                f"Dry run: Would index raw text for {law.official_id} "
                f"({len(text):,} chars)"
            )
            return 1

        doc = {
            "_index": INDEX_ARTICLES,
            "_id": f"{law.official_id}-full_text",
            "_source": {
                "law_id": law.official_id,
                "law_name": law.name,
                "article": "full_text",
                "text": text[:50000],  # Cap at 50KB to avoid ES limits
                "category": law.category or "unknown",
                "tier": law.tier or "state",
                "state": law.state or "",
                "municipality": law.municipality or "",
                "book": None,
                "title": None,
                "chapter": None,
                "hierarchy": [],
                "publication_date": (
                    version.publication_date.isoformat()
                    if version.publication_date
                    else None
                ),
                "tags": [
                    law.tier or "unknown",
                    (law.category or "unknown").lower(),
                    "raw_text",
                ],
            },
        }
        helpers.bulk(es, [doc])

        # Also index law-level doc
        self._index_law_doc(law, version, 0, es, dry_run)

        return 1

    def index_law(self, law, es, dry_run=False):
        """Index a single law with articles or raw text fallback."""
        version = law.versions.last()
        if not version or not version.xml_file_path:
            return 0

        file_path = resolve_data_path_or_none(version.xml_file_path)

        if not file_path:
            self.stdout.write(
                self.style.WARNING(
                    f"File not found for {law.official_id}: {version.xml_file_path}"
                )
            )
            return 0

        # Read file content
        text = file_path.read_text(encoding="utf-8")

        # Check if this is AKN XML or raw text
        is_akn = text.strip().startswith("<?xml") or "<akomaNtoso" in text[:500]

        if not is_akn:
            return self._index_raw_text(law, version, text, es, dry_run)

        # Extract articles from AKN XML
        extracted_articles = self.extract_articles_from_xml(text, law.official_id)

        if dry_run:
            self.stdout.write(
                f"Dry run: Would index {len(extracted_articles)} articles "
                f"for {law.official_id}"
            )
            return len(extracted_articles)

        # Prepare ES article docs
        actions = []
        for art in extracted_articles:
            hierarchy_breadcrumbs = []
            if art["title"]:
                hierarchy_breadcrumbs.append(
                    f"{art['title']['num']} {art['title']['heading']}"
                )
            if art["chapter"]:
                hierarchy_breadcrumbs.append(
                    f"{art['chapter']['num']} {art['chapter']['heading']}"
                )

            doc = {
                "_index": INDEX_ARTICLES,
                "_id": f"{law.official_id}-{art['article_id']}",
                "_source": {
                    "law_id": law.official_id,
                    "law_name": law.name,
                    "article": art["article_id"],
                    "text": art["text"],
                    "category": law.category or "unknown",
                    "tier": law.tier or "federal",
                    "state": law.state or "",
                    "municipality": law.municipality or "",
                    "book": art["book"]["heading"] if art["book"] else None,
                    "title": art["title"]["heading"] if art["title"] else None,
                    "chapter": art["chapter"]["heading"] if art["chapter"] else None,
                    "hierarchy": hierarchy_breadcrumbs,
                    "publication_date": (
                        version.publication_date.isoformat()
                        if version.publication_date
                        else None
                    ),
                    "tags": [
                        law.tier or "federal",
                        (law.category or "unknown").lower(),
                    ],
                },
            }
            actions.append(doc)

        if actions:
            helpers.bulk(es, actions)

        # Index law-level document
        self._index_law_doc(law, version, len(actions), es, dry_run)

        return len(actions)

    def handle(self, *args, **options):
        # Connect ES
        if not options["dry_run"]:
            es = Elasticsearch([ES_HOST])
            if not es.ping():
                self.stderr.write(f"Elasticsearch offline at {ES_HOST}")
                return
            self.stdout.write(f"Connected to Elasticsearch at {ES_HOST}")

            # Create indices if requested
            if options["create_indices"]:
                self._create_indices(es)
        else:
            es = None

        # Select Laws
        if options["law_id"]:
            laws = Law.objects.filter(official_id=options["law_id"])
        else:
            laws = Law.objects.all()

        # Filter by tier
        tier = options.get("tier", "all")
        if tier and tier != "all":
            laws = laws.filter(tier=tier)

        if options.get("limit"):
            laws = laws[: options["limit"]]

        total = laws.count()
        self.stdout.write(f"Indexing {total} laws (tier={tier})...")

        count = 0
        total_articles = 0
        skipped = 0
        raw_text_count = 0

        for law in laws:
            try:
                n = self.index_law(law, es, options["dry_run"])
                if n == 0:
                    skipped += 1
                else:
                    total_articles += n
                count += 1
                if count % 50 == 0:
                    self.stdout.write(
                        f"  Processed {count}/{total} laws "
                        f"({total_articles} articles)..."
                    )
            except Exception as e:
                self.stderr.write(f"Error indexing {law.official_id}: {e}")

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Indexed {total_articles} articles from {count} laws."
            )
        )
        if skipped:
            self.stdout.write(f"Skipped {skipped} laws (no file found)")
        self.stdout.write("=" * 60)
