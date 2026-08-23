"""
Corpus watch — flags a *known yearly instrument* when it reappears in the DOF.

Some documents in Tezca's corpus are re-issued on a fixed yearly cadence by
the same authority: the SEP calendario escolar (an acuerdo, ~May–July each
year), the JCF Reglas de Operación (~December), the RMF, and so on. These are
exactly the documents whose corpus entry is *pinned by codigo* — so when next
year's edition is published, a human has to add the new pinned entry. The
generic DOF-daily change detector
(:func:`apps.scraper.federal.dof_daily.DofScraper.detect_law_changes`) will
not catch them: it filters to ``DECRETO``/``LEY``/``REGLAMENTO``-type titles,
and an SEP *acuerdo* establishing a *calendario* matches none of those
keywords. It would slip through silently — and the year-over-year loop kalya
depends on (docs/data/SEP_CALENDARIO_ESCOLAR.md) would never get its trigger.

This module is that trigger. It is a small declarative registry of watch
patterns; :func:`scan_entries` runs them against a day's DOF entries and
returns a hit for each match, naming the corpus the new publication belongs
to and what an operator must do (add the pinned codigo + re-run the fetcher).
It is deliberately *detect-and-notify only*: it never mutates the corpus,
because pinning a codigo requires the identity-verification step the fetchers
enforce (an opaque codigo can resolve to the wrong instrument), which is a
human decision, not an automated one.

``check_dof_daily`` calls :func:`scan_entries` on every run; the
``check_corpus_watches`` management command runs it on demand for any date
(e.g. to back-check the window when a yearly acuerdo was expected).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CorpusWatch:
    """A declarative watch for one yearly-reissued instrument.

    A DOF entry matches when its title matches *every* pattern in
    ``title_patterns`` (all case-insensitive), and — when
    ``issuer_contains`` is set — its issuing-authority category contains that
    fragment. All patterns must match so a watch is specific: the SEP
    calendario watch requires both "calendario" and "ciclo lectivo" so it
    fires on the yearly calendario acuerdo but not on every SEP acuerdo.
    """

    key: str
    corpus: str  # which corpus the hit belongs to (matches the data/ dir + registry)
    description: str
    title_patterns: List[str]  # ALL must match (case-insensitive)
    issuer_contains: Optional[str] = None  # matched against the entry "category"
    # Human-facing instruction recorded on a hit — what to do when it fires.
    action: str = ""
    # Months (1–12) the instrument is normally published in — advisory only,
    # used by the on-demand checker to suggest a back-check window; never a
    # filter (a late/early publication must still be caught).
    expected_months: List[int] = field(default_factory=list)

    def matches(self, title: str, category: str = "") -> bool:
        title_l = title.lower()
        for pattern in self.title_patterns:
            if not re.search(pattern.lower(), title_l):
                return False
        if self.issuer_contains:
            if self.issuer_contains.lower() not in (category or "").lower():
                return False
        return True


# ---------------------------------------------------------------------------
# The watch registry.
#
# One entry per yearly-reissued pinned instrument. Add a watch here when a
# corpus is added whose documents are re-published on a fixed cadence and
# pinned by codigo.
# ---------------------------------------------------------------------------

# The SEP calendario escolar for educación básica: an ACUERDO the SEP
# publishes each ciclo (2026-2027 = Acuerdo 07/07/26, DOF 2026-07-15, codigo
# 5793645; see apps.scraper.federal.sep_calendario_scraper). When the
# 2027-2028 edition lands this fires, and an operator adds its pinned entry.
SEP_CALENDARIO_WATCH = CorpusWatch(
    key="sep_calendario_escolar",
    corpus="sep_calendario",
    description=(
        "SEP calendario escolar (educación básica) — yearly acuerdo, "
        "typically published May–July"
    ),
    title_patterns=[r"calendario", r"ciclo lectivo"],
    issuer_contains="EDUCACION PUBLICA",
    action=(
        "New SEP calendario-escolar acuerdo detected. Add a pinned "
        "SepCalendarDocument for the new ciclo in "
        "apps/scraper/federal/sep_calendario_scraper.py (verify the DOF "
        "codigo against primary text — the identity guard rejects a "
        "mis-pinned one), extract the day-level dates from the annex grid "
        "into data/sep_calendario/dates-<ciclo>.json, run `manage.py "
        "ingest_sep_calendario --catalog ...`, and notify kalya so its "
        "organizational-calendar generator can draft the new ciclo."
    ),
    expected_months=[5, 6, 7],
)

# The JCF Reglas de Operación: re-issued by the STPS each ejercicio fiscal
# (~December). The existing JCF corpus is pinned the same way, and its own
# note already flags a re-verification window; a watch makes the yearly
# reissue loud instead of silent, on the same machinery as the SEP one.
JCF_REGLAS_WATCH = CorpusWatch(
    key="jcf_reglas_operacion",
    corpus="jcf",
    description=(
        "JCF Reglas de Operación — yearly STPS instrument, typically "
        "published in December for the next ejercicio fiscal"
    ),
    title_patterns=[r"reglas de operaci[oó]n", r"j[oó]venes construyendo el futuro"],
    issuer_contains="TRABAJO",
    action=(
        "New JCF Reglas de Operación detected. Add a pinned JcfDocument for "
        "the new ejercicio fiscal in apps/scraper/federal/jcf_scraper.py "
        "(verify the DOF codigo), run `manage.py ingest_jcf`, and mark the "
        "prior year's ROP abrogada."
    ),
    expected_months=[12],
)

CORPUS_WATCHES: List[CorpusWatch] = [
    SEP_CALENDARIO_WATCH,
    JCF_REGLAS_WATCH,
]

CORPUS_WATCHES_BY_KEY: Dict[str, CorpusWatch] = {w.key: w for w in CORPUS_WATCHES}


@dataclass
class WatchHit:
    """A DOF entry that matched a corpus watch."""

    watch_key: str
    corpus: str
    title: str
    url: str
    action: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "watch_key": self.watch_key,
            "corpus": self.corpus,
            "title": self.title,
            "url": self.url,
            "action": self.action,
        }


def scan_entries(entries: List[Dict[str, str]]) -> List[WatchHit]:
    """Return a :class:`WatchHit` for every (entry, watch) match.

    ``entries`` is the output of
    :meth:`apps.scraper.federal.dof_daily.DofScraper.fetch_daily_edition`
    (dicts with ``title``, ``category``, ``url``). Detection only — nothing
    is written. An entry can match more than one watch; each match is its own
    hit.
    """
    hits: List[WatchHit] = []
    for entry in entries:
        title = entry.get("title", "") or ""
        category = entry.get("category", "") or ""
        for watch in CORPUS_WATCHES:
            if watch.matches(title, category):
                hits.append(
                    WatchHit(
                        watch_key=watch.key,
                        corpus=watch.corpus,
                        title=title,
                        url=entry.get("url", "") or "",
                        action=watch.action,
                    )
                )
    return hits
