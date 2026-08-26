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

import logging
import re

from django.core.management.base import BaseCommand
from elasticsearch import Elasticsearch, helpers
from lxml import etree

from apps.api.es_index_manager import (
    create_versioned_index,
    ensure_alias_exists,
    get_current_index,
    swap_alias,
)
from apps.api.models import Law
from apps.api.utils.paths import ES_HOST, read_data_content

logger = logging.getLogger(__name__)

INDEX_LAWS = "laws"
INDEX_ARTICLES = "articles"

NS = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}

# Prefix applied to transitorio article ids so they never collide with the
# id of a substantive article that happens to share the same ordinal number.
# See extract_articles_from_xml / _derive_article_id for the rationale.
TRANSITORIO_ID_PREFIX = "T-"

# Spanish ordinal words used to number transitorio provisions ("Primero.-",
# "Octavo.", "Décimo Segundo", "Único"). A bare <num> that is one of these —
# with no "Artículo" prefix and no digits — signals a transitorio node whose
# derived id would otherwise be a plain integer (via the parser's id="trans-N")
# and collide with the substantive article of the same number.
_ORDINAL_WORD_RE = re.compile(
    r"^(?:"
    r"primer|segund|tercer|cuart|quint|sext|s[ée]ptim|octav|noven|"
    r"d[ée]cim|und[ée]cim|duod[ée]cim|vig[ée]sim|trig[ée]sim|"
    r"cuadrag[ée]sim|quincuag[ée]sim|[úu]ltim|[úu]nic"
    r")[oa]s?\b",
    re.IGNORECASE,
)


class Command(BaseCommand):
    help = "Index laws in Elasticsearch with V2 hierarchy structure"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--all", action="store_true", help="Index all laws")
        group.add_argument(
            "--law-id", type=str, help="Index specific law by official_id"
        )

        parser.add_argument("--dry-run", action="store_true", help="No ES writes")
        parser.add_argument(
            "--batch-size", type=int, default=50, help="Batch size for ES indexing"
        )
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
        parser.add_argument(
            "--reindex",
            action="store_true",
            help="Create new versioned index, bulk index into it, then swap alias",
        )
        parser.add_argument(
            "--migrate-alias",
            action="store_true",
            help="One-time migration: convert concrete 'articles' index to alias",
        )
        parser.add_argument(
            "--include-quarantined",
            action="store_true",
            help="Include laws with quarantined quality grades (D/F) in indexing",
        )
        parser.add_argument(
            "--with-embeddings",
            action="store_true",
            help="Generate text embeddings for semantic search (requires sentence-transformers)",
        )

    def _create_indices(self, es):
        """Create Elasticsearch indices with proper mappings."""
        # Laws index
        if not es.indices.exists(index=INDEX_LAWS):
            es.indices.create(
                index=INDEX_LAWS,
                mappings={
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {"type": "text", "analyzer": "spanish"},
                        "category": {"type": "keyword"},
                        "domains": {"type": "keyword"},
                        "tier": {"type": "keyword"},
                        "state": {"type": "keyword"},
                        "municipality": {"type": "keyword"},
                        "publication_date": {"type": "date"},
                        "status": {"type": "keyword"},
                        "total_articles": {"type": "integer"},
                    }
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Created index: {INDEX_LAWS}"))

        # Articles index
        if not es.indices.exists(index=INDEX_ARTICLES):
            es.indices.create(
                index=INDEX_ARTICLES,
                settings={
                    "analysis": {
                        "filter": {
                            "spanish_legal_synonyms": {
                                "type": "synonym",
                                "synonyms": [
                                    "ley, legislación, ordenamiento",
                                    "amparo, protección, tutela",
                                    "constitución, carta magna, ley fundamental",
                                    "código, codificación",
                                    "reglamento, regulación, normativa",
                                    "decreto, disposición",
                                    "artículo, numeral, precepto",
                                    "tribunal, juzgado, corte",
                                    "juicio, proceso, litigio, procedimiento",
                                    "demanda, acción, pretensión",
                                    "sentencia, resolución, fallo",
                                    "recurso, impugnación, medio de defensa",
                                    "NOM, norma oficial mexicana",
                                    "DOF, diario oficial de la federación",
                                    "CPEUM, constitución política de los estados unidos mexicanos",
                                    "LISR, ley del impuesto sobre la renta",
                                    "LIVA, ley del impuesto al valor agregado",
                                    "CFF, código fiscal de la federación",
                                    "LFTR, ley federal de telecomunicaciones y radiodifusión",
                                    "obligación, deber",
                                    "derecho, facultad, potestad",
                                    "sanción, multa, penalidad",
                                    "contrato, convenio, acuerdo",
                                    "propiedad, dominio, posesión",
                                    # Procedural
                                    "actor, demandante, promovente",
                                    "demandado, emplazado, parte contraria",
                                    "auto, providencia, acuerdo judicial",
                                    "notificación, emplazamiento, citación",
                                    "prueba, evidencia, medio probatorio",
                                    # Constitutional
                                    "garantías, derechos humanos, derechos fundamentales",
                                    "federalismo, pacto federal, sistema federal",
                                    "soberanía, poder constituyente, supremacía",
                                    # Commercial
                                    "sociedad, empresa, persona moral",
                                    "quiebra, concurso mercantil, insolvencia",
                                    "pagaré, título de crédito, letra de cambio",
                                    "marca, patente, propiedad industrial",
                                    # Tax
                                    "contribución, impuesto, tributo, gravamen",
                                    "deducción, acreditamiento, compensación",
                                    "contribuyente, sujeto pasivo, causante",
                                    # Administrative
                                    "licitación, concurso, adjudicación",
                                    "concesión, permiso, autorización, licencia",
                                ],
                            },
                            "spanish_stop": {
                                "type": "stop",
                                "stopwords": "_spanish_",
                            },
                            "spanish_stemmer": {
                                "type": "stemmer",
                                "language": "light_spanish",
                            },
                            "accent_folding": {
                                "type": "asciifolding",
                                "preserve_original": True,
                            },
                        },
                        "analyzer": {
                            "spanish_legal": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "spanish_legal_synonyms",
                                    "spanish_stop",
                                    "spanish_stemmer",
                                    "accent_folding",
                                ],
                            },
                        },
                    },
                    "index": {
                        "number_of_replicas": 0,
                    },
                },
                mappings={
                    "properties": {
                        "law_id": {"type": "keyword"},
                        "law_name": {
                            "type": "text",
                            "analyzer": "spanish_legal",
                            "fields": {
                                "keyword": {"type": "keyword"},
                            },
                        },
                        "article": {"type": "keyword"},
                        "text": {
                            "type": "text",
                            "analyzer": "spanish_legal",
                        },
                        "category": {"type": "keyword"},
                        "domains": {"type": "keyword"},
                        "tier": {"type": "keyword"},
                        "law_type": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "is_transitorio": {"type": "boolean"},
                        "state": {"type": "keyword"},
                        "municipality": {"type": "keyword"},
                        "book": {"type": "text", "analyzer": "spanish_legal"},
                        "title": {"type": "text", "analyzer": "spanish_legal"},
                        "chapter": {"type": "text", "analyzer": "spanish_legal"},
                        "hierarchy": {"type": "keyword"},
                        "publication_date": {"type": "date"},
                        "tags": {"type": "keyword"},
                        "suggest": {
                            "type": "completion",
                            "analyzer": "simple",
                        },
                        "text_embedding": {
                            "type": "dense_vector",
                            "dims": 768,
                            "index": True,
                            "similarity": "cosine",
                        },
                    }
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

    @staticmethod
    def _node_id(node):
        """Return the node's stable id attribute, tolerating eId or id.

        The AKN generators (akn_generator_v2, bluebell) emit an ``id``
        attribute; some sources emit the AKN-3.0 ``eId``. Read both so the
        transitorio detector works regardless of which one is present.
        """
        return node.get("eId") or node.get("id") or ""

    def _is_transitorio(self, node, num_text, has_numeric_articles=True):
        """Decide whether an <article> node is a transitorio provision.

        Transitorios are numbered with ordinals ("Primero.-", "Octavo.") and,
        when parsed by akn_generator_v2, carry ``id="trans-N"``. They live in a
        DISPOSICIONES/ARTÍCULOS TRANSITORIOS section appended after the main
        body. Because they are serialised as <article> nodes just like
        substantive articles, their derived id (a bare number) collides with the
        substantive article of the same number and ES silently overwrites one.

        Detection is layered, preferring the AKN structure over string matching:
          1. The node's own id/eId begins with a transitorio marker
             ("trans", "transitorio", "disp-trans", "dt"). This is the parser's
             canonical signal (akn_generator_v2 emits id="trans-N").
          2. An ancestor container (section/hcontainer/chapter/title/part) is
             headed/numbered "Transitorios" / "Disposiciones Transitorias".
          3. Fallback heuristic: the <num> is a bare Spanish ordinal word
             ("Octavo", "Décimo Segundo") with no "Artículo" prefix and no
             digits. This ONLY applies when the document also contains
             substantive "Artículo N" articles — i.e. the real collision
             scenario. Instruments that number every substantive provision with
             ordinals (JCF Reglas de Operación, Lineamientos, Acuerdos) have NO
             "Artículo N" articles, so their ordinals are the primary scheme and
             must be preserved verbatim, never namespaced.
        """
        node_id = self._node_id(node).lower()
        if re.match(r"^(?:trans|transitori|disp[-_]?trans|dt[-_])", node_id):
            return True

        # Walk ancestor containers looking for a "Transitorios" heading/num.
        for tag in ("section", "hcontainer", "chapter", "title", "part", "book"):
            for anc in node.xpath(f"ancestor::akn:{tag}", namespaces=NS):
                anc_id = (anc.get("eId") or anc.get("id") or "").lower()
                if re.search(r"transitori", anc_id):
                    return True
                for child_tag in ("heading", "num"):
                    child = anc.find(f"akn:{child_tag}", NS)
                    if (
                        child is not None
                        and child.text
                        and re.search(r"transitori", child.text, re.IGNORECASE)
                    ):
                        return True

        # Fallback: bare ordinal num — only when substantive "Artículo N"
        # articles coexist (otherwise ordinals ARE the article scheme, e.g.
        # JCF Reglas: PRIMERA, SEGUNDA, DÉCIMA QUINTA).
        if has_numeric_articles and num_text:
            stripped = num_text.strip()
            has_articulo = re.match(r"^(?:Art[ií]culo|ARTÍCULO)\b", stripped)
            has_digit = re.search(r"\d", stripped)
            if not has_articulo and not has_digit and _ORDINAL_WORD_RE.match(stripped):
                return True

        return False

    @staticmethod
    def _document_has_numeric_articles(article_nodes):
        """True if any <article> is numbered "Artículo N" (a substantive,
        digit-numbered article). Distinguishes real laws — where bare ordinals
        signal transitorios — from ordinal-only instruments (Reglas,
        Lineamientos) where ordinals are the substantive numbering scheme."""
        for node in article_nodes:
            num = node.find("akn:num", NS)
            if num is not None and num.text and re.search(r"\d", num.text):
                return True
        return False

    def _derive_article_id(self, node, has_numeric_articles=True):
        """Derive a stable, collision-free article id for an <article> node.

        For substantive articles this is the article number ("8", "27-A").
        For transitorios it is namespaced with ``TRANSITORIO_ID_PREFIX`` so
        ``lfpdppp-8`` (substantive) and ``lfpdppp-T-8`` (the "Octavo"
        transitorio) are distinct ES documents that both survive indexing.

        Returns a tuple ``(article_id, is_transitorio)``.
        """
        num = node.find("akn:num", NS)
        num_text = num.text.strip() if num is not None and num.text else ""
        raw = num_text or self._node_id(node)

        is_transitorio = self._is_transitorio(node, num_text, has_numeric_articles)

        # Base id: strip the "Artículo" prefix and trailing period.
        base = re.sub(r"^(?:Art[ií]culo|ARTÍCULO)\s*", "", raw).rstrip(".").strip()

        if is_transitorio:
            # Prefer the numeric ordinal (from id="trans-N" or an ordinal word)
            # so distinct transitorios get distinct ids; fall back to the ordinal
            # text itself when no number is available.
            trans_num = ""
            node_id = self._node_id(node)
            m = re.search(r"(\d+)$", node_id)
            if m:
                trans_num = m.group(1)
            else:
                from apps.parsers.patterns.articles import ordinal_to_number

                mapped = ordinal_to_number(base) if base else None
                trans_num = str(mapped) if mapped is not None else base
            article_id = f"{TRANSITORIO_ID_PREFIX}{trans_num or base}".strip()
            # Guard against an empty/degenerate id.
            if article_id == TRANSITORIO_ID_PREFIX:
                article_id = f"{TRANSITORIO_ID_PREFIX}{node_id or 'x'}"
            return article_id, True

        return base, False

    def extract_articles_from_xml(self, xml_content, law_official_id):
        """Parse AKN XML and extract articles with hierarchy.

        Transitorio provisions are namespaced (see _derive_article_id) so their
        Elasticsearch ``_id`` never collides with a substantive article of the
        same ordinal number. A defensive de-duplication pass additionally
        guarantees that if two nodes still derive the same id (e.g. a reform
        decree that re-uses substantive article numbers and is not cleanly
        marked as transitorio in the source XML), later nodes are suffixed
        rather than silently overwriting earlier ones downstream in ES.
        """
        try:
            root = etree.fromstring(xml_content.encode("utf-8"))
        except Exception as e:
            self.stderr.write(f"XML Parse Error for {law_official_id}: {e}")
            return []

        articles = []
        seen_ids: dict = {}
        article_nodes = root.xpath("//akn:article", namespaces=NS)

        # Document-level context: only when substantive "Artículo N" articles
        # exist do bare ordinals signal transitorios (see _is_transitorio).
        has_numeric_articles = self._document_has_numeric_articles(article_nodes)

        for node in article_nodes:
            eid = node.get("eId") or node.get("id")
            article_id, is_transitorio = self._derive_article_id(
                node, has_numeric_articles
            )

            # Extract structured text
            text_content = self._extract_article_text(node)

            if not text_content:
                continue

            # Defensive de-dup: never let two articles resolve to the same id.
            if article_id in seen_ids:
                seen_ids[article_id] += 1
                deduped = f"{article_id}-dup{seen_ids[article_id]}"
                self.stderr.write(
                    f"Duplicate article id '{article_id}' in {law_official_id}; "
                    f"reindexing second occurrence as '{deduped}' to avoid overwrite"
                )
                article_id = deduped
            else:
                seen_ids[article_id] = 0

            article_data = {
                "article_id": article_id,
                "eId": eid,
                "is_transitorio": is_transitorio,
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
                "domains": law.domains or [],
                "tier": law.tier or "federal",
                "state": law.state or "",
                "municipality": law.municipality or "",
                "publication_date": (
                    version.publication_date.isoformat()
                    if version.publication_date
                    else None
                ),
                # Reflect the Law's real status (vigente/abrogada/derogada/unknown)
                # instead of a blanket "active" — the hardcode contradicted the
                # status the article-level docs carry and the db_saver fix.
                "status": law.status or "unknown",
                "total_articles": article_count,
                "suggest": {
                    "input": [law.name] + ([law.short_name] if law.short_name else []),
                },
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
                "domains": law.domains or [],
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
                "law_type": law.law_type or "legislative",
                "status": law.status or "unknown",
            },
        }
        helpers.bulk(es, [doc])

        # Also index law-level doc
        self._index_law_doc(law, version, 0, es, dry_run)

        return 1

    def index_law(self, law, es, dry_run=False, embedding_generator=None):
        """Index a single law with articles or raw text fallback."""
        # LawVersion.Meta.ordering = ["-publication_date"] (descending), so
        # .first() is the NEWEST version. Using .last() here previously indexed
        # the OLDEST version, serving superseded text for amended laws.
        version = law.versions.first()
        if not version or not version.xml_file_path:
            return 0

        text = read_data_content(version.xml_file_path)

        if not text:
            self.stdout.write(
                self.style.WARNING(
                    f"File not found for {law.official_id}: {version.xml_file_path}"
                )
            )
            return 0

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
                    "domains": law.domains or [],
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
                    ]
                    + (["transitorio"] if art.get("is_transitorio") else []),
                    "law_type": law.law_type or "legislative",
                    "status": law.status or "unknown",
                    "is_transitorio": bool(art.get("is_transitorio")),
                },
            }
            # Add embedding if generator is available
            if embedding_generator and art["text"]:
                try:
                    doc["_source"]["text_embedding"] = embedding_generator.generate(
                        art["text"]
                    )
                except Exception:
                    logger.debug(
                        "Embedding generation failed for article in %s; indexing without it",
                        law.official_id,
                        exc_info=True,
                    )

            actions.append(doc)

        if actions:
            helpers.bulk(es, actions)

        # Index law-level document
        self._index_law_doc(law, version, len(actions), es, dry_run)

        return len(actions)

    def handle(self, *args, **options):
        global INDEX_ARTICLES

        # Connect ES
        if not options["dry_run"]:
            es = Elasticsearch([ES_HOST])
            if not es.ping():
                self.stderr.write(f"Elasticsearch offline at {ES_HOST}")
                return
            self.stdout.write(f"Connected to Elasticsearch at {ES_HOST}")

            # One-time migration from concrete index to alias
            if options["migrate_alias"]:
                self.stdout.write("Migrating concrete index to alias...")
                migrated = ensure_alias_exists(es)
                if migrated:
                    self.stdout.write(self.style.SUCCESS("Migration complete"))
                else:
                    self.stdout.write(
                        "No migration needed (alias already exists or no index found)"
                    )
                return

            # Reindex mode: create new versioned index and swap alias after indexing
            reindex_new_index = None
            reindex_old_index = None
            if options["reindex"]:
                reindex_old_index = get_current_index(es)
                # Get mappings/settings from current articles index for the new versioned index
                articles_settings = None
                articles_mappings = None
                if es.indices.exists(index=INDEX_ARTICLES) or (
                    reindex_old_index and es.indices.exists(index=reindex_old_index)
                ):
                    source_index = reindex_old_index or INDEX_ARTICLES
                    info = es.indices.get(index=source_index)
                    idx_info = info[source_index]
                    articles_mappings = idx_info.get("mappings")
                    raw_settings = idx_info.get("settings", {}).get("index", {})
                    # Strip read-only settings
                    for key in [
                        "creation_date",
                        "uuid",
                        "version",
                        "provided_name",
                        "number_of_replicas",
                        "number_of_shards",
                    ]:
                        raw_settings.pop(key, None)
                    articles_settings = raw_settings if raw_settings else None

                # Fall back to default mapping/settings when no source index exists
                # (e.g. fresh ES instance). Without this, dynamic mapping creates
                # keyword fields as text, breaking aggregations.
                if not articles_mappings:
                    self._create_indices(es)
                    if es.indices.exists(index=INDEX_ARTICLES):
                        info = es.indices.get(index=INDEX_ARTICLES)
                        idx_info = info[INDEX_ARTICLES]
                        articles_mappings = idx_info.get("mappings")
                        raw_settings = idx_info.get("settings", {}).get("index", {})
                        for key in [
                            "creation_date",
                            "uuid",
                            "version",
                            "provided_name",
                            "number_of_replicas",
                            "number_of_shards",
                        ]:
                            raw_settings.pop(key, None)
                        articles_settings = raw_settings if raw_settings else None
                        # Remove the temporary index — reindex will create a versioned one
                        es.indices.delete(index=INDEX_ARTICLES)

                reindex_new_index = create_versioned_index(
                    es,
                    mappings=articles_mappings,
                    settings=articles_settings,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Created versioned index: {reindex_new_index}")
                )
                # Override INDEX_ARTICLES so all indexing goes to the new index
                INDEX_ARTICLES = reindex_new_index

            # Create indices if requested
            if options["create_indices"]:
                self._create_indices(es)
        else:
            es = None
            reindex_new_index = None
            reindex_old_index = None

        # Initialize embedding generator if requested
        embedding_generator = None
        if options.get("with_embeddings"):
            try:
                from apps.parsers.embeddings import EmbeddingGenerator

                embedding_generator = EmbeddingGenerator()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Embedding generator loaded ({embedding_generator.dimensions}-dim)"
                    )
                )
            except ImportError:
                self.stderr.write(
                    "sentence-transformers not installed. "
                    "Run: poetry install -E embeddings"
                )
                return

        # Select Laws
        if options["law_id"]:
            laws = Law.objects.filter(official_id=options["law_id"])
        else:
            laws = Law.objects.all()

        # Filter by tier
        tier = options.get("tier", "all")
        if tier and tier != "all":
            laws = laws.filter(tier=tier)

        # Exclude quarantined laws (D/F quality grades) unless --include-quarantined
        if not options.get("include_quarantined"):
            try:
                from django.conf import settings as django_settings

                quarantine_grades = getattr(
                    django_settings, "QUALITY_QUARANTINE_GRADES", ["D", "F"]
                )
                quarantined_qs = laws.filter(
                    versions__quality_grade__in=quarantine_grades
                ).distinct()
                quarantined_count = quarantined_qs.count()
                if quarantined_count > 0:
                    laws = laws.exclude(versions__quality_grade__in=quarantine_grades)
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping {quarantined_count} quarantined laws "
                            f"(grades: {', '.join(quarantine_grades)}). "
                            f"Use --include-quarantined to override."
                        )
                    )
            except (
                Exception
            ):  # noqa: BLE001 — pre-migration schemas may lack quality_grade column
                logger.debug(
                    "quarantine filter skipped (DB schema not migrated)", exc_info=True
                )

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
                n = self.index_law(law, es, options["dry_run"], embedding_generator)
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

        # Swap alias to new versioned index after successful indexing
        if reindex_new_index and not options["dry_run"]:
            swap_alias(es, old_index=reindex_old_index, new_index=reindex_new_index)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Swapped alias: {reindex_old_index or '(none)'} -> {reindex_new_index}"
                )
            )

        self.stdout.write("=" * 60)
