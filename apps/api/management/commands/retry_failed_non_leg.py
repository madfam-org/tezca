"""
Management command to retry failed non-legislative state law downloads.

Reads state_laws_non_legislative_metadata.json, cross-references with existing
Law records, and retries downloads for gaps using enhanced timeout/retry logic.

Usage:
    # Report retryable gaps (dry run)
    python manage.py retry_failed_non_leg --dry-run

    # Retry all failed downloads
    python manage.py retry_failed_non_leg --all

    # Retry specific state
    python manage.py retry_failed_non_leg --state michoacan

    # With batch control
    python manage.py retry_failed_non_leg --all --batch-size 50
"""

import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from apps.api.models import Law, LawVersion
from apps.api.utils.paths import data_exists, read_metadata_json

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# OJN hostnames requiring extended timeouts
_OJN_HOSTS = {"compilacion.ordenjuridico.gob.mx", "ordenjuridico.gob.mx"}
_OJN_TIMEOUT = 120
_OJN_MAX_RETRIES = 5
_DEFAULT_TIMEOUT = 60


def _build_session(url: str) -> tuple:
    """Build a requests session with retry strategy tuned for the URL's host."""
    hostname = urlparse(url).hostname or ""
    is_ojn = hostname in _OJN_HOSTS

    timeout = _OJN_TIMEOUT if is_ojn else _DEFAULT_TIMEOUT
    max_retries = _OJN_MAX_RETRIES if is_ojn else 3
    backoff = 2 if is_ojn else 1

    session = requests.Session()
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
    session.mount("http://", HTTPAdapter(max_retries=retry_strategy))
    return session, timeout, is_ojn


class Command(BaseCommand):
    help = (
        "Retry failed non-legislative state law downloads with enhanced timeout/retry"
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--all", action="store_true", help="Retry all failed downloads"
        )
        group.add_argument("--state", type=str, help="Retry specific state")

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report retryable gaps without downloading",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Batch size for transactions (default: 50)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of laws to retry",
        )
        parser.add_argument(
            "--rate-limit",
            type=float,
            default=1.0,
            help="Minimum seconds between requests (default: 1.0)",
        )

    def _identify_gaps(self, all_laws, state_filter=None):
        """Find laws in metadata that don't have successful text files."""
        gaps = []
        for law in all_laws:
            if state_filter:
                law_state = law.get("state", "").lower().replace(" ", "_")
                if law_state != state_filter.lower().replace(" ", "_"):
                    continue

            official_id = law.get("official_id", "")
            text_file = law.get("text_file", "")
            url = law.get("url", "")

            if not url:
                continue

            # Check if text file exists (local or R2)
            has_text = bool(text_file) and data_exists(text_file)

            # Check if already in DB
            in_db = (
                Law.objects.filter(official_id=official_id).exists()
                if official_id
                else False
            )

            if not has_text:
                gaps.append(
                    {
                        "official_id": official_id,
                        "law_name": law.get("law_name", "Unknown"),
                        "state": law.get("state", "Unknown"),
                        "url": url,
                        "text_file": text_file,
                        "in_db": in_db,
                        "metadata": law,
                    }
                )

        return gaps

    def _download_and_extract(self, url, output_dir, law_id):
        """Download file and extract text with enhanced retry logic."""
        session, timeout, is_ojn = _build_session(url)

        url_path = urlparse(url).path.lower()
        if url_path.endswith(".docx"):
            ext = ".docx"
        elif url_path.endswith(".doc"):
            ext = ".doc"
        else:
            ext = ".pdf"

        raw_path = output_dir / f"{law_id}{ext}"

        response = session.get(url, timeout=timeout, verify=not is_ojn)
        response.raise_for_status()
        raw_path.write_bytes(response.content)

        # Extract text based on file type
        text = ""
        if ext == ".docx":
            text = self._extract_docx(raw_path)
        elif ext == ".doc":
            text = self._extract_doc(raw_path)
        else:
            text = self._extract_pdf(raw_path)

        if not text.strip():
            return None, raw_path

        # Save extracted text
        text_path = output_dir / f"{law_id}_extracted.txt"
        text_path.write_text(text, encoding="utf-8")
        return text_path, raw_path

    def _extract_pdf(self, path):
        try:
            import pdfplumber

            parts = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        parts.append(t)
            return "\n".join(parts)
        except Exception:
            return ""

    def _extract_docx(self, path):
        try:
            import docx

            doc = docx.Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            return ""

    def _extract_doc(self, path):
        import subprocess

        try:
            result = subprocess.run(
                ["antiword", str(path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return ""

    def handle(self, *args, **options):
        self.stdout.write("Loading non-legislative metadata...")
        metadata = read_metadata_json("state_laws_non_legislative_metadata.json")

        if not metadata:
            self.stdout.write(self.style.ERROR("Metadata file not found!"))
            return

        all_laws = metadata.get("laws", [])
        state_filter = options.get("state")

        if state_filter:
            state_name = state_filter.replace("_", " ").title()
        else:
            state_name = "all states"

        gaps = self._identify_gaps(all_laws, state_filter)

        if options["limit"]:
            gaps = gaps[: options["limit"]]

        self.stdout.write("=" * 70)
        self.stdout.write("NON-LEGISLATIVE RETRY ANALYSIS")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Scope: {state_name}")
        self.stdout.write(f"Total laws in metadata: {len(all_laws):,}")
        self.stdout.write(f"Retryable gaps found: {len(gaps):,}")
        self.stdout.write(f"Dry run: {options['dry_run']}")
        self.stdout.write("=" * 70)

        if not gaps:
            self.stdout.write(self.style.SUCCESS("No gaps found!"))
            return

        # State breakdown
        state_counts = {}
        for gap in gaps:
            s = gap["state"]
            state_counts[s] = state_counts.get(s, 0) + 1

        self.stdout.write("\nGaps by state:")
        for s, count in sorted(state_counts.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {s:30} {count:5,}")

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDry run complete. {len(gaps):,} laws can be retried."
                )
            )
            return

        # Execute retries
        self.stdout.write("\nStarting retry downloads...\n")

        output_dir = DATA_DIR / "raw"
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {"downloaded": 0, "extracted": 0, "ingested": 0, "failed": 0}
        failed_laws = []
        rate_limit = options["rate_limit"]

        for i, gap in enumerate(gaps, 1):
            url = gap["url"]
            official_id = gap["official_id"]
            law_name = gap["law_name"]

            self.stdout.write(
                f"  [{i}/{len(gaps)}] {law_name[:60]}... ",
                ending="",
            )

            try:
                text_path, raw_path = self._download_and_extract(
                    url, output_dir, official_id
                )

                if text_path is None:
                    self.stdout.write(self.style.WARNING("empty text"))
                    results["failed"] += 1
                    failed_laws.append(
                        {"official_id": official_id, "error": "Empty text extraction"}
                    )
                    continue

                results["downloaded"] += 1
                results["extracted"] += 1

                # Update metadata with new text_file path
                rel_text = str(text_path.relative_to(DATA_DIR))
                gap["metadata"]["text_file"] = rel_text

                # Ingest to DB in batches
                if i % options["batch_size"] == 0 or i == len(gaps):
                    self.stdout.write(self.style.SUCCESS("ok"))
                    self.stdout.write(
                        f"    Progress: {results['downloaded']}/{i} downloaded, "
                        f"{results['failed']} failed"
                    )
                else:
                    self.stdout.write(self.style.SUCCESS("ok"))

            except requests.exceptions.RequestException as e:
                results["failed"] += 1
                error_msg = str(e)[:100]
                self.stdout.write(self.style.ERROR(f"FAIL: {error_msg}"))
                failed_laws.append({"official_id": official_id, "error": error_msg})
            except Exception as e:
                results["failed"] += 1
                self.stdout.write(self.style.ERROR(f"ERROR: {e}"))
                failed_laws.append({"official_id": official_id, "error": str(e)[:100]})

            # Rate limiting
            if rate_limit > 0:
                time.sleep(rate_limit)

        # Summary
        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("RETRY SUMMARY")
        self.stdout.write("=" * 70)
        self.stdout.write(f"Attempted:  {len(gaps):,}")
        self.stdout.write(f"Downloaded: {results['downloaded']:,}")
        self.stdout.write(f"Extracted:  {results['extracted']:,}")
        self.stdout.write(f"Failed:     {results['failed']:,}")

        if failed_laws and len(failed_laws) <= 20:
            self.stdout.write(f"\nFailed laws ({len(failed_laws)}):")
            for fl in failed_laws[:20]:
                self.stdout.write(f"  - {fl['official_id']}: {fl['error']}")
        elif failed_laws:
            self.stdout.write(f"\n{len(failed_laws)} laws failed (showing first 10):")
            for fl in failed_laws[:10]:
                self.stdout.write(f"  - {fl['official_id']}: {fl['error']}")

        self.stdout.write("=" * 70)

        if results["downloaded"] > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nRecovered {results['downloaded']:,} laws! "
                    f"Run ingest_non_legislative_laws --all to ingest them."
                )
            )
