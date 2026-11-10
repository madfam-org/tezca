"""Render a segmented RMF as Akoma Ntoso that ``index_laws`` consumes as-is.

Shape (only what the indexer reads is load-bearing):

* every rule is an ``<article>`` whose ``<num>`` is the rule number
  (``3.13.7.``), so ``apps.api.transitorios.derive_article_id`` yields the
  article id ``3.13.7``; the epígrafe goes in ``<heading>`` (not indexed as
  text), the closing legal references are the last paragraph;
* rules nest in ``<title>``/``<chapter>``/``<section>``/``<subsection>`` with ``<num>`` and
  ``<heading>``, which become the ES ``title``/``chapter`` breadcrumbs;
* compiler notes ("- Reformada en la Primera RMRMF …") are ``<note>``
  children, which the indexer skips;
* transitorios live in ``<hcontainer name="transitorios">`` with node ids
  ``trans-N`` (base resolution) and ``trans-rK-N`` (K-th block, i.e. the
  resolución de modificaciones K - 1), which the indexer maps to ``T-N`` and
  ``T-RK-N``;
* the Glosario is an article numbered ``Glosario``.
"""

from __future__ import annotations

from typing import Dict, Optional

from lxml import etree

from apps.parsers.rmf.segmenter import Division, RmfDocument, Rule, Transitorio

AKN_NS = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
_TAG_BY_KIND = {
    "titulo": "title",
    "capitulo": "chapter",
    "seccion": "section",
    "subseccion": "subsection",
}
_PREFIX_BY_KIND = {
    "titulo": "tit",
    "capitulo": "cap",
    "seccion": "sec",
    "subseccion": "subsec",
}


def rule_eid(number: str) -> str:
    return "regla-" + number.replace(".", "-")


def transitorio_eid(item: Transitorio) -> str:
    if item.block > 1:
        return f"trans-r{item.block}-{item.number}"
    return f"trans-{item.number}"


def _el(parent, tag: str, text: Optional[str] = None, **attrs):
    node = etree.SubElement(parent, f"{{{AKN_NS}}}{tag}", **attrs)
    if text is not None:
        node.text = text
    return node


def _paragraphs(parent, eid: str, paragraphs, class_: Optional[str] = None) -> None:
    for index, text in enumerate(paragraphs, start=1):
        attrs = {"eId": f"{eid}-para-{index}"}
        if class_:
            attrs["class"] = class_
        para = _el(parent, "paragraph", **attrs)
        content = _el(para, "content")
        _el(content, "p", text)


def _notes(parent, eid: str, notes) -> None:
    for index, text in enumerate(notes, start=1):
        note = _el(parent, "note", eId=f"{eid}-note-{index}", placement="top")
        _el(note, "p", text)


def _rule(parent, rule: Rule) -> None:
    eid = rule_eid(rule.number)
    article = _el(parent, "article", eId=eid, id=eid)
    _el(article, "num", f"{rule.number}.")
    if rule.title:
        _el(article, "heading", rule.title)
    _notes(article, eid, rule.notes)
    _paragraphs(article, eid, rule.paragraphs)
    if rule.references:
        para = _el(article, "paragraph", eId=f"{eid}-refs", **{"class": "referencias"})
        content = _el(para, "content")
        _el(content, "p", rule.references)


def _division(parent, division: Division, parent_eid: str = "") -> None:
    local = f"{_PREFIX_BY_KIND[division.kind]}_{division.number.replace('.', '-')}"
    eid = f"{parent_eid}__{local}" if parent_eid else local
    node = _el(parent, _TAG_BY_KIND[division.kind], eId=eid, id=eid)
    _el(node, "num", division.label)
    if division.heading:
        _el(node, "heading", division.heading)
    for child in division.children:
        if isinstance(child, Rule):
            _rule(node, child)
        else:
            _division(node, child, eid)


def _transitorio(parent, item: Transitorio) -> None:
    eid = transitorio_eid(item)
    article = _el(parent, "article", eId=eid, id=eid)
    _el(article, "num", item.ordinal)
    _notes(article, eid, item.notes)
    _paragraphs(article, eid, item.paragraphs)


def build_akn(doc: RmfDocument, metadata: Dict[str, str]) -> str:
    """Serialise ``doc``. ``metadata`` keys:

    ``official_id`` (``rmf_2026``), ``work_date`` (DOF date of the base
    resolution), ``expression_date`` (date of this text: DOF date of the base
    or of the last modification it compiles), ``author`` (``#sat``).
    """
    official_id = metadata["official_id"]
    work = f"/mx/fed/resolucion-miscelanea-fiscal/{metadata['work_date']}/{official_id}"
    expression = f"{work}/spa@{metadata['expression_date']}"

    root = etree.Element(f"{{{AKN_NS}}}akomaNtoso", nsmap={None: AKN_NS})
    act = _el(root, "act", name="resolucionMiscelaneaFiscal")
    meta = _el(act, "meta")
    ident = _el(meta, "identification", source="#tezca-rmf-parser")
    frbr_work = _el(ident, "FRBRWork")
    _el(frbr_work, "FRBRthis", value=f"{work}/main")
    _el(frbr_work, "FRBRuri", value=work)
    _el(frbr_work, "FRBRdate", date=metadata["work_date"], name="publication")
    _el(frbr_work, "FRBRauthor", href=metadata.get("author", "#sat"))
    _el(frbr_work, "FRBRcountry", value="mx")
    frbr_expr = _el(ident, "FRBRExpression")
    _el(frbr_expr, "FRBRthis", value=f"{expression}/main")
    _el(frbr_expr, "FRBRuri", value=expression)
    _el(frbr_expr, "FRBRdate", date=metadata["expression_date"], name="publication")
    _el(frbr_expr, "FRBRauthor", href="#tezca-rmf-parser")
    _el(frbr_expr, "FRBRlanguage", language="spa")
    frbr_man = _el(ident, "FRBRManifestation")
    _el(frbr_man, "FRBRthis", value=f"{expression}/main.xml")
    _el(frbr_man, "FRBRuri", value=f"{expression}/main.akn")
    _el(frbr_man, "FRBRdate", date=metadata["expression_date"], name="publication")
    _el(frbr_man, "FRBRauthor", href="#tezca-rmf-parser")

    body = _el(act, "body")
    if doc.glossary:
        glossary = _el(body, "article", eId="glosario", id="glosario")
        _el(glossary, "num", "Glosario")
        _paragraphs(glossary, "glosario", doc.glossary)
    for division in doc.divisions:
        _division(body, division)

    if doc.transitorios or doc.modifications:
        container = _el(body, "hcontainer", name="transitorios", eId="transitorios")
        _el(container, "heading", "Transitorios")
        for item in doc.transitorios:
            if item.block == 1:
                _transitorio(container, item)
        for block in doc.modifications:
            eid = f"transitorios-r{block.block}"
            sub = _el(
                container, "hcontainer", name="resolucionDeModificaciones", eId=eid
            )
            _el(sub, "heading", block.label)
            if block.resolutivos:
                intro = _el(sub, "intro")
                for text in block.resolutivos:
                    _el(intro, "p", text)
            for item in doc.transitorios:
                if item.block == block.block:
                    _transitorio(sub, item)

    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", pretty_print=True
    ).decode("utf-8")
