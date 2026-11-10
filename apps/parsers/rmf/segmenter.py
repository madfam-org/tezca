"""Segment an RMF into Títulos/Capítulos/Secciones, rules and transitorios.

Input is the sequence of :class:`~apps.parsers.rmf.lines.SourceLine` read
from the DOF or SAT-compiled PDF. Output is an :class:`RmfDocument` whose
unit is the **rule** (``3.13.7``), not the article: every rule carries its
number, its epígrafe, its paragraphs and the italic legal references that
close it.

What makes a line a rule start, and not a cross-reference that happens to
wrap to the start of a line ("conforme a la regla\\n2.3.8. y la ficha …"):

1. it is regular weight and opens with a dotted number ``N.N[.N[.N]].``;
2. the number's parent is an open division (rule ``3.13.7`` needs Capítulo
   ``3.13`` open; ``2.6.1.4`` needs Sección ``2.6.1``; ``2.7.7.1.1`` needs
   Subsección ``2.7.7.1``);
3. it follows an epígrafe (bold, at the body indent) or hangs left of the
   body indent, as every rule number in both editions does.

Transitorios are numbered with ordinals. The compiled edition prints the
tens word of compound ordinals ("Décimo", "Vigésimo") in bold on its own
line, so "Décimo" + "Primero. Para los efectos …" is one ordinal. Transitorios
of the base resolution are block 1; transitorios of the N-th resolución de
modificaciones that the compiled edition appends are block N + 1, the block
scheme ``apps.api.transitorios`` already uses (``T-R2-1``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Sequence, Union

from apps.parsers.patterns.articles import ordinal_to_number
from apps.parsers.rmf.lines import (
    ALIGN_BODY,
    ALIGN_HANGING,
    STYLE_BOLD,
    STYLE_BOLD_ITALIC,
    STYLE_ITALIC,
    STYLE_REGULAR,
    SourceLine,
)

RULE_NUMBER_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,3}){1,4})\.(?=\s|$)\s*(.*)$")
HEADING_RE = re.compile(
    r"^(Título|Capítulo|Sección|Subsección)\s+(\d{1,2}(?:\.\d{1,3}){0,3})\.\s*(.*)$"
)
TRANSITORIOS_HEADING_RE = re.compile(r"^Transitorios?$")

_ORD_UNIT = (
    r"Primer[oa]|Segund[oa]|Tercer[oa]|Cuart[oa]|Quint[oa]|Sext[oa]|"
    r"Séptim[oa]|Octav[oa]|Noven[oa]"
)
_ORD_TENS = r"Décim[oa]|Vigésim[oa]|Trigésim[oa]|Cuadragésim[oa]"
TRANSITORIO_RE = re.compile(
    rf"^((?:(?:{_ORD_TENS})\s+)?(?:{_ORD_UNIT})|(?:{_ORD_TENS})|Únic[oa])\.\s*(.*)$"
)
ORDINAL_TENS_LINE_RE = re.compile(rf"^(?:{_ORD_TENS})$")
MODIFICATION_RE = re.compile(
    r"^(Primera|Segunda|Tercera|Cuarta|Quinta|Sexta|Séptima|Octava|Novena|Décima)"
    r"\s+Modificación de la Resolución Miscelánea Fiscal para \d{4}"
)
RESOLUTIVO_RE = re.compile(
    r"^(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|SÉPTIMO|OCTAVO|NOVENO|"
    r"DÉCIMO|ÚNICO)\.\s*(.*)$"
)
NOTE_MARKER_RE = re.compile(
    r"^(?:Regla|Transitorio|Glosario|Título|Capítulo|Sección)\b"
)
GLOSSARY_START_RE = re.compile(
    r"^Para una mejor comprensión de lo establecido en la presente Resolución"
)
SIGNATURE_RE = re.compile(r"^Atentamente\.?$")
DEROGADA_RE = re.compile(r"^\(?\s*Se deroga\s*\.?\s*\)?\.?$", re.IGNORECASE)

# A line that opens a new paragraph even without a sentence end before it:
# fracciones (I.), incisos (a)), numerales (1.) and bullets.
_LIST_ITEM_RE = re.compile(
    r"^(?:[IVXLC]+\.\s|[a-zñ]\)\s|[A-Z]\)\s|\d{1,2}\.(?!\d)\s|•|-\s)"
)

# A heading line that ends mid-phrase continues on the next line.
_UNFINISHED_RE = re.compile(
    r"(?:\b(?:de|del|la|las|los|el|y|e|en|a|o|u|por|para|que|con|al|sus?)|[,;])$"
)

_FEMININE_TO_MASCULINE = {"Primera": "Primero", "Única": "Único"}


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------


@dataclass
class Rule:
    number: str
    title: str = ""
    paragraphs: List[str] = field(default_factory=list)
    references: str = ""
    notes: List[str] = field(default_factory=list)
    titulo: str = ""
    capitulo: str = ""
    seccion: str = ""
    subseccion: str = ""

    @property
    def derogada(self) -> bool:
        return len(self.paragraphs) == 1 and bool(DEROGADA_RE.match(self.paragraphs[0]))

    @property
    def text(self) -> str:
        """The rule as published: paragraphs, then its closing references."""
        parts = list(self.paragraphs)
        if self.references:
            parts.append(self.references)
        return "\n\n".join(parts)


@dataclass
class Division:
    kind: str  # "titulo" | "capitulo" | "seccion" | "subseccion"
    number: str
    heading: str = ""
    children: List[Union["Division", Rule]] = field(default_factory=list)

    @property
    def label(self) -> str:
        word = {
            "titulo": "Título",
            "capitulo": "Capítulo",
            "seccion": "Sección",
            "subseccion": "Subsección",
        }
        return f"{word[self.kind]} {self.number}."


@dataclass
class Transitorio:
    block: int
    ordinal: str
    number: int
    paragraphs: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(self.paragraphs)


@dataclass
class ModificationBlock:
    """A resolución de modificaciones as the compiled edition appends it."""

    block: int
    label: str
    resolutivos: List[str] = field(default_factory=list)


@dataclass
class RmfDocument:
    glossary: List[str] = field(default_factory=list)
    divisions: List[Division] = field(default_factory=list)
    transitorios: List[Transitorio] = field(default_factory=list)
    modifications: List[ModificationBlock] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def iter_rules(self) -> Iterator[Rule]:
        def walk(nodes):
            for node in nodes:
                if isinstance(node, Rule):
                    yield node
                else:
                    yield from walk(node.children)

        yield from walk(self.divisions)

    def rules(self) -> List[Rule]:
        return list(self.iter_rules())

    def rule(self, number: str) -> Optional[Rule]:
        wanted = number.rstrip(".")
        for rule in self.iter_rules():
            if rule.number == wanted:
                return rule
        return None

    def transitorio(self, number: int, block: int = 1) -> Optional[Transitorio]:
        for item in self.transitorios:
            if item.block == block and item.number == number:
                return item
        return None


# --------------------------------------------------------------------------
# Paragraph assembly
# --------------------------------------------------------------------------


class _Paragraphs:
    """Re-joins PDF lines into paragraphs."""

    def __init__(self) -> None:
        self.items: List[str] = []

    def add(self, text: str, force_new: bool = False) -> None:
        text = text.strip()
        if not text:
            return
        if not self.items or force_new or _starts_paragraph(self.items[-1], text):
            self.items.append(text)
        else:
            self.items[-1] = _join_wrapped(self.items[-1], text)


# "… artículo 113-" + "E de la Ley" is "113-E", not "113- E". Only a hyphen
# glued to a letter or digit; a spaced dash ("texto -") is punctuation.
_WRAPPED_HYPHEN_RE = re.compile(r"[\wÁÉÍÓÚÑáéíóúñ]-$")


def _join_wrapped(previous: str, line: str) -> str:
    if _WRAPPED_HYPHEN_RE.search(previous):
        return f"{previous}{line}"
    return f"{previous} {line}"


def _starts_paragraph(previous: str, line: str) -> bool:
    if _LIST_ITEM_RE.match(line):
        return True
    if previous.count("“") > previous.count("”") + previous.count('"'):
        # Inside a quoted name: 'la declaración “ISR de confianza.' +
        # 'Personas Morales”' is one sentence.
        return False
    return previous.rstrip().endswith((".", ":", ";", ".”", '."')) and (
        line[:1].isupper() or line[:1] in '“"('
    )


def _parent_number(number: str) -> str:
    return number.rsplit(".", 1)[0]


def _last_component(number: str) -> int:
    return int(number.rsplit(".", 1)[1])


# --------------------------------------------------------------------------
# Segmenter
# --------------------------------------------------------------------------

_DIVISION_DEPTH = {"titulo": 0, "capitulo": 1, "seccion": 2, "subseccion": 3}
_KIND_BY_WORD = {
    "Título": "titulo",
    "Capítulo": "capitulo",
    "Sección": "seccion",
    "Subsección": "subseccion",
}


class _Segmenter:
    def __init__(self, lines: Sequence[SourceLine]) -> None:
        self.lines = lines
        self.doc = RmfDocument()
        self.phase = "front"
        self.stack: List[Division] = []  # open divisions, outermost first
        self.heading_open: Optional[Division] = None
        self.pending_title: List[str] = []
        self.pending_notes: List[str] = []
        self.in_note = False
        self.rule: Optional[Rule] = None
        self.rule_body: Optional[_Paragraphs] = None
        self.rule_refs: List[str] = []
        self.glossary = _Paragraphs()
        self.glossary_after_bold = False
        self.block = 1
        self.transitorio: Optional[Transitorio] = None
        self.transitorio_body: Optional[_Paragraphs] = None
        self.pending_tens: Optional[str] = None
        self.modification: Optional[ModificationBlock] = None
        self.modification_label_open = False

    # -- helpers ----------------------------------------------------------

    def warn(self, message: str, line: Optional[SourceLine] = None) -> None:
        where = f" (p. {line.page})" if line is not None and line.page else ""
        self.doc.warnings.append(f"{message}{where}")

    def _note(self, line: SourceLine) -> bool:
        """Consume compiler notes ("Regla 2.1.6." + "- Reformada en …")."""
        text = line.text
        if line.style == STYLE_BOLD_ITALIC and NOTE_MARKER_RE.match(text):
            self.pending_notes.append(text)
            self.in_note = True
            return True
        if not self.in_note:
            return False
        if line.style in (STYLE_ITALIC, STYLE_BOLD_ITALIC) or (
            line.style == STYLE_REGULAR
            and (
                text.startswith("- ")
                or not self.pending_notes[-1].rstrip().endswith(".")
            )
        ):
            if text.startswith("- ") or not self.pending_notes:
                self.pending_notes.append(text)
            else:
                self.pending_notes[-1] = f"{self.pending_notes[-1]} {text}"
            return True
        self.in_note = False
        return False

    def _close_rule(self) -> None:
        if self.rule is None:
            return
        if self.pending_title:
            # Bold lines that never led to a rule number are emphasis inside
            # the rule (a bold table header, a bold defined term).
            for text in self.pending_title:
                self.rule_body.add(text, force_new=True)
            self.pending_title = []
        self.rule.paragraphs = list(self.rule_body.items)
        self.rule.references = " ".join(self.rule_refs).strip()
        if not self.rule.paragraphs and self.rule.references:
            self.warn(f"regla {self.rule.number}: only references, no text")
        self.rule = None
        self.rule_body = None
        self.rule_refs = []

    def _close_transitorio(self) -> None:
        if self.transitorio is None:
            return
        self.transitorio.paragraphs = list(self.transitorio_body.items)
        self.doc.transitorios.append(self.transitorio)
        self.transitorio = None
        self.transitorio_body = None

    def _rule_parent(self, number: str) -> Optional[int]:
        """Index in ``self.stack`` of the division a rule number belongs to."""
        parent = _parent_number(number)
        for depth in range(len(self.stack) - 1, -1, -1):
            if self.stack[depth].number == parent:
                return depth
        return None

    # -- phases -----------------------------------------------------------

    def run(self) -> RmfDocument:
        for line in self.lines:
            handler = getattr(self, f"_on_{self.phase}")
            handler(line)
        self._close_rule()
        self._close_transitorio()
        self.doc.glossary = list(self.glossary.items)
        if not any(True for _ in self.doc.iter_rules()):
            self.warn("no rules found")
        return self.doc

    def _on_front(self, line: SourceLine) -> None:
        if GLOSSARY_START_RE.match(line.text):
            self.phase = "glossary"
            self.glossary.add(line.text)

    def _on_glossary(self, line: SourceLine) -> None:
        m = HEADING_RE.match(line.text)
        if line.style == STYLE_BOLD and m and m.group(1) == "Título":
            self.phase = "rules"
            self._on_rules(line)
            return
        bold = line.style == STYLE_BOLD
        self.glossary.add(line.text, force_new=bold or self.glossary_after_bold)
        self.glossary_after_bold = bold

    def _open_division(self, kind: str, number: str, heading: str, line) -> bool:
        depth = _DIVISION_DEPTH[kind]
        if depth > len(self.stack):
            return False
        if depth > 0 and not number.startswith(self.stack[depth - 1].number + "."):
            return False
        if depth == 0 and "." in number:
            return False
        division = Division(kind=kind, number=number, heading=heading.strip())
        del self.stack[depth:]
        if self.stack:
            self.stack[-1].children.append(division)
        else:
            self.doc.divisions.append(division)
        self.stack.append(division)
        self.heading_open = division
        return True

    def _on_rules(self, line: SourceLine) -> None:
        text = line.text
        if self._note(line):
            return

        if line.style == STYLE_BOLD:
            m = HEADING_RE.match(text)
            if m:
                kind = _KIND_BY_WORD[m.group(1)]
                if not self.pending_title:
                    self._close_rule()
                    if self._open_division(kind, m.group(2), m.group(3), line):
                        return
                    self.warn(f"heading out of sequence ignored: {text[:60]}", line)
            if line.align != ALIGN_BODY and TRANSITORIOS_HEADING_RE.match(text):
                self._close_rule()
                self.heading_open = None
                self.stack = []
                self.phase = "transitorios"
                self.block = 1
                return
            # A derogated rule is printed all in bold: "2.12.4. Se deroga."
            if line.align == ALIGN_HANGING and self._try_open_rule(line):
                return
            # Headings are centred, but a long centred line can start right at
            # the body indent. It still belongs to the heading when it opens in
            # lowercase (an epígrafe always opens with a capital) or when the
            # heading so far ends mid-phrase ("… en los Polos de").
            if self.heading_open is not None and (
                line.align != ALIGN_BODY
                or text[:1].islower()
                or _UNFINISHED_RE.search(self.heading_open.heading)
            ):
                self.heading_open.heading = (
                    f"{self.heading_open.heading} {text}".strip()
                )
                return
            self.heading_open = None
            if RULE_NUMBER_RE.match(text):
                self.warn(
                    f"bold line that looks like a rule kept as epígrafe: {text[:60]}",
                    line,
                )
            if not self.pending_title and text[:1].islower():
                self.warn(f"epígrafe starts in lowercase: {text[:60]}", line)
            self.pending_title.append(text)
            return

        self.heading_open = None
        if line.style == STYLE_REGULAR and self._try_open_rule(line):
            return

        if self.rule is None:
            if self.pending_title or text:
                self.warn(f"text outside any rule dropped: {text[:60]}", line)
            self.pending_title = []
            return
        if self.pending_title:
            for bold_text in self.pending_title:
                self.rule_body.add(bold_text, force_new=True)
            self.pending_title = []
        if line.style == STYLE_ITALIC:
            self.rule_refs.append(text)
            return
        if self.rule_refs:
            # Italic text followed by more body: it was emphasis, not the
            # closing references.
            for ref in self.rule_refs:
                self.rule_body.add(ref)
            self.rule_refs = []
        self.rule_body.add(text)

    def _try_open_rule(self, line: SourceLine) -> bool:
        m = RULE_NUMBER_RE.match(line.text)
        if not m:
            return False
        number, rest = m.group(1), m.group(2)
        depth = self._rule_parent(number)
        if depth is None or not (self.pending_title or line.align == ALIGN_HANGING):
            return False
        title = " ".join(self.pending_title)
        self.pending_title = []
        self._close_rule()
        self.heading_open = None
        del self.stack[depth + 1 :]
        self._open_rule(number, title, rest, line)
        return True

    def _open_rule(self, number: str, title: str, rest: str, line: SourceLine) -> None:
        siblings = [c for c in self.stack[-1].children if isinstance(c, Rule)]
        if siblings and _last_component(number) <= _last_component(siblings[-1].number):
            self.warn(f"regla {number} after {siblings[-1].number}", line)
        if not title:
            self.warn(f"regla {number} has no epígrafe", line)
        path = {d.kind: d.number for d in self.stack}
        self.rule = Rule(
            number=number,
            title=title,
            notes=self.pending_notes,
            titulo=path.get("titulo", ""),
            capitulo=path.get("capitulo", ""),
            seccion=path.get("seccion", ""),
            subseccion=path.get("subseccion", ""),
        )
        self.pending_notes = []
        self.rule_body = _Paragraphs()
        self.rule_refs = []
        if rest:
            self.rule_body.add(rest)
        self.stack[-1].children.append(self.rule)

    # -- transitorios -------------------------------------------------------

    def _transitorio_line(self, line: SourceLine) -> bool:
        """Open a transitorio if ``line`` starts one. Returns True if consumed."""
        text = line.text
        if line.style == STYLE_BOLD and ORDINAL_TENS_LINE_RE.match(text):
            self.pending_tens = text
            return True
        if line.style != STYLE_REGULAR:
            return False
        m = TRANSITORIO_RE.match(text)
        if not m or not (self.pending_tens or line.align == ALIGN_HANGING):
            return False
        ordinal = m.group(1)
        if self.pending_tens:
            ordinal = f"{self.pending_tens} {ordinal}"
            self.pending_tens = None
        ordinal = " ".join(_FEMININE_TO_MASCULINE.get(w, w) for w in ordinal.split())
        number = 1 if ordinal == "Único" else ordinal_to_number(ordinal)
        if number is None:
            return False
        self._close_transitorio()
        self.transitorio = Transitorio(
            block=self.block, ordinal=ordinal, number=number, notes=self.pending_notes
        )
        self.pending_notes = []
        self.transitorio_body = _Paragraphs()
        if m.group(2):
            self.transitorio_body.add(m.group(2))
        return True

    def _start_modification(self, line: SourceLine) -> bool:
        m = MODIFICATION_RE.match(line.text)
        if line.style != STYLE_BOLD or not m:
            return False
        self._close_transitorio()
        self.pending_tens = None
        number = ordinal_to_number(m.group(1))
        self.block = (number or len(self.doc.modifications) + 1) + 1
        self.modification = ModificationBlock(block=self.block, label=line.text)
        self.doc.modifications.append(self.modification)
        self.modification_label_open = True
        self.phase = "modification"
        return True

    def _on_transitorios(self, line: SourceLine) -> None:
        if self._note(line):
            return
        if self._start_modification(line):
            return
        if self._transitorio_line(line):
            return
        if line.style == STYLE_REGULAR and SIGNATURE_RE.match(line.text):
            self._close_transitorio()
            self.phase = "closing"
            return
        if self.pending_tens:
            # A bold tens word not followed by an ordinal line is plain text.
            self._append_transitorio_text(self.pending_tens, line)
            self.pending_tens = None
        self._append_transitorio_text(line.text, line)

    def _append_transitorio_text(self, text: str, line: SourceLine) -> None:
        if self.transitorio is None:
            self.warn(f"text outside any transitorio dropped: {text[:60]}", line)
            return
        self.transitorio_body.add(text)

    def _on_closing(self, line: SourceLine) -> None:
        # Signature block of the base resolution; only a later modification
        # block (compiled edition) is content.
        self._start_modification(line)

    def _on_modification(self, line: SourceLine) -> None:
        text = line.text
        if self.modification_label_open:
            if line.style == STYLE_BOLD and not TRANSITORIOS_HEADING_RE.match(text):
                self.modification.label = f"{self.modification.label} {text}"
                return
            self.modification_label_open = False
        if self._start_modification(line):
            return
        if line.style == STYLE_BOLD and TRANSITORIOS_HEADING_RE.match(text):
            self.phase = "modification_transitorios"
            return
        if RESOLUTIVO_RE.match(text) or not self.modification.resolutivos:
            self.modification.resolutivos.append(text)
        else:
            self.modification.resolutivos[-1] = (
                f"{self.modification.resolutivos[-1]} {text}"
            )

    def _on_modification_transitorios(self, line: SourceLine) -> None:
        if self._note(line):
            return
        if self._start_modification(line):
            return
        if self._transitorio_line(line):
            return
        if line.style == STYLE_REGULAR and SIGNATURE_RE.match(line.text):
            self._close_transitorio()
            self.phase = "closing"
            return
        self._append_transitorio_text(line.text, line)


def segment(lines: Sequence[SourceLine]) -> RmfDocument:
    """Segment RMF lines into rules and transitorios. Pure; never raises on
    odd input — anything it cannot place is reported in ``warnings``."""
    return _Segmenter(lines).run()


def validate(doc: RmfDocument) -> List[str]:
    """Problems that make a parse unfit for ingestion (empty if fit)."""
    problems: List[str] = []
    rules = doc.rules()
    if not rules:
        problems.append("no rules parsed")
    seen = set()
    for rule in rules:
        if rule.number in seen:
            problems.append(f"duplicate regla {rule.number}")
        seen.add(rule.number)
        if not rule.paragraphs:
            problems.append(f"regla {rule.number} has no text")
    keys = set()
    for item in doc.transitorios:
        key = (item.block, item.number)
        if key in keys:
            problems.append(
                f"duplicate transitorio {item.ordinal} (block {item.block})"
            )
        keys.add(key)
    if not any(t.block == 1 for t in doc.transitorios):
        problems.append("no transitorios of the base resolution")
    return problems
