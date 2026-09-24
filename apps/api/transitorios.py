"""Transitorio detection and collision-free article ids for the article index.

Transitorio provisions ("Primero.-", "Octavo.", "Décimo Segundo.-") are
numbered with ordinals that map onto the same integers as the substantive
articles of the law. The Elasticsearch ``_id`` of an article document is
``"{law}-{article}"``, so a transitorio that derives the id ``"8"`` silently
overwrites substantive Artículo 8 (last write wins). That is the LFPDPPP
collision of #218 / #222: ``lfpdppp-8`` served the "Octavo" transitorio instead
of the sensitive-data consent article.

Id scheme (public; the API exposes it as ``article_id``):

* substantive articles keep their number verbatim: ``"8"``, ``"27-A"``;
* transitorios of the law's own decree: ``"T-8"`` (``TRANSITORIO_ID_PREFIX``);
* transitorios of the N-th later decree block (reform decrees appended after
  the first TRANSITORIOS section, each restarting at "Primero"):
  ``"T-R2-1"``, ``"T-R3-4"``. Every transitorio id starts with ``"T-"``.

This module is pure (lxml + re, no Django) so it can be unit-tested directly
and reused by any indexer.
"""

import re

from apps.parsers.patterns.articles import ordinal_to_number
from apps.parsers.patterns.structure import TRANSITORIO_ORDINAL_PATTERN

NS = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}

TRANSITORIO_ID_PREFIX = "T-"
REFORM_BLOCK_MARK = "R"

KIND_ARTICULO = "articulo"
KIND_TRANSITORIO = "transitorio"

# Spanish ordinal words used to number transitorio provisions. A bare <num>
# that is one of these — no "Artículo" prefix, no digits — signals a
# transitorio node whose derived id would otherwise collide with the
# substantive article of the same number.
_ORDINAL_WORD_RE = re.compile(
    r"^(?:"
    r"primer|segund|tercer|cuart|quint|sext|s[ée]ptim|octav|noven|"
    r"d[ée]cim|und[ée]cim|duod[ée]cim|vig[ée]sim|trig[ée]sim|"
    r"cuadrag[ée]sim|quincuag[ée]sim|sexag[ée]sim|septuag[ée]sim|"
    r"octog[ée]sim|nonag[ée]sim|[úu]ltim|[úu]nic"
    r")[oa]s?\b",
    re.IGNORECASE,
)

# An ordinal heading at the start of a provision's TEXT ("Octavo.- Los
# registros…", "Décimo Primero.- …", "Primero. El presente…"). Shared with the
# parser (apps.parsers.patterns.structure) so both layers agree on what a
# transitorio heading is. Requires the "." delimiter right after the ordinal
# phrase, so a wrapped line like "Décimo Tercero del presente Decreto" is NOT
# a heading.
_TEXT_HEADING_RE = re.compile(TRANSITORIO_ORDINAL_PATTERN, re.IGNORECASE)

_NODE_ID_TRANS_RE = re.compile(r"^(?:trans|transitori|disp[-_]?trans|dt[-_])")
_NODE_ID_BLOCK_RE = re.compile(r"[-_]r(\d+)[-_](\d+)$", re.IGNORECASE)
_TRANSITORIO_ARTICLE_ID_RE = re.compile(r"^T-")

# Leading characters compared when deciding whether two transitorio texts are
# the same provision parsed twice (legacy XMLs carry some transitorios both as
# a proper trans-N node and as an ordinal-headed article node).
_SAME_PROVISION_PREFIX = 160


def transitorio_id(number, block=1):
    """Public article id for transitorio ``number`` of decree ``block``."""
    if block and int(block) > 1:
        return f"{TRANSITORIO_ID_PREFIX}{REFORM_BLOCK_MARK}{int(block)}-{number}"
    return f"{TRANSITORIO_ID_PREFIX}{number}"


def article_kind(source):
    """``"transitorio"`` or ``"articulo"`` for an article ES ``_source``.

    Prefers the indexed ``is_transitorio`` flag; documents indexed before the
    flag existed fall back to the id scheme (every transitorio id is ``T-…``).
    """
    flag = source.get("is_transitorio")
    if flag is None:
        flag = bool(_TRANSITORIO_ARTICLE_ID_RE.match(str(source.get("article") or "")))
    return KIND_TRANSITORIO if flag else KIND_ARTICULO


def node_id(node):
    """The node's stable id attribute (AKN-3.0 ``eId`` or generator ``id``)."""
    return node.get("eId") or node.get("id") or ""


def document_has_numeric_articles(article_nodes):
    """True if any <article> <num> carries a digit ("Artículo 8").

    Distinguishes real laws — where bare ordinals signal transitorios — from
    ordinal-only instruments (Reglas, Lineamientos) where ordinals ARE the
    substantive numbering scheme and must never be namespaced.
    """
    for node in article_nodes:
        num = node.find("akn:num", NS)
        if num is not None and num.text and re.search(r"\d", num.text):
            return True
    return False


def is_transitorio_node(node, num_text, has_numeric_articles=True):
    """Decide whether an <article> node is a transitorio provision.

    Layered, preferring AKN structure over string matching:
      1. the node id starts with a transitorio marker (the parser emits
         ``id="trans-N"`` / ``id="trans-rK-N"``);
      2. an ancestor container is headed/numbered "Transitorios";
      3. fallback: the <num> is a bare Spanish ordinal word — only when the
         document also has digit-numbered articles (see
         ``document_has_numeric_articles``).
    """
    if _NODE_ID_TRANS_RE.match(node_id(node).lower()):
        return True

    for tag in ("section", "hcontainer", "chapter", "title", "part", "book"):
        for anc in node.xpath(f"ancestor::akn:{tag}", namespaces=NS):
            anc_id = (anc.get("eId") or anc.get("id") or "").lower()
            if "transitori" in anc_id:
                return True
            for child_tag in ("heading", "num"):
                child = anc.find(f"akn:{child_tag}", NS)
                if (
                    child is not None
                    and child.text
                    and re.search(r"transitori", child.text, re.IGNORECASE)
                ):
                    return True

    if has_numeric_articles and num_text:
        stripped = num_text.strip()
        has_articulo = re.match(r"^(?:Art[ií]culo|ARTÍCULO)\b", stripped)
        has_digit = re.search(r"\d", stripped)
        if not has_articulo and not has_digit and _ORDINAL_WORD_RE.match(stripped):
            return True

    return False


def derive_article_id(node, has_numeric_articles=True):
    """Return ``(article_id, is_transitorio)`` for an <article> node.

    Substantive articles keep their number ("8", "27-A"). Transitorios are
    namespaced (``T-8``, ``T-R2-1``) so they can never share an ES ``_id``
    with a substantive article.
    """
    num = node.find("akn:num", NS)
    num_text = num.text.strip() if num is not None and num.text else ""
    nid = node_id(node)
    raw = num_text or nid

    base = re.sub(r"^(?:Art[ií]culo|ARTÍCULO)\s*", "", raw).rstrip(".").strip()

    if not is_transitorio_node(node, num_text, has_numeric_articles):
        return base, False

    block = 1
    number = ""
    block_match = _NODE_ID_BLOCK_RE.search(nid)
    if block_match:
        block, number = int(block_match.group(1)), block_match.group(2)
    else:
        trailing = re.search(r"(\d+)$", nid)
        if trailing:
            number = trailing.group(1)
        else:
            mapped = ordinal_to_number(base) if base else None
            number = str(mapped) if mapped is not None else base
    if not number:
        number = nid or "x"
    return transitorio_id(number, block), True


def split_ordinal_heading(text):
    """``(number, remainder)`` if ``text`` opens with an ordinal heading.

    ``"Décimo Primero.- Los municipios…"`` → ``(11, "Los municipios…")``.
    Returns ``None`` when the text has no resolvable ordinal heading.
    """
    if not text:
        return None
    match = _TEXT_HEADING_RE.match(text)
    if not match:
        return None
    phrase = match.group(1).strip()
    if re.match(r"^[úu]nic[oa]$", phrase, re.IGNORECASE):
        number = 1
    elif re.match(r"^[úu]ltim[oa]$", phrase, re.IGNORECASE):
        number = 999
    else:
        number = ordinal_to_number(phrase)
    if number is None:
        return None
    return number, text[match.end() :].strip()


def _normalise(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _same_provision(first, second):
    a, b = _normalise(first), _normalise(second)
    if not a or not b:
        return False
    if a.startswith(b) or b.startswith(a):
        return True
    return a[:_SAME_PROVISION_PREFIX] == b[:_SAME_PROVISION_PREFIX]


def resolve_article_ids(articles, has_numeric_articles, warn=None):
    """Make article ids unique without ever letting one overwrite another.

    ``articles`` are dicts in document order carrying at least ``article_id``,
    ``is_transitorio`` and ``text``. Returns a new list. Rules, in order:

    1. The first node to claim a substantive id owns it. Substantive ids never
       change (``lfpdppp-8`` stays Artículo 8).
    2. Legacy XMLs (generated by the pre-#218 parser) serialise transitorios as
       ``<num>Artículo N</num>`` nodes whose TEXT opens with the ordinal
       heading ("Octavo.- …"). A non-transitorio node whose id is already
       owned by a substantive article — or that appears after a transitorio
       has been seen — and whose text opens with an ordinal heading is a
       transitorio: it is renumbered from the heading (``Décimo Primero`` →
       ``T-11``) and the heading is stripped. A numbering restart ("Primero"
       after "Vigésimo") opens a new decree block (``T-R2-1``).
    3. A duplicate-id node with no heading that directly follows a transitorio
       is a wrapped-line fragment of it ("…Octavo y" / "Décimo Tercero del
       presente Decreto…"); its text is appended to that transitorio.
    4. A transitorio whose id is already taken by a transitorio with the same
       text is the same provision parsed twice; the first copy is kept.
    5. Anything still colliding is suffixed ``-dupN`` and reported through
       ``warn`` — visible, never a silent overwrite.
    """
    warn = warn or (lambda message: None)
    resolved = []
    by_id = {}
    substantive_ids = set()
    dup_counts = {}
    seen_transitorio = False
    content_block = 0
    content_last = None

    for original in articles:
        art = dict(original)
        aid = art["article_id"]
        is_dup_substantive = not art["is_transitorio"] and aid in substantive_ids

        if (
            has_numeric_articles
            and not art["is_transitorio"]
            and (is_dup_substantive or seen_transitorio)
        ):
            heading = split_ordinal_heading(art["text"])
            if heading:
                number, remainder = heading
                if content_last is None or number <= content_last:
                    content_block += 1
                content_last = number
                new_id = transitorio_id(number, content_block)
                warn(f"article '{aid}' is transitorio text; indexing as '{new_id}'")
                art.update(
                    article_id=new_id,
                    is_transitorio=True,
                    text=remainder or art["text"],
                )
                aid = new_id
            elif is_dup_substantive and resolved and resolved[-1]["is_transitorio"]:
                previous = resolved[-1]
                warn(
                    f"article '{aid}' is a fragment of transitorio "
                    f"'{previous['article_id']}'; merging its text"
                )
                previous["text"] = f"{previous['text']}\n\n{art['text']}"
                continue

        if aid in by_id:
            prior = by_id[aid]
            if (
                art["is_transitorio"]
                and prior["is_transitorio"]
                and _same_provision(prior["text"], art["text"])
            ):
                continue
            dup_counts[aid] = dup_counts.get(aid, 0) + 1
            deduped = f"{aid}-dup{dup_counts[aid]}"
            warn(
                f"Duplicate article id '{aid}'; indexing later occurrence as "
                f"'{deduped}' to avoid overwrite"
            )
            art["article_id"] = aid = deduped

        if art["is_transitorio"]:
            seen_transitorio = True
        else:
            substantive_ids.add(aid)
        by_id[aid] = art
        resolved.append(art)

    return resolved
