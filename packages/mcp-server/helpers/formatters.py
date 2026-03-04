"""Format API responses into readable text for LLM consumption."""

from __future__ import annotations


def format_search_results(data: dict) -> str:
    """Format search response into readable text."""
    total = data.get("total", 0)
    page = data.get("page", 1)
    total_pages = data.get("total_pages", 1)
    results = data.get("results", [])

    if not results:
        return "No results found."

    lines = [f"Found {total} results (page {page}/{total_pages}):\n"]

    for i, r in enumerate(results, 1):
        law = r.get("law_name", "Unknown")
        article = r.get("article", "")
        snippet = r.get("snippet", "").strip()
        tier = r.get("tier", "")
        state = r.get("state")
        score = r.get("score", 0)

        loc = f"[{tier}]" if not state else f"[{tier} - {state}]"
        lines.append(f"{i}. {law} — {article} {loc} (score: {score:.1f})")
        if snippet:
            lines.append(f"   {snippet}")
        lines.append("")

    facets = data.get("facets")
    if facets:
        lines.append("Facets:")
        for facet_name, buckets in facets.items():
            if buckets:
                items = ", ".join(f"{b['key']}({b['count']})" for b in buckets[:5])
                lines.append(f"  {facet_name}: {items}")

    return "\n".join(lines)


def format_law_detail(data: dict) -> str:
    """Format law detail response."""
    lines = [
        f"# {data.get('name', 'Unknown')}",
        "",
        f"ID: {data.get('id', '')}",
        f"Category: {data.get('category', 'N/A')}",
        f"Tier: {data.get('tier', '')}",
        f"Type: {data.get('law_type', '')}",
        f"Status: {data.get('status', '')}",
        f"Articles: {data.get('articles', 0)}",
    ]

    state = data.get("state")
    if state:
        lines.append(f"State: {state}")

    source = data.get("source_url")
    if source:
        lines.append(f"Source: {source}")

    versions = data.get("versions", [])
    if versions:
        lines.append(f"\nVersions ({len(versions)}):")
        for v in versions[:5]:
            date = v.get("publication_date", "")
            summary = v.get("change_summary", "")
            lines.append(f"  - {date}: {summary}" if summary else f"  - {date}")
        if len(versions) > 5:
            lines.append(f"  ... and {len(versions) - 5} more")

    return "\n".join(lines)


def format_articles(data: dict) -> str:
    """Format law articles response."""
    law_name = data.get("law_name", "")
    total = data.get("total", 0)
    articles = data.get("articles", [])
    page = data.get("page", 1)
    page_size = data.get("page_size", 500)

    lines = [f"# {law_name}", f"Total articles: {total} (page {page})\n"]

    for a in articles:
        aid = a.get("article_id", "")
        text = a.get("text", "").strip()
        lines.append(f"## {aid}")
        lines.append(text)
        lines.append("")

    if total > page * page_size:
        lines.append(f"[{total - page * page_size} more articles on next pages]")

    return "\n".join(lines)


def format_structure(data: dict) -> str:
    """Format hierarchical law structure."""
    law_id = data.get("law_id", "")
    structure = data.get("structure", [])

    if not structure:
        return f"No structure available for {law_id}."

    lines = [f"Structure of {law_id}:\n"]
    _render_tree(structure, lines, indent=0)
    return "\n".join(lines)


def _render_tree(nodes: list, lines: list, indent: int) -> None:
    """Recursively render a tree structure."""
    prefix = "  " * indent
    for node in nodes:
        label = node.get("label", "")
        lines.append(f"{prefix}- {label}")
        children = node.get("children", [])
        if children:
            _render_tree(children, lines, indent + 1)


def format_law_list(data: dict) -> str:
    """Format paginated law list (DRF format)."""
    count = data.get("count", 0)
    results = data.get("results", [])

    if not results:
        return "No laws found."

    lines = [f"Found {count} laws:\n"]
    for r in results:
        name = r.get("name", "")
        law_id = r.get("id", "")
        tier = r.get("tier", "")
        status = r.get("status", "")
        category = r.get("category", "")
        lines.append(f"- {name} [{law_id}] ({tier}, {category}, {status})")

    has_next = data.get("next") is not None
    if has_next:
        lines.append(f"\n[More results available — {count} total]")

    return "\n".join(lines)


def format_related_laws(data: dict) -> str:
    """Format related laws response."""
    related = data.get("related", [])
    if not related:
        return f"No related laws found for {data.get('law_id', '')}."

    lines = [f"Laws related to {data.get('law_id', '')}:\n"]
    for r in related:
        name = r.get("name", "")
        law_id = r.get("law_id", "")
        tier = r.get("tier", "")
        category = r.get("category", "")
        lines.append(f"- {name} [{law_id}] ({tier}, {category})")

    return "\n".join(lines)


def format_cross_references(data: dict) -> str:
    """Format cross-reference data."""
    stats = data.get("statistics")
    if stats:
        return _format_ref_stats(stats)

    outgoing = data.get("outgoing", [])
    incoming = data.get("incoming", [])
    lines = []

    if outgoing:
        lines.append(f"Outgoing references ({data.get('total_outgoing', len(outgoing))}):")
        for ref in outgoing[:20]:
            target = ref.get("targetLawSlug", "")
            article = ref.get("targetArticle", "")
            text = ref.get("text", "")
            lines.append(f"  → {target} Art. {article}: {text}")

    if incoming:
        lines.append(f"\nIncoming references ({data.get('total_incoming', len(incoming))}):")
        for ref in incoming[:20]:
            source = ref.get("sourceLawSlug", "")
            article = ref.get("sourceArticle", "")
            lines.append(f"  ← {source} Art. {article}")

    return "\n".join(lines) if lines else "No cross-references found."


def _format_ref_stats(stats: dict) -> str:
    """Format law-level reference statistics."""
    lines = [
        f"Outgoing references: {stats.get('total_outgoing', 0)}",
        f"Incoming references: {stats.get('total_incoming', 0)}",
    ]

    most_ref = stats.get("most_referenced_laws", [])
    if most_ref:
        lines.append("\nMost referenced laws:")
        for r in most_ref[:10]:
            lines.append(f"  - {r['slug']} ({r['count']} refs)")

    most_citing = stats.get("most_citing_laws", [])
    if most_citing:
        lines.append("\nMost citing laws:")
        for r in most_citing[:10]:
            lines.append(f"  - {r['slug']} ({r['count']} refs)")

    return "\n".join(lines)


def format_judicial_results(data: dict) -> str:
    """Format judicial search/list results."""
    total = data.get("total", 0)
    results = data.get("results", [])

    if not results:
        return "No judicial records found."

    lines = [f"Found {total} judicial records:\n"]
    for r in results:
        registro = r.get("registro", "")
        tipo = r.get("tipo", "")
        materia = r.get("materia", "")
        rubro = r.get("rubro", "")
        instancia = r.get("instancia", "")
        fecha = r.get("fecha_publicacion", "")
        # Truncate rubro
        if len(rubro) > 120:
            rubro = rubro[:117] + "..."
        lines.append(f"- [{registro}] {tipo} | {materia} | {instancia}")
        lines.append(f"  {rubro}")
        lines.append(f"  Date: {fecha}")
        lines.append("")

    return "\n".join(lines)


def format_judicial_detail(data: dict) -> str:
    """Format a single judicial record."""
    lines = [
        f"# {data.get('rubro', 'Unknown')}",
        "",
        f"Registro: {data.get('registro', '')}",
        f"Tipo: {data.get('tipo', '')}",
        f"Materia: {data.get('materia', '')}",
        f"Época: {data.get('epoca', '')}",
        f"Instancia: {data.get('instancia', '')}",
        f"Ponente: {data.get('ponente', '')}",
        f"Fecha: {data.get('fecha_publicacion', '')}",
    ]

    fuente = data.get("fuente")
    if fuente:
        lines.append(f"Fuente: {fuente}")

    texto = data.get("texto", "")
    if texto:
        lines.append(f"\n## Texto\n{texto}")

    precedentes = data.get("precedentes", "")
    if precedentes:
        lines.append(f"\n## Precedentes\n{precedentes}")

    return "\n".join(lines)


def format_judicial_stats(data: dict) -> str:
    """Format judicial corpus statistics."""
    total = data.get("total", 0)
    lines = [f"Judicial corpus: {total} records\n"]

    by_tipo = data.get("by_tipo", {})
    if by_tipo:
        lines.append("By type:")
        for k, v in by_tipo.items():
            lines.append(f"  - {k}: {v}")

    by_materia = data.get("by_materia", {})
    if by_materia:
        lines.append("\nBy subject matter:")
        for k, v in by_materia.items():
            lines.append(f"  - {k}: {v}")

    by_epoca = data.get("by_epoca", {})
    if by_epoca:
        lines.append("\nBy epoch:")
        for k, v in by_epoca.items():
            lines.append(f"  - {k}: {v}")

    return "\n".join(lines)


def format_categories(data: list) -> str:
    """Format categories list."""
    if not data:
        return "No categories available."

    lines = ["Legal categories:\n"]
    for cat in data:
        slug = cat.get("category", "")
        label = cat.get("label", slug)
        count = cat.get("count", 0)
        lines.append(f"- {label} [{slug}]: {count} laws")

    return "\n".join(lines)


def format_states(data: dict) -> str:
    """Format states list."""
    states = data.get("states", [])
    if not states:
        return "No states available."

    return "Mexican states with indexed laws:\n" + "\n".join(f"- {s}" for s in states)


def format_stats(data: dict) -> str:
    """Format platform dashboard stats."""
    lines = [
        "# Tezca Platform Statistics\n",
        f"Total laws: {data.get('total_laws', 0):,}",
        f"  Federal: {data.get('federal_count', 0):,}",
        f"  State: {data.get('state_count', 0):,}",
        f"  Municipal: {data.get('municipal_count', 0):,}",
        f"Total articles: {data.get('total_articles', 0):,}",
        f"Last update: {data.get('last_update', 'N/A')}",
        "",
        "Coverage:",
        f"  Federal: {data.get('federal_coverage', 0):.1f}%",
        f"  State: {data.get('state_coverage', 0):.1f}%",
        f"  Overall: {data.get('total_coverage', 0):.1f}%",
    ]

    recent = data.get("recent_laws", [])
    if recent:
        lines.append("\nRecent additions:")
        for r in recent[:5]:
            lines.append(f"  - {r.get('name', '')} ({r.get('tier', '')}, {r.get('date', '')})")

    return "\n".join(lines)


def format_coverage(data: dict) -> str:
    """Format detailed coverage statistics."""
    lines = [
        "# Tezca Coverage Report\n",
        f"Total laws: {data.get('total_laws', 0):,}",
        f"Overall coverage: {data.get('overall_pct', 0):.1f}%",
        "",
    ]

    tiers = data.get("tiers", [])
    for t in tiers:
        name = t.get("name", {})
        label = name.get("en", name.get("es", t.get("id", "")))
        have = t.get("have", 0)
        universe = t.get("universe")
        pct = t.get("pct")
        pct_str = f"{pct:.1f}%" if pct is not None else "N/A"
        universe_str = f"/{universe:,}" if universe else ""
        lines.append(f"- {label}: {have:,}{universe_str} ({pct_str})")

    return "\n".join(lines)


def format_suggestions(data: dict) -> str:
    """Format suggest/autocomplete results."""
    suggestions = data.get("suggestions", [])
    if not suggestions:
        return "No suggestions found."

    lines = ["Suggestions:\n"]
    for s in suggestions:
        name = s.get("name", "")
        law_id = s.get("id", "")
        tier = s.get("tier", "")
        lines.append(f"- {name} [{law_id}] ({tier})")

    return "\n".join(lines)


def format_search_within_law(data: dict) -> str:
    """Format within-law search results."""
    law_id = data.get("law_id", "")
    query = data.get("query", "")
    total = data.get("total", 0)
    results = data.get("results", [])

    if not results:
        return f'No results for "{query}" in {law_id}.'

    lines = [f'Found {total} matches for "{query}" in {law_id}:\n']
    for r in results:
        aid = r.get("article_id", "")
        snippet = r.get("snippet", "").strip()
        score = r.get("score", 0)
        lines.append(f"- {aid} (score: {score:.1f})")
        if snippet:
            lines.append(f"  {snippet}")
        lines.append("")

    return "\n".join(lines)
