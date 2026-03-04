"""
PNT (Plataforma Nacional de Transparencia) SIPOT Municipal Scraper

Queries the PNT/SIPOT public API to discover and download municipal regulatory
documents ("reglamentos municipales") across all Mexican states and municipalities.

The PNT SIPOT API exposes transparency obligation data published by every
municipality in Mexico. This scraper targets the regulatory framework
obligation (Marco Normativo) to extract municipal reglamentos.

API base: https://consultapublica.plataformadetransparencia.org.mx/sipot-ws/
"""

import argparse
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from .base import MunicipalScraper

logger = logging.getLogger(__name__)

# PNT SIPOT API constants
PNT_API_BASE = "https://consultapublica.plataformadetransparencia.org.mx/sipot-ws/"
PNT_SUBJECTS_ENDPOINT = "obligation/subjects"
PNT_RECORDS_ENDPOINT = "obligation/records"

# SIPOT obligation ID for "Marco Normativo Aplicable" (Article 70, Fraction I)
# This is the standard PNT obligation that contains regulatory framework documents.
MARCO_NORMATIVO_OBLIGATION_ID = "I"

# Map from KNOWN_STATES keys to PNT state identifiers (1-indexed, alphabetical by
# official name as PNT uses INEGI-based state codes).
# PNT uses numeric state codes aligned with INEGI's catalogue.
INEGI_STATE_CODES: Dict[str, int] = {
    "aguascalientes": 1,
    "baja_california": 2,
    "baja_california_sur": 3,
    "campeche": 4,
    "coahuila": 5,
    "colima": 6,
    "chiapas": 7,
    "chihuahua": 8,
    "ciudad_de_mexico": 9,
    "durango": 10,
    "guanajuato": 11,
    "guerrero": 12,
    "hidalgo": 13,
    "jalisco": 14,
    "estado_de_mexico": 15,
    "michoacan": 16,
    "morelos": 17,
    "nayarit": 18,
    "nuevo_leon": 19,
    "oaxaca": 20,
    "puebla": 21,
    "queretaro": 22,
    "quintana_roo": 23,
    "san_luis_potosi": 24,
    "sinaloa": 25,
    "sonora": 26,
    "tabasco": 27,
    "tamaulipas": 28,
    "tlaxcala": 29,
    "veracruz": 30,
    "yucatan": 31,
    "zacatecas": 32,
}

# Reverse lookup: INEGI code -> state key
STATE_KEY_BY_CODE: Dict[int, str] = {v: k for k, v in INEGI_STATE_CODES.items()}

# Friendly state names for output (matches KNOWN_STATES values)
STATE_DISPLAY_NAMES: Dict[str, str] = {
    "aguascalientes": "Aguascalientes",
    "baja_california": "Baja California",
    "baja_california_sur": "Baja California Sur",
    "campeche": "Campeche",
    "chiapas": "Chiapas",
    "chihuahua": "Chihuahua",
    "ciudad_de_mexico": "Ciudad de Mexico",
    "coahuila": "Coahuila",
    "colima": "Colima",
    "durango": "Durango",
    "estado_de_mexico": "Estado de Mexico",
    "guanajuato": "Guanajuato",
    "guerrero": "Guerrero",
    "hidalgo": "Hidalgo",
    "jalisco": "Jalisco",
    "michoacan": "Michoacan",
    "morelos": "Morelos",
    "nayarit": "Nayarit",
    "nuevo_leon": "Nuevo Leon",
    "oaxaca": "Oaxaca",
    "puebla": "Puebla",
    "queretaro": "Queretaro",
    "quintana_roo": "Quintana Roo",
    "san_luis_potosi": "San Luis Potosi",
    "sinaloa": "Sinaloa",
    "sonora": "Sonora",
    "tabasco": "Tabasco",
    "tamaulipas": "Tamaulipas",
    "tlaxcala": "Tlaxcala",
    "veracruz": "Veracruz",
    "yucatan": "Yucatan",
    "zacatecas": "Zacatecas",
}

# Keywords for filtering regulatory documents from PNT results
REGULATORY_KEYWORDS = re.compile(
    r"reglamento|bando|codigo|código|normativ|lineamiento|decreto|acuerdo|manual",
    re.IGNORECASE,
)


def _sanitize_filename(name: str, max_length: int = 120) -> str:
    """
    Convert a document title into a safe filesystem name.

    Replaces non-alphanumeric characters (except period, hyphen, underscore)
    with underscores and truncates to max_length.
    """
    sanitized = re.sub(r"[^\w.\-]", "_", name, flags=re.UNICODE)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("_")
    return sanitized


class PNTMunicipalScraper(MunicipalScraper):
    """
    Scraper for the PNT (Plataforma Nacional de Transparencia) SIPOT API.

    Queries municipal regulatory framework obligations to discover reglamentos
    municipales, bandos, codigos, and related documents. Downloads linked PDFs
    to the standard data/municipal/{state}/{municipality}/ directory structure.

    The SIPOT API returns JSON payloads with document metadata including titles,
    publication dates, and links to hosted or external PDF files.
    """

    def __init__(
        self,
        state_key: str,
        municipality: Optional[str] = None,
        obligation_id: str = MARCO_NORMATIVO_OBLIGATION_ID,
    ):
        """
        Initialize the PNT scraper for a state and optionally a municipality.

        Args:
            state_key: State identifier matching KNOWN_STATES keys
                       (e.g. 'jalisco', 'nuevo_leon').
            municipality: Optional municipality name filter. If None, scrapes
                          all municipalities in the state.
            obligation_id: SIPOT obligation fraction identifier. Defaults to
                           "I" (Marco Normativo Aplicable).

        Raises:
            ValueError: If state_key is not recognized.
        """
        if state_key not in INEGI_STATE_CODES:
            raise ValueError(
                f"Unknown state key: {state_key}. "
                f"Valid keys: {', '.join(sorted(INEGI_STATE_CODES.keys()))}"
            )

        config = {
            "name": municipality or f"PNT-{state_key}",
            "state": STATE_DISPLAY_NAMES[state_key],
            "base_url": PNT_API_BASE,
        }
        super().__init__(config=config)

        self.state_key = state_key
        self.state_code = INEGI_STATE_CODES[state_key]
        self.municipality_filter = municipality
        self.obligation_id = obligation_id

        # PNT API requires JSON content type for POST requests
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        # Slightly longer interval for API requests to be respectful
        self.min_request_interval = 2.0

        logger.info(
            "Initialized PNT scraper for state=%s (code=%d), municipality=%s",
            self.state_key,
            self.state_code,
            self.municipality_filter or "ALL",
        )

    def _api_post(self, endpoint: str, payload: Dict) -> Optional[Dict]:
        """
        Make a POST request to the PNT SIPOT API.

        Args:
            endpoint: API endpoint path (appended to PNT_API_BASE).
            payload: JSON request body.

        Returns:
            Parsed JSON response dict, or None on failure.
        """
        url = urljoin(PNT_API_BASE, endpoint)
        self._rate_limit()

        try:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("PNT API error at %s: %s", endpoint, e)
            return None

    def _api_get(self, url: str) -> Optional[Dict]:
        """
        Make a GET request to a PNT API URL.

        Args:
            url: Full URL to query.

        Returns:
            Parsed JSON response dict, or None on failure.
        """
        self._rate_limit()
        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("PNT API GET error at %s: %s", url, e)
            return None

    def fetch_subjects(self) -> List[Dict]:
        """
        Fetch the list of obligated subjects (municipalities) for the state.

        Each subject represents a municipal government entity that publishes
        regulatory documents through the PNT.

        Returns:
            List of subject dicts with at minimum 'id' and 'name' keys.
        """
        payload = {
            "stateId": self.state_code,
            "governmentLevel": "Municipal",
            "obligationId": self.obligation_id,
        }

        logger.info(
            "Fetching PNT subjects for state=%s, level=Municipal",
            self.state_key,
        )

        data = self._api_post(PNT_SUBJECTS_ENDPOINT, payload)
        if not data:
            logger.error("Failed to fetch subjects for state %s", self.state_key)
            return []

        subjects = data if isinstance(data, list) else data.get("results", [])
        logger.info(
            "Found %d municipal subjects in %s",
            len(subjects),
            self.state_key,
        )
        return subjects

    def fetch_records(
        self, subject_id: str, page: int = 1, page_size: int = 100
    ) -> Optional[Dict]:
        """
        Fetch regulatory obligation records for a specific subject.

        Args:
            subject_id: PNT subject identifier for the municipality.
            page: Pagination page number (1-indexed).
            page_size: Number of records per page.

        Returns:
            API response dict with 'results' list and pagination info,
            or None on failure.
        """
        payload = {
            "subjectId": subject_id,
            "obligationId": self.obligation_id,
            "page": page,
            "pageSize": page_size,
        }

        return self._api_post(PNT_RECORDS_ENDPOINT, payload)

    def fetch_all_records(self, subject_id: str) -> List[Dict]:
        """
        Fetch all records for a subject, handling pagination.

        Args:
            subject_id: PNT subject identifier.

        Returns:
            Complete list of record dicts across all pages.
        """
        all_records: List[Dict] = []
        page = 1
        page_size = 100

        while True:
            data = self.fetch_records(subject_id, page=page, page_size=page_size)
            if not data:
                break

            records = data if isinstance(data, list) else data.get("results", [])
            if not records:
                break

            all_records.extend(records)

            # Check if there are more pages
            total = data.get("totalCount", 0) if isinstance(data, dict) else 0
            if total and len(all_records) >= total:
                break

            # Safety: if the API returns fewer records than page_size, we are done
            if len(records) < page_size:
                break

            page += 1

        return all_records

    def _extract_document_url(self, record: Dict) -> Optional[str]:
        """
        Extract the document URL from a PNT record.

        The SIPOT API stores document links in various fields depending on
        how the obligated subject uploaded the data. This method checks
        known field patterns.

        Args:
            record: Single record dict from the PNT API.

        Returns:
            Absolute URL string, or None if no document link found.
        """
        # Common field names where PNT stores document links
        url_fields = [
            "documentUrl",
            "document_url",
            "url",
            "linkDocumento",
            "link",
            "hipervinculo",
            "hipervínculo",
            "archivoUrl",
            "archivo",
        ]

        for field in url_fields:
            value = record.get(field)
            if value and isinstance(value, str) and value.startswith("http"):
                return value.strip()

        # Check nested fields structure (some records use a 'fields' list)
        fields = record.get("fields", [])
        if isinstance(fields, list):
            for field_entry in fields:
                if not isinstance(field_entry, dict):
                    continue
                field_value = field_entry.get("value", "")
                if isinstance(field_value, str) and field_value.startswith("http"):
                    return field_value.strip()

        return None

    def _extract_document_title(self, record: Dict) -> str:
        """
        Extract a meaningful title from a PNT record.

        Args:
            record: Single record dict from the PNT API.

        Returns:
            Document title string, or a fallback based on record ID.
        """
        title_fields = [
            "denominacion",
            "denominación",
            "title",
            "nombre",
            "name",
            "descripcion",
            "descripción",
            "fundamento",
        ]

        for field in title_fields:
            value = record.get(field)
            if value and isinstance(value, str) and len(value.strip()) > 3:
                return value.strip()

        # Check nested fields
        fields = record.get("fields", [])
        if isinstance(fields, list):
            for field_entry in fields:
                if not isinstance(field_entry, dict):
                    continue
                label = field_entry.get("label", "").lower()
                if any(
                    k in label for k in ["denominaci", "nombre", "titulo", "título"]
                ):
                    value = field_entry.get("value", "")
                    if isinstance(value, str) and len(value.strip()) > 3:
                        return value.strip()

        record_id = record.get("id", "unknown")
        return f"Documento PNT {record_id}"

    def _extract_publication_date(self, record: Dict) -> Optional[str]:
        """
        Extract publication or last-reform date from a PNT record.

        Args:
            record: Single record dict from the PNT API.

        Returns:
            Date string in the format found, or None.
        """
        date_fields = [
            "fechaPublicacion",
            "fecha_publicacion",
            "fechaUltimaModificacion",
            "fecha_ultima_modificacion",
            "fechaValidacion",
            "date",
        ]

        for field in date_fields:
            value = record.get(field)
            if value and isinstance(value, str) and len(value.strip()) >= 8:
                return value.strip()

        return None

    def _is_regulatory_document(self, title: str) -> bool:
        """
        Determine whether a document title indicates a municipal regulation.

        Args:
            title: Document title string.

        Returns:
            True if the title matches regulatory keywords.
        """
        return bool(REGULATORY_KEYWORDS.search(title))

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape the PNT SIPOT API for municipal regulatory documents.

        Iterates over all municipal subjects in the configured state (or a
        single municipality if municipality_filter is set), fetches their
        Marco Normativo obligation records, and extracts document metadata.

        Returns:
            List of law dictionaries with name, url, municipality, state,
            tier, category, and PNT-specific metadata.
        """
        subjects = self.fetch_subjects()
        if not subjects:
            return []

        # Filter to specific municipality if requested
        if self.municipality_filter:
            filter_lower = self.municipality_filter.lower()
            subjects = [
                s
                for s in subjects
                if filter_lower in s.get("name", "").lower()
                or filter_lower in s.get("nombre", "").lower()
            ]
            if not subjects:
                logger.warning(
                    "No PNT subject found matching municipality '%s' in %s",
                    self.municipality_filter,
                    self.state_key,
                )
                return []
            logger.info(
                "Filtered to %d subject(s) matching '%s'",
                len(subjects),
                self.municipality_filter,
            )

        laws: List[Dict] = []
        seen_urls: Set[str] = set()
        total_subjects = len(subjects)

        for idx, subject in enumerate(subjects, 1):
            subject_id = subject.get("id", subject.get("subjectId", ""))
            subject_name = subject.get(
                "name", subject.get("nombre", f"Subject-{subject_id}")
            )

            logger.info(
                "[%d/%d] Processing subject: %s (id=%s)",
                idx,
                total_subjects,
                subject_name,
                subject_id,
            )

            if not subject_id:
                logger.warning("Subject missing ID, skipping: %s", subject)
                continue

            records = self.fetch_all_records(str(subject_id))
            logger.info("  Found %d records for %s", len(records), subject_name)

            for record in records:
                title = self._extract_document_title(record)
                doc_url = self._extract_document_url(record)
                pub_date = self._extract_publication_date(record)

                if not doc_url:
                    logger.debug("  Skipping record without document URL: %s", title)
                    continue

                if doc_url in seen_urls:
                    continue
                seen_urls.add(doc_url)

                # Clean municipality name from PNT subject label
                municipality_name = self._clean_municipality_name(subject_name)

                law = {
                    "name": title,
                    "url": doc_url,
                    "municipality": municipality_name,
                    "state": STATE_DISPLAY_NAMES[self.state_key],
                    "tier": "municipal",
                    "category": self.extract_category(title),
                    "status": "Discovered",
                    "source": "PNT-SIPOT",
                    "pnt_subject_id": str(subject_id),
                    "pnt_record_id": str(record.get("id", "")),
                    "publication_date": pub_date,
                    "is_regulatory": self._is_regulatory_document(title),
                }

                if self.validate_law_data(law):
                    laws.append(law)

        logger.info(
            "PNT scrape complete for %s: %d documents from %d subjects",
            self.state_key,
            len(laws),
            total_subjects,
        )

        return laws

    def scrape_catalog_regulatory_only(self) -> List[Dict]:
        """
        Scrape the catalog but return only documents matching regulatory keywords.

        Convenience method that filters scrape_catalog() results to reglamentos,
        bandos, codigos, and similar documents.

        Returns:
            Filtered list of law dictionaries.
        """
        all_docs = self.scrape_catalog()
        regulatory = [d for d in all_docs if d.get("is_regulatory", False)]
        logger.info(
            "Filtered to %d regulatory documents out of %d total",
            len(regulatory),
            len(all_docs),
        )
        return regulatory

    def scrape_law_content(self, url: str) -> Optional[Dict]:
        """
        Fetch the content of a specific law document from its URL.

        Handles both PDF downloads and HTML page extraction.

        Args:
            url: URL of the law document.

        Returns:
            Dict with url, file_type, content, size_bytes; or None on failure.
        """
        if self.is_pdf(url):
            try:
                self._rate_limit()
                response = self.session.get(url, timeout=120, verify=False)
                response.raise_for_status()
                return {
                    "url": url,
                    "file_type": "pdf",
                    "content": None,
                    "size_bytes": len(response.content),
                }
            except Exception as e:
                logger.error("Error fetching PDF %s: %s", url, e)
                return None
        else:
            html = self.fetch_page(url)
            if not html:
                return None

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text_content = soup.get_text(separator="\n", strip=True)

            return {
                "url": url,
                "file_type": "html",
                "content": text_content,
                "size_bytes": len(text_content),
            }

    def download_documents(
        self,
        laws: List[Dict],
        base_output_dir: str = "data/municipal",
        regulatory_only: bool = True,
        max_downloads: int = 0,
    ) -> List[Dict]:
        """
        Download documents from a list of scraped law entries.

        Saves files to data/municipal/{state_key}/{municipality}/ with
        sanitized filenames. Writes a metadata JSON sidecar for each download.

        Args:
            laws: List of law dicts from scrape_catalog().
            base_output_dir: Root output directory.
            regulatory_only: If True, only download documents matching
                             regulatory keywords.
            max_downloads: Maximum number of files to download (0 = unlimited).

        Returns:
            List of dicts with download results (path, size, status).
        """
        results: List[Dict] = []
        download_count = 0

        for law in laws:
            if regulatory_only and not law.get("is_regulatory", False):
                continue

            if max_downloads > 0 and download_count >= max_downloads:
                logger.info("Reached download limit of %d, stopping", max_downloads)
                break

            municipality_dir = _sanitize_filename(law["municipality"])
            output_dir = Path(base_output_dir) / self.state_key / municipality_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            doc_url = law["url"]
            title = law["name"]

            logger.info("Downloading [%d]: %s", download_count + 1, title[:80])

            download_result = self.download_law_content(doc_url, str(output_dir))
            if download_result:
                # Write metadata sidecar
                meta_filename = _sanitize_filename(title) + ".meta.json"
                meta_path = output_dir / meta_filename
                metadata = {
                    "name": title,
                    "url": doc_url,
                    "municipality": law["municipality"],
                    "state": law["state"],
                    "category": law.get("category", ""),
                    "publication_date": law.get("publication_date"),
                    "source": "PNT-SIPOT",
                    "pnt_subject_id": law.get("pnt_subject_id", ""),
                    "pnt_record_id": law.get("pnt_record_id", ""),
                    "file_path": download_result.get("file_path", ""),
                    "file_type": download_result.get("file_type", ""),
                    "size_bytes": download_result.get("size_bytes", 0),
                }
                meta_path.write_text(
                    json.dumps(metadata, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                results.append(
                    {
                        "law": title,
                        "municipality": law["municipality"],
                        "file_path": download_result.get("file_path"),
                        "size_bytes": download_result.get("size_bytes", 0),
                        "status": "downloaded",
                    }
                )
                download_count += 1
            else:
                results.append(
                    {
                        "law": title,
                        "municipality": law["municipality"],
                        "file_path": None,
                        "size_bytes": 0,
                        "status": "failed",
                    }
                )

        succeeded = sum(1 for r in results if r["status"] == "downloaded")
        failed = sum(1 for r in results if r["status"] == "failed")
        logger.info(
            "Download complete: %d succeeded, %d failed out of %d attempted",
            succeeded,
            failed,
            len(results),
        )

        return results

    def save_catalog(self, laws: List[Dict], output_path: str) -> None:
        """
        Save the scraped catalog to a JSON file for later processing.

        Args:
            laws: List of law dicts from scrape_catalog().
            output_path: File path for the output JSON.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(laws, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved catalog with %d entries to %s", len(laws), output_path)

    @staticmethod
    def _clean_municipality_name(subject_name: str) -> str:
        """
        Clean a PNT subject name into a normalized municipality name.

        PNT subjects often include prefixes like "H. Ayuntamiento de" or
        "Municipio de". This strips those prefixes.

        Args:
            subject_name: Raw subject name from the PNT API.

        Returns:
            Cleaned municipality name.
        """
        prefixes_to_strip = [
            r"^H\.?\s*Ayuntamiento\s+de\s+",
            r"^Ayuntamiento\s+(Municipal\s+)?de\s+",
            r"^Municipio\s+de\s+",
            r"^Gobierno\s+Municipal\s+de\s+",
            r"^Administraci[oó]n\s+Municipal\s+de\s+",
        ]
        name = subject_name.strip()
        for pattern in prefixes_to_strip:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()
        return name

    @staticmethod
    def list_available_states() -> List[str]:
        """Return sorted list of valid state keys."""
        return sorted(INEGI_STATE_CODES.keys())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description=(
            "PNT SIPOT municipal scraper -- discover and download municipal "
            "regulations from the Plataforma Nacional de Transparencia"
        ),
    )
    parser.add_argument(
        "--state",
        required=True,
        help=(
            "State key (e.g. 'jalisco', 'nuevo_leon'). "
            f"Valid keys: {', '.join(sorted(INEGI_STATE_CODES.keys()))}"
        ),
    )
    parser.add_argument(
        "--municipality",
        default=None,
        help="Filter to a specific municipality name (substring match)",
    )
    parser.add_argument(
        "--regulatory-only",
        action="store_true",
        default=False,
        help="Only include documents matching regulatory keywords",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        default=False,
        help="Download discovered documents (PDFs) to data/municipal/",
    )
    parser.add_argument(
        "--max-downloads",
        type=int,
        default=0,
        help="Maximum number of documents to download (0 = unlimited)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/municipal",
        help="Base output directory for downloads (default: data/municipal)",
    )
    parser.add_argument(
        "--save-catalog",
        default=None,
        help="Save catalog JSON to this file path before downloading",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of results displayed (0 = all)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    scraper = PNTMunicipalScraper(
        state_key=args.state,
        municipality=args.municipality,
    )

    if args.regulatory_only:
        laws = scraper.scrape_catalog_regulatory_only()
    else:
        laws = scraper.scrape_catalog()

    print(f"\n{'=' * 70}")
    print(f"PNT SIPOT Scraper Results")
    print(f"State: {STATE_DISPLAY_NAMES.get(args.state, args.state)}")
    if args.municipality:
        print(f"Municipality filter: {args.municipality}")
    print(f"Documents discovered: {len(laws)}")

    regulatory_count = sum(1 for l in laws if l.get("is_regulatory"))
    print(f"Regulatory documents: {regulatory_count}")

    municipalities = {l["municipality"] for l in laws}
    print(f"Municipalities with data: {len(municipalities)}")
    print(f"{'=' * 70}")

    display = laws[: args.limit] if args.limit > 0 else laws
    for i, law in enumerate(display, 1):
        reg_marker = " [REG]" if law.get("is_regulatory") else ""
        print(f"\n[{i}] {law['name'][:100]}{reg_marker}")
        print(f"    Municipality: {law['municipality']}")
        print(f"    Category: {law['category']}")
        print(f"    URL: {law['url']}")
        if law.get("publication_date"):
            print(f"    Published: {law['publication_date']}")

    if args.save_catalog:
        scraper.save_catalog(laws, args.save_catalog)

    if args.download:
        print(f"\nDownloading documents to {args.output_dir}/...")
        results = scraper.download_documents(
            laws,
            base_output_dir=args.output_dir,
            regulatory_only=args.regulatory_only,
            max_downloads=args.max_downloads,
        )
        succeeded = sum(1 for r in results if r["status"] == "downloaded")
        failed = sum(1 for r in results if r["status"] == "failed")
        print(f"\nDownload complete: {succeeded} succeeded, {failed} failed")
