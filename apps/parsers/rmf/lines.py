"""Typographic lines of an RMF PDF: text + font style + horizontal alignment.

The RMF is typeset with a fixed visual grammar, in the DOF edition as well as
in SAT's compiled ("compilada") edition:

* the epígrafe (rule title) is **bold**, left-aligned at the body indent;
* the rule number (``3.13.1.``) hangs to the left of the body indent, on the
  same line as the first words of the rule;
* the legal references that close a rule (``LISR 113-E, 113-G, CFF 27``) are
  *italic*;
* Títulos, Capítulos and Secciones are bold and centred;
* the compiled edition adds compiler notes before an amended rule: a
  ***bold-italic*** marker (``Regla 2.1.6.``) followed by italic
  ``- Reformada en la Primera RMRMF …`` lines.

Plain-text extraction (``pdftotext``) loses exactly that information, so a
title cannot be told apart from the last line of the previous rule, and a
wrapped cross-reference such as "conforme a la regla\\n2.3.8. y la ficha …"
looks like a new rule. This module keeps style and alignment per line; the
segmenter in :mod:`apps.parsers.rmf.segmenter` works only on these
``SourceLine`` records, so it is pure and can be tested on a fixture without
the PDF.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

STYLE_REGULAR = "regular"
STYLE_BOLD = "bold"
STYLE_ITALIC = "italic"
STYLE_BOLD_ITALIC = "bold_italic"

ALIGN_HANGING = "hanging"  # left of the body indent: rule numbers, ordinals
ALIGN_BODY = "body"  # at the body indent: paragraphs, epígrafes
ALIGN_INSET = "inset"  # right of the body indent: fracciones, centred headings

# Distance (PDF points) from the body indent that still counts as "at" it.
# Measured: body 128 / numbers 70 (compiled), body 156 / numbers 99 (DOF);
# fracciones sit at +42 or more.
_ALIGN_TOLERANCE = 15.0


@dataclass(frozen=True)
class SourceLine:
    text: str
    style: str = STYLE_REGULAR
    align: str = ALIGN_BODY
    page: int = 0


def style_from_fonts(fontnames: Iterable[str]) -> str:
    """Majority style of a line from its characters' PDF font names."""
    counts: Counter = Counter()
    for name in fontnames:
        lowered = (name or "").lower()
        bold = "bold" in lowered or "black" in lowered
        italic = "italic" in lowered or "oblique" in lowered
        if bold and italic:
            counts[STYLE_BOLD_ITALIC] += 1
        elif bold:
            counts[STYLE_BOLD] += 1
        elif italic:
            counts[STYLE_ITALIC] += 1
        else:
            counts[STYLE_REGULAR] += 1
    if not counts:
        return STYLE_REGULAR
    return counts.most_common(1)[0][0]


def classify_align(x0: float, body_x: float) -> str:
    if x0 < body_x - _ALIGN_TOLERANCE:
        return ALIGN_HANGING
    if x0 > body_x + _ALIGN_TOLERANCE:
        return ALIGN_INSET
    return ALIGN_BODY


# --------------------------------------------------------------------------
# Page furniture
# --------------------------------------------------------------------------

_PAGE_NUMBER_RE = re.compile(r"^Página \d+ de \d+$")
# SAT compiled edition: a three-line disclaimer at the foot of every page.
_COMPILED_FOOTER_RE = re.compile(r"^NOTA: Este documento constituye una compilación")
# DOF running head: "Domingo 28 de diciembre de 2025 DIARIO OFICIAL" (either
# order), sometimes with "(Edición Vespertina)".
_DOF_HEAD_RE = re.compile(
    r"^(?:\(Edición Vespertina\)\s*)?"
    r"(?:(?:Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\s+DIARIO OFICIAL"
    r"|DIARIO OFICIAL\s+(?:Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4})"
    r"(?:\s*\(Edición Vespertina\))?$"
)


def drop_page_furniture(lines: Sequence[SourceLine]) -> List[SourceLine]:
    """Remove running heads, page numbers and the compiled-edition footer.

    ``lines`` must be one page, top to bottom. The compiled footer always
    closes the page, so everything from its first line down is dropped.
    """
    kept: List[SourceLine] = []
    for line in lines:
        text = line.text.strip()
        if _COMPILED_FOOTER_RE.match(text):
            break
        if _PAGE_NUMBER_RE.match(text) or _DOF_HEAD_RE.match(text):
            continue
        kept.append(line)
    return kept


# --------------------------------------------------------------------------
# PDF extraction (pdfplumber)
# --------------------------------------------------------------------------


def extract_lines(pdf_path: Path | str) -> List[SourceLine]:
    """Read every page of an RMF PDF into ``SourceLine`` records.

    The body indent is measured once per document (the most common left edge
    of regular-weight lines): the RMF keeps one indent throughout, while a
    per-page measure is skewed on pages made mostly of fracciones.
    """
    import pdfplumber  # heavy import, only needed when reading a PDF

    raw: List[tuple] = []  # (page_no, text, style, x0)
    left_edges: Counter = Counter()
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            for line in page.extract_text_lines(return_chars=True):
                text = re.sub(r"\s+", " ", line["text"]).strip()
                if not text:
                    continue
                style = style_from_fonts(
                    c.get("fontname", "") for c in line["chars"] if c["text"].strip()
                )
                x0 = float(line["x0"])
                raw.append((page_no, text, style, x0))
                if style == STYLE_REGULAR:
                    left_edges[round(x0)] += 1
            page.flush_cache()

    if not raw:
        return []
    body_x = float(left_edges.most_common(1)[0][0]) if left_edges else raw[0][3]

    lines: List[SourceLine] = []
    page_lines: List[SourceLine] = []
    current_page = raw[0][0]
    for page_no, text, style, x0 in raw:
        if page_no != current_page:
            lines.extend(drop_page_furniture(page_lines))
            page_lines = []
            current_page = page_no
        page_lines.append(
            SourceLine(
                text=text, style=style, align=classify_align(x0, body_x), page=page_no
            )
        )
    lines.extend(drop_page_furniture(page_lines))
    return lines


# --------------------------------------------------------------------------
# JSON Lines round-trip (fixtures and extraction caches)
# --------------------------------------------------------------------------


def dump_jsonl(lines: Iterable[SourceLine], path: Path | str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(asdict(line), ensure_ascii=False) + "\n")


def load_jsonl(path: Path | str) -> List[SourceLine]:
    out: List[SourceLine] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if raw:
                out.append(SourceLine(**json.loads(raw)))
    return out
