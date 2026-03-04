"""MCP prompt templates for common legal research workflows."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt()
    def research_mexican_law(topic: str, jurisdiction: str = "all") -> str:
        """Step-by-step workflow for researching a Mexican law topic.

        Args:
            topic: The legal topic to research (e.g. "propiedad intelectual").
            jurisdiction: "federal", "state", "municipal", or "all".
        """
        return f"""\
Research Mexican law on: {topic}
Jurisdiction: {jurisdiction}

Follow these steps:

1. **Understand the landscape**: Call get_categories() and read tezca://taxonomy
   to understand which legal categories relate to "{topic}".

2. **Search broadly**: Use search_laws(query="{topic}", jurisdiction="{jurisdiction}")
   to find relevant articles across all indexed laws.

3. **Identify key laws**: From search results, note the most frequently appearing
   law_ids. Use suggest_laws() if you need to find specific law names.

4. **Deep dive**: For each key law:
   a. get_law_detail(law_id) — check status, category, version history
   b. get_law_structure(law_id) — understand the law's organization
   c. get_law_articles(law_id, page_size=50) — read relevant articles

5. **Map the citation network**: Use get_cross_references(law_id) to find
   which other laws cite this one and which it cites.

6. **Check judicial interpretation**: Use search_judicial(query="{topic}")
   to find how courts have interpreted the relevant provisions.

7. **Synthesize**: Combine statutory text, cross-references, and judicial
   interpretations into a comprehensive legal analysis.

Important: All law text is in Spanish. Search in Spanish for best results.
"""

    @mcp.prompt()
    def compare_state_laws(topic: str, states: str) -> str:
        """Guide for comparing how different Mexican states regulate a topic.

        Args:
            topic: Legal topic to compare (e.g. "transparencia", "medio ambiente").
            states: Comma-separated state names (e.g. "Jalisco,Ciudad de México").
        """
        state_list = [s.strip() for s in states.split(",")]
        state_bullets = "\n".join(f"   - {s}" for s in state_list)

        return f"""\
Compare state laws on: {topic}
States: {', '.join(state_list)}

Follow these steps:

1. **Get state list**: Call get_states() to verify state names are correct.

2. **Search per state**: For each state, run:
   search_laws(query="{topic}", jurisdiction="state", state="<state_name>")

   States to compare:
{state_bullets}

3. **Identify comparable laws**: Find the equivalent law in each state.
   Use suggest_laws() with state-specific terms if needed.

4. **Compare structure**: For each law, call get_law_structure() to see
   how each state organizes the topic.

5. **Compare key provisions**: Use search_within_law() to find specific
   provisions on subtopics of interest within each state's law.

6. **Check for federal baseline**: Search federal law on "{topic}" to
   understand the national framework that states build upon.

7. **Synthesize differences**: Create a comparison table noting:
   - Scope and definitions
   - Key obligations and rights
   - Enforcement mechanisms
   - Unique provisions per state
"""

    @mcp.prompt()
    def trace_legal_authority(law_id: str) -> str:
        """Trace the citation chain and judicial interpretations for a specific law.

        Args:
            law_id: The law identifier (e.g. "amparo", "codigo_civil_federal").
        """
        return f"""\
Trace legal authority for: {law_id}

Follow these steps:

1. **Get law metadata**: Call get_law_detail("{law_id}") to understand
   the law's category, tier, status, and version history.

2. **Map outgoing references**: Call get_cross_references("{law_id}")
   to see which laws this one cites. The constitutional and organic law
   references establish its legal foundation.

3. **Map incoming references**: From the same cross-references response,
   identify which laws cite {law_id}. These are the laws that depend on
   or implement its provisions.

4. **Find related laws**: Call get_related_laws("{law_id}") for
   thematically similar legislation that may form part of the same
   regulatory framework.

5. **Search judicial interpretations**: Use search_judicial(query="<law_name>")
   to find how the SCJN has interpreted this law. Pay attention to:
   - Jurisprudencia (binding precedent)
   - Tesis aisladas (non-binding but influential interpretations)

6. **Check specific articles**: For key articles identified in judicial
   records, use get_cross_references("{law_id}", article_id="<num>")
   to see article-level citation patterns.

7. **Build authority map**: Synthesize into a hierarchy:
   - Constitutional basis (Art. 1, 14, 16, etc.)
   - Organic/enabling laws
   - {law_id} itself
   - Implementing regulations (reglamentos)
   - Judicial interpretations
"""
