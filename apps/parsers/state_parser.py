"""
State/Municipal Law Parser - Adapts IngestionPipeline for non-federal laws.

State and municipal laws are already downloaded as raw text (.txt) or PDF (.pdf).
This parser reads existing files, generates AKN XML via AkomaNtosoGeneratorV2,
calculates quality metrics, and optionally detects cross-references.

Unlike the federal IngestionPipeline, this does NOT download from URLs.
"""

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from apps.parsers.akn_generator_v2 import AkomaNtosoGeneratorV2
from apps.parsers.quality import QualityCalculator, QualityMetrics


@dataclass
class StateParseResult:
    """Result of parsing a state/municipal law."""

    official_id: str
    law_name: str
    success: bool = False
    error: Optional[str] = None

    text_path: Optional[Path] = None
    akn_path: Optional[Path] = None
    quality_metrics: Optional[QualityMetrics] = None
    duration_seconds: float = 0.0
    article_count: int = 0

    def summary(self) -> str:
        status = "OK" if self.success else "FAIL"
        grade = self.quality_metrics.grade if self.quality_metrics else "N/A"
        return (
            f"[{status}] {self.official_id}: "
            f"{self.article_count} articles, Grade {grade} "
            f"({self.duration_seconds:.1f}s)"
        )


class StateLawParser:
    """
    Parser for state and municipal laws.

    Reads existing text files, generates Akoma Ntoso XML using V2 parser,
    calculates quality, and saves AKN XML alongside source files.
    """

    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
        self.base_dir = base_dir
        self.parser = AkomaNtosoGeneratorV2()
        self.quality_calc = QualityCalculator()

    def _slugify(self, text: str) -> str:
        """Create a URL-safe slug from text."""
        slug = text.lower().strip()
        # Remove accents (simple approach)
        replacements = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ñ": "n",
            "ü": "u",
        }
        for char, replacement in replacements.items():
            slug = slug.replace(char, replacement)
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        return slug[:100]  # Cap length

    def _create_state_frbr_metadata(
        self, law_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create FRBR metadata adapted for state/municipal laws."""
        law_name = law_metadata.get("law_name", "Unknown")
        state = law_metadata.get("state", "unknown")
        tier = law_metadata.get("tier", "state")
        municipality = law_metadata.get("municipality", "")
        pub_date = law_metadata.get("publication_date", "2023-01-01")
        official_id = law_metadata.get("official_id", "unknown")

        state_slug = self._slugify(state)
        law_slug = self._slugify(law_name)

        # Build jurisdiction path
        if tier == "municipal" and municipality:
            muni_slug = self._slugify(municipality)
            jurisdiction = f"mx/{state_slug}/{muni_slug}"
        else:
            jurisdiction = f"mx/{state_slug}"

        # Determine law type from name
        name_lower = law_name.lower()
        if "código" in name_lower or "codigo" in name_lower:
            law_type = "codigo"
        elif "reglamento" in name_lower:
            law_type = "reglamento"
        elif "decreto" in name_lower:
            law_type = "decreto"
        else:
            law_type = "ley"

        return {
            "work_uri": f"/{jurisdiction}/{law_type}/{pub_date}/{law_slug}/main",
            "expression_uri": (
                f"/{jurisdiction}/{law_type}/{pub_date}/{law_slug}/spa@/main"
            ),
            "manifestation_uri": (
                f"/{jurisdiction}/{law_type}/{pub_date}/{law_slug}/spa@/main.xml"
            ),
            "date": pub_date,
            "title": law_name,
            "country": "mx",
            "language": "spa",
            "law_id": official_id,
            "status": law_metadata.get("status", "vigente"),
        }

    def _determine_akn_output_path(self, law_metadata: Dict[str, Any]) -> Path:
        """Determine where to write the AKN XML file."""
        tier = law_metadata.get("tier", "state")
        state = law_metadata.get("state", "unknown")
        state_slug = self._slugify(state)
        official_id = law_metadata.get("official_id", "unknown")

        if tier == "municipal":
            municipality = law_metadata.get("municipality", "unknown")
            muni_slug = self._slugify(municipality)
            akn_dir = self.base_dir / "data" / "municipal" / muni_slug / "akn"
        else:
            akn_dir = self.base_dir / "data" / "state_laws" / state_slug / "akn"

        akn_dir.mkdir(parents=True, exist_ok=True)
        return akn_dir / f"{official_id}-v2.xml"

    def parse_law(self, law_metadata: Dict[str, Any]) -> StateParseResult:
        """
        Parse a single state/municipal law to AKN XML.

        Args:
            law_metadata: Dict with keys: official_id, law_name, state, tier,
                         text_file (relative path to raw text),
                         publication_date (optional), municipality (optional)

        Returns:
            StateParseResult with paths and quality info
        """
        start_time = time.time()
        official_id = law_metadata.get("official_id", "unknown")
        law_name = law_metadata.get("law_name", "Unknown")

        result = StateParseResult(official_id=official_id, law_name=law_name)

        try:
            # 1. Locate source text file
            text_file = law_metadata.get("text_file", "")
            if not text_file:
                result.error = "No text_file in metadata"
                return result

            # Resolve path (Docker or local)
            from apps.api.utils.paths import resolve_data_path_or_none

            text_path = resolve_data_path_or_none(text_file)
            if not text_path:
                result.error = f"Text file not found: {text_file}"
                return result

            result.text_path = text_path

            # 2. Read text content
            if text_path.suffix.lower() == ".pdf":
                text = self._extract_pdf_text(text_path)
            else:
                text = text_path.read_text(encoding="utf-8", errors="ignore")

            if not text or len(text.strip()) < 100:
                result.error = f"Text too short ({len(text.strip())} chars)"
                return result

            # 3. Generate AKN XML
            akn_path = self._determine_akn_output_path(law_metadata)
            metadata = self._create_state_frbr_metadata(law_metadata)

            _, parse_result = self.parser.generate_xml(text, metadata, akn_path)

            result.akn_path = akn_path
            result.article_count = parse_result.metadata.get("articles", 0)

            # 4. Calculate quality
            parse_time = time.time() - start_time
            slug = self._slugify(law_name)
            try:
                quality = self.quality_calc.calculate(
                    xml_path=akn_path,
                    law_name=law_name,
                    law_slug=slug,
                    articles_expected=None,
                    parse_time=parse_time,
                    parser_confidence=parse_result.confidence,
                )
                result.quality_metrics = quality
            except Exception as e:
                # Quality calc failure is non-fatal
                pass

            # 5. Cross-references (optional, non-fatal)
            try:
                from apps.parsers.cross_reference_integration import (
                    detect_and_store_cross_references,
                )

                detect_and_store_cross_references(official_id, akn_path)
            except Exception:
                pass

            result.success = True
            result.duration_seconds = time.time() - start_time
            return result

        except Exception as e:
            result.error = str(e)
            result.duration_seconds = time.time() - start_time
            return result

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from a PDF file using pdfplumber."""
        try:
            import pdfplumber

            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except ImportError:
            raise RuntimeError(
                "pdfplumber required for PDF extraction: pip install pdfplumber"
            )
        except Exception as e:
            raise RuntimeError(f"PDF extraction failed for {pdf_path}: {e}")
