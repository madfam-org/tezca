"""
RMF (Resolución Miscelánea Fiscal) Scraper.

Fetches the current year's RMF and its annexes from the SAT portal. The RMF
is published annually with quarterly modifications and contains the
administrative rules that implement the CFF and other tax laws — including
Rule 2.9.21 (API + technical requirements for digital platforms).

This is the SAT-side regulatory feed that Karafiel's compliance use case
depends on (per `docs/strategy/FEATURE_PARITY_PLAN_2026-04-27.md` §3.6).

Strategy: requests-first for the listing pages (they're server-rendered
HTML on www.sat.gob.mx, which has valid TLS — no INSECURE_HOSTS entry
needed). PDF + DOCX downloads use the same session. Parsing of the
downloaded documents is delegated to the existing ingestion pipeline
(parser_v2 → DatabaseSaver) once the metadata + text files land on disk.

Key targets:
- Annual RMF document
- Quarterly modifications (1a, 2a, 3a, 4a)
- Annexes 1-31 (tax tables, forms, technical requirements)
- Rule 2.9.21 (digital-platform API requirements — Karafiel-relevant)

Usage::

    python -m apps.scraper.federal.rmf_scraper --year 2026
    python -m apps.scraper.federal.rmf_scraper --year 2026 --include-annexes
    python -m apps.scraper.federal.rmf_scraper --year 2026 --output-dir data/rmf
"""

import argparse
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from apps.scraper.http import DEFAULT_TIMEOUT, DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Source URLs (SAT — www.sat.gob.mx — valid TLS, no INSECURE_HOSTS entry)
# ---------------------------------------------------------------------------

SAT_BASE = "https://www.sat.gob.mx"
SAT_RMF_INDEX = f"{SAT_BASE}/normatividad/22702/resoluciones-miscelaneas-fiscales"
SAT_RMF_ANNEXES_INDEX = (
    f"{SAT_BASE}/normatividad/22703/anexos-de-la-resolucion-miscelanea-fiscal"
)

# ---------------------------------------------------------------------------
# Behavior knobs
# ---------------------------------------------------------------------------

_MIN_REQUEST_INTERVAL = 1.0  # seconds — polite to SAT
_REQUEST_TIMEOUT = DEFAULT_TIMEOUT
_MAX_RETRIES = 3

# RMF document type prefixes used in SAT page anchor text
_RMF_TYPES = ("RMF", "Anexo", "Modificación", "1a.", "2a.", "3a.", "4a.")

# Identifies a 4-digit year to anchor the document to
_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

# Common file extensions SAT links to
_DOCUMENT_EXTENSIONS = (".pdf", ".doc", ".docx")

# Categories assigned to ingested Law records
RMF_CATEGORY = "resolución_miscelánea_fiscal"
RMF_DOMAINS = ["fiscal"]


@dataclass
class RmfDocument:
    """Single RMF artifact discovered on the SAT portal.

    Mirrors the shape that DatabaseSaver / ingest_non_legislative_laws
    expects: an ``official_id`` plus enough metadata to derive a Law +
    LawVersion row, plus a ``url`` to download the actual content.
    """

    official_id: str
    name: str
    url: str
    document_type: str  # "rmf" | "modification" | "annex"
    year: int
    publication_date: Optional[str] = None
    annex_number: Optional[str] = None
    modification_number: Optional[str] = None
    category: str = RMF_CATEGORY
    domains: List[str] = field(default_factory=lambda: list(RMF_DOMAINS))
    source: str = "sat_rmf_scraper"


class RmfScraper:
    """Scraper for SAT's annual RMF + quarterly modifications + annexes.

    Concrete coverage:

    1. Annual RMF — one document per fiscal year
    2. Modifications — typically 1a/2a/3a/4a per year
    3. Annexes — numbered 1 through ~31 each year (varies)

    Output: a JSON catalog of discovered ``RmfDocument`` records plus
    downloaded source files, ready for the parser pipeline +
    ``ingest_non_legislative_laws`` analogue to materialize as Law +
    Article rows.
    """

    def __init__(self, output_dir: str = "data/rmf") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._session = self._build_session()
        self._last_request_at: float = 0.0

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    @staticmethod
    def _build_session() -> requests.Session:
        """Return a session configured for sat.gob.mx.

        SAT's portal has a valid certificate chain (verified 2026-04-27),
        so no INSECURE_HOSTS bypass is needed. Retries are conservative —
        the SAT WAF gets unhappy with rapid retries; we'd rather fail
        fast and let Celery retry the whole task than hammer them.
        """
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/html, application/xhtml+xml, */*",
                "Accept-Language": "es-MX,es;q=0.9,en;q=0.5",
            }
        )
        return session

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_at
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_at = time.time()

    def _get(self, url: str) -> Optional[requests.Response]:
        """Polite GET with bounded retries on transient errors."""
        for attempt in range(1, _MAX_RETRIES + 1):
            self._rate_limit()
            try:
                resp = self._session.get(url, timeout=_REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response else None
                if status in (403, 404):
                    # Permanent — no point retrying.
                    logger.warning("HTTP %s for %s", status, url)
                    return None
                logger.warning(
                    "HTTP %s for %s (attempt %d/%d)",
                    status,
                    url,
                    attempt,
                    _MAX_RETRIES,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                logger.warning(
                    "Network error for %s (attempt %d/%d): %s",
                    url,
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
            time.sleep(2**attempt)  # exponential backoff: 2s, 4s, 8s
        logger.error("Giving up on %s after %d attempts", url, _MAX_RETRIES)
        return None

    # ------------------------------------------------------------------
    # Index parsing
    # ------------------------------------------------------------------

    def _parse_index_links(
        self, html: str, base_url: str, year: int
    ) -> List[Dict[str, str]]:
        """Extract document links from a SAT index page.

        SAT's RMF + annexes index pages are standard HTML lists of
        anchors pointing to PDF/DOC/DOCX files (sometimes with an
        intermediate microsite landing page). We collect the
        (text, href) pairs and let the caller classify each one.
        """
        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, str]] = []

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            text = " ".join(anchor.get_text().split())
            if not text:
                continue

            # Year filter: skip anchors that name a different year explicitly.
            year_matches = [int(m.group(0)) for m in _YEAR_PATTERN.finditer(text)]
            if year_matches and year not in year_matches:
                continue

            # Absolute URL
            if href.startswith("/"):
                href = f"{SAT_BASE}{href}"
            elif not href.startswith("http"):
                href = f"{base_url.rstrip('/')}/{href}"

            # Heuristic: skip nav/footer links that don't look like documents.
            looks_like_document = (
                href.lower().endswith(_DOCUMENT_EXTENSIONS)
                or "rmf" in text.lower()
                or "anexo" in text.lower()
                or "modificación" in text.lower()
                or "modificacion" in text.lower()
                or "miscelánea" in text.lower()
                or "miscelanea" in text.lower()
            )
            if not looks_like_document:
                continue

            results.append({"text": text, "url": href})

        return results

    def _classify(self, anchor: Dict[str, str], year: int) -> Optional[RmfDocument]:
        """Turn a raw (text, url) pair into an :class:`RmfDocument`.

        Returns ``None`` when the anchor doesn't look like an RMF
        artifact we care about — defensive guard against picking up
        unrelated SAT links present on the index page.
        """
        text = anchor["text"]
        url = anchor["url"]
        text_lower = text.lower()

        # Annex detection — "Anexo 1", "Anexo 14", etc.
        annex_match = re.search(r"anexo\s+(\d{1,2}(?:[a-z])?)", text_lower)
        if annex_match:
            annex_num = annex_match.group(1)
            return RmfDocument(
                official_id=f"rmf_{year}_anexo_{annex_num}",
                name=f"Anexo {annex_num} de la RMF {year}",
                url=url,
                document_type="annex",
                year=year,
                annex_number=annex_num,
            )

        # Modification detection — "Primera Modificación", "1a. Modificación", etc.
        mod_match = re.search(
            r"(primera|segunda|tercera|cuarta|1a\.?|2a\.?|3a\.?|4a\.?)\s*"
            r"(?:modificaci[oó]n|resoluci[oó]n)",
            text_lower,
        )
        if mod_match:
            ordinal = {
                "primera": "1",
                "segunda": "2",
                "tercera": "3",
                "cuarta": "4",
                "1a": "1",
                "1a.": "1",
                "2a": "2",
                "2a.": "2",
                "3a": "3",
                "3a.": "3",
                "4a": "4",
                "4a.": "4",
            }.get(mod_match.group(1).rstrip("."), "1")
            return RmfDocument(
                official_id=f"rmf_{year}_modificacion_{ordinal}",
                name=f"{ordinal}ª Modificación a la RMF {year}",
                url=url,
                document_type="modification",
                year=year,
                modification_number=ordinal,
            )

        # Annual RMF detection — "Resolución Miscelánea Fiscal para 2026"
        if "miscelánea fiscal" in text_lower or "miscelanea fiscal" in text_lower:
            return RmfDocument(
                official_id=f"rmf_{year}",
                name=f"Resolución Miscelánea Fiscal {year}",
                url=url,
                document_type="rmf",
                year=year,
            )

        return None

    # ------------------------------------------------------------------
    # Top-level discovery
    # ------------------------------------------------------------------

    def discover(self, year: int, include_annexes: bool = True) -> List[RmfDocument]:
        """Walk the SAT RMF + annex indices for ``year`` and return all
        unique ``RmfDocument`` records discovered.

        Deduplication is by ``official_id`` — if the same artifact appears
        on both index pages (which it sometimes does), we keep the first.
        """
        documents: Dict[str, RmfDocument] = {}

        # 1. Main RMF + modifications index
        index_resp = self._get(SAT_RMF_INDEX)
        if index_resp:
            for anchor in self._parse_index_links(index_resp.text, SAT_RMF_INDEX, year):
                doc = self._classify(anchor, year)
                if doc and doc.official_id not in documents:
                    documents[doc.official_id] = doc
        else:
            logger.error("Failed to load RMF main index — discovery incomplete")

        # 2. Annexes index (optional — annex parsing is heavier)
        if include_annexes:
            annexes_resp = self._get(SAT_RMF_ANNEXES_INDEX)
            if annexes_resp:
                for anchor in self._parse_index_links(
                    annexes_resp.text, SAT_RMF_ANNEXES_INDEX, year
                ):
                    doc = self._classify(anchor, year)
                    if doc and doc.official_id not in documents:
                        documents[doc.official_id] = doc
            else:
                logger.warning(
                    "Failed to load RMF annexes index — annexes will be missing"
                )

        return sorted(documents.values(), key=lambda d: d.official_id)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def download(self, document: RmfDocument) -> Optional[Path]:
        """Download a single RMF artifact to ``self.output_dir``.

        Returns the local Path on success, None on failure. The caller
        is responsible for downstream parsing (PDF text extraction,
        article splitting) — this function only fetches the bytes.
        """
        resp = self._get(document.url)
        if not resp:
            return None

        # Pick a sensible filename from the URL or fall back to official_id.
        url_name = document.url.rsplit("/", 1)[-1].split("?")[0]
        if any(url_name.lower().endswith(ext) for ext in _DOCUMENT_EXTENSIONS):
            filename = f"{document.official_id}_{url_name}"
        else:
            filename = f"{document.official_id}.html"

        target = self.output_dir / filename
        target.write_bytes(resp.content)
        logger.info(
            "Downloaded %s → %s (%d bytes)",
            document.official_id,
            target,
            len(resp.content),
        )
        return target

    def write_catalog(self, documents: List[RmfDocument]) -> Path:
        """Write the discovered catalog to ``catalog.json`` for the
        ingestion pipeline to pick up.
        """
        catalog_path = self.output_dir / "catalog.json"
        payload = [asdict(d) for d in documents]
        catalog_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(
            "Wrote catalog with %d documents → %s", len(documents), catalog_path
        )
        return catalog_path

    # ------------------------------------------------------------------
    # End-to-end run
    # ------------------------------------------------------------------

    def run(
        self,
        year: int = 2026,
        include_annexes: bool = True,
        download_documents: bool = False,
    ) -> Dict[str, Any]:
        """Discover + (optionally) download RMF artifacts for ``year``.

        Args:
            year: Target fiscal year.
            include_annexes: Walk the annexes index too.
            download_documents: When True, fetch each document's bytes
                to disk. Default False so a fast catalog-only sweep can
                run in CI / tests without N HTTP fetches.

        Returns:
            Summary dict suitable for AcquisitionLog persistence:
            ``{total, by_type, downloaded, errors, catalog_path}``.
        """
        documents = self.discover(year=year, include_annexes=include_annexes)

        downloaded = 0
        errors = 0
        if download_documents:
            for doc in documents:
                if self.download(doc):
                    downloaded += 1
                else:
                    errors += 1

        catalog_path = self.write_catalog(documents)

        by_type: Dict[str, int] = {}
        for doc in documents:
            by_type[doc.document_type] = by_type.get(doc.document_type, 0) + 1

        result = {
            "year": year,
            "total": len(documents),
            "by_type": by_type,
            "downloaded": downloaded,
            "errors": errors,
            "catalog_path": str(catalog_path),
        }
        logger.info("RMF run complete: %s", result)
        return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape the SAT RMF + modifications + annexes for a year"
    )
    parser.add_argument(
        "--year", type=int, default=2026, help="Fiscal year to scrape (default: 2026)"
    )
    parser.add_argument(
        "--include-annexes",
        action="store_true",
        default=True,
        help="Walk the annexes index too (default: on)",
    )
    parser.add_argument(
        "--no-annexes",
        dest="include_annexes",
        action="store_false",
        help="Skip the annexes index",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Fetch each document's bytes to disk (slow)",
    )
    parser.add_argument(
        "--output-dir", default="data/rmf", help="Where to write catalog + downloads"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    scraper = RmfScraper(output_dir=args.output_dir)
    result = scraper.run(
        year=args.year,
        include_annexes=args.include_annexes,
        download_documents=args.download,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
