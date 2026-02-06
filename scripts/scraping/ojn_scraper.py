#!/usr/bin/env python3
"""
OJN (Orden Jurídico Nacional) Web Scraper

Scrapes state laws from http://compilacion.ordenjuridico.gob.mx/

Features:
- Discovers all laws for each of 32 Mexican states
- Extracts metadata (publication date, status, type)
- Downloads PDFs and Word documents
- Converts .doc files to PDF for processing
- Respects rate limits (1-2 requests/second)
- Tracks individual law failures with reason codes
- Multi-power scanning (Ejecutivo, Legislativo, Judicial, Autónomos)
- Municipal-scope law discovery
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup


class OJNScraper:
    """Scraper for Orden Jurídico Nacional state laws"""

    BASE_URL = "http://compilacion.ordenjuridico.gob.mx"

    # Rate limiting
    REQUEST_DELAY = 1.0  # seconds between requests

    def __init__(self, output_dir: str = "data/state_laws"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )

    def _request(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        """Make HTTP request with rate limiting and retries"""
        for attempt in range(retries):
            try:
                time.sleep(self.REQUEST_DELAY)  # Rate limiting
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                print(f"  ⚠️  Request failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    return None
        return None

    def get_state_laws(self, state_id: int, power_id: int = 2) -> List[Dict]:
        """
        Fetch all laws for a given state and power

        Args:
            state_id: State ID (1-32)
            power_id: Power ID (1=Ejecutivo, 2=Legislativo, 3=Judicial, 4=Autónomos)

        Returns:
            List of law dictionaries with metadata
        """
        url = f"{self.BASE_URL}/listPoder2.php?edo={state_id}&idPoder={power_id}"
        print(f"\n📥 Fetching laws for state {state_id}, power {power_id}")
        print(f"   URL: {url}")

        response = self._request(url)
        if not response:
            print("   ❌ Failed to fetch law list")
            return []

        soup = BeautifulSoup(response.content, "html.parser")

        # Find all law links in the table
        laws = []
        for link in soup.find_all("a", href=re.compile(r"fichaOrdenamiento2\.php")):
            href = link.get("href")
            match = re.search(r"idArchivo=(\d+)", href)
            if match:
                file_id = int(match.group(1))
                law_name = link.get_text(strip=True)
                laws.append(
                    {
                        "file_id": file_id,
                        "name": law_name,
                        "state_id": state_id,
                        "power_id": power_id,
                    }
                )

        print(f"   ✅ Found {len(laws)} laws")
        return laws

    def get_law_metadata(self, file_id: int, ambito: str = "ESTATAL") -> Optional[Dict]:
        """
        Fetch detailed metadata for a specific law

        Args:
            file_id: Law file ID
            ambito: Scope (ESTATAL or MUNICIPAL)

        Returns:
            Dictionary with law metadata
        """
        url = f"{self.BASE_URL}/fichaOrdenamiento2.php?idArchivo={file_id}&ambito={ambito}"

        response = self._request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        metadata = {"file_id": file_id, "ambito": ambito, "url": url}

        # Extract metadata from table
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) == 2:
                key = cells[0].get_text(strip=True).rstrip(":")
                value = cells[1].get_text(strip=True)

                # Map Spanish field names to English keys
                field_mapping = {
                    "Fecha de publicación": "publication_date",
                    "Poder": "power",
                    "Ámbito": "ambito_full",
                    "Estatus": "status",
                    "Tipo": "type",
                    "Localidad": "locality",
                }

                if key in field_mapping:
                    metadata[field_mapping[key]] = value

        # Find download link
        download_link = soup.find("a", href=re.compile(r"obtenerdoc\.php"))
        if download_link:
            href = download_link.get("href")
            metadata["download_url"] = (
                f"{self.BASE_URL}/{href}" if not href.startswith("http") else href
            )

            # Determine file format from URL
            if ".doc" in href.lower():
                metadata["format"] = "doc"
            elif ".pdf" in href.lower():
                metadata["format"] = "pdf"
            else:
                metadata["format"] = "unknown"

        return metadata

    def download_document(self, download_url: str, output_path: Path) -> bool:
        """
        Download law document (PDF or Word)

        Args:
            download_url: URL to download
            output_path: Where to save the file

        Returns:
            True if successful, False otherwise
        """
        # Skip if file already exists and is valid (>1KB)
        if output_path.exists() and output_path.stat().st_size > 1024:
            print(f"   ⏭️  Already downloaded: {output_path.name}")
            return True

        print(f"   📥 Downloading: {output_path.name}")

        response = self._request(download_url)
        if not response:
            print(f"   ❌ Download failed")
            return False

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            print(f"   ✅ Saved: {output_path}")
            return True
        except Exception as e:
            print(f"   ❌ Save failed: {e}")
            return False

    def _make_failure_record(self, law, reason, metadata=None):
        """Create a standardized failure record for a law."""
        return {
            "file_id": law["file_id"],
            "law_name": law["name"],
            "failure_reason": reason,
            "download_url": (metadata.get("download_url", "") if metadata else ""),
            "timestamp": datetime.now().isoformat(),
        }

    def _download_law(self, law, state_dir, results):
        """
        Process a single law: fetch metadata, download document, update results.

        Shared logic for scrape_state() and scrape_state_comprehensive().
        """
        # Check if already downloaded (any extension) — skip metadata fetch too
        safe_name = re.sub(r"[^\w\s-]", "", law["name"])[:100]
        safe_name = safe_name.replace(" ", "_").lower()
        existing = list(state_dir.glob(f"{safe_name}_{law['file_id']}.*"))
        if existing and existing[0].stat().st_size > 1024:
            print(f"   ⏭️  Already exists: {existing[0].name}")
            results["successful"] += 1
            results["laws"].append(
                {
                    "file_id": law["file_id"],
                    "law_name": law["name"],
                    "local_path": str(existing[0]),
                    "skipped": True,
                }
            )
            return

        metadata = self.get_law_metadata(law["file_id"])
        if not metadata:
            print("   ❌ Failed to fetch metadata")
            results["failed"] += 1
            results["failed_laws"].append(self._make_failure_record(law, "no_metadata"))
            return

        if "download_url" not in metadata:
            print("   ⚠️  No download URL found")
            results["failed"] += 1
            results["failed_laws"].append(
                self._make_failure_record(law, "no_download_url", metadata)
            )
            return

        # Determine file extension
        file_format = metadata.get("format", "pdf")
        file_ext = "doc" if file_format == "doc" else "pdf"

        # Create safe filename
        safe_name = re.sub(r"[^\w\s-]", "", law["name"])[:100]
        safe_name = safe_name.replace(" ", "_").lower()
        file_path = state_dir / f"{safe_name}_{law['file_id']}.{file_ext}"

        if self.download_document(metadata["download_url"], file_path):
            metadata["local_path"] = str(file_path)
            metadata["law_name"] = law["name"]
            results["successful"] += 1
            results["laws"].append(metadata)
        else:
            results["failed"] += 1
            results["failed_laws"].append(
                self._make_failure_record(law, "download_failed", metadata)
            )

    def scrape_state(
        self, state_id: int, state_name: str, limit: Optional[int] = None
    ) -> Dict:
        """
        Scrape all laws for a single state

        Args:
            state_id: State ID (1-32)
            state_name: State name for organizing files
            limit: Optional limit on number of laws to scrape (for testing)

        Returns:
            Summary dictionary with statistics
        """
        print(f"\n{'='*70}")
        print(f"🏛️  Scraping State: {state_name} (ID: {state_id})")
        print(f"{'='*70}")

        # Get legislative laws (power_id=2)
        laws = self.get_state_laws(state_id, power_id=2)

        if limit:
            laws = laws[:limit]
            print(f"   ⚠️  Limited to {limit} laws for testing")

        state_dir = self.output_dir / state_name.lower().replace(" ", "_")
        state_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "state_id": state_id,
            "state_name": state_name,
            "total_found": len(laws),
            "successful": 0,
            "failed": 0,
            "laws": [],
            "failed_laws": [],
        }

        for i, law in enumerate(laws, 1):
            print(f"\n[{i}/{len(laws)}] Processing: {law['name'][:60]}...")
            self._download_law(law, state_dir, results)

        # Save metadata JSON
        metadata_file = state_dir / f"{state_name.lower()}_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*70}")
        print(f"✅ State Complete: {state_name}")
        print(f"   Success: {results['successful']}/{results['total_found']}")
        print(f"   Failed: {results['failed']}")
        if results["failed_laws"]:
            print(f"   Failure details: {len(results['failed_laws'])} records")
        print(f"   Metadata saved: {metadata_file}")
        print(f"{'='*70}")

        return results

    def scrape_state_comprehensive(
        self,
        state_id: int,
        state_name: str,
        power_ids: Optional[List[int]] = None,
        limit: Optional[int] = None,
    ) -> Dict:
        """
        Scrape laws for a state across multiple powers (comprehensive).

        Queries all power_ids and deduplicates by file_id before downloading.

        Args:
            state_id: State ID (1-32)
            state_name: State name for organizing files
            power_ids: List of power IDs to query (default: [1, 2, 3, 4])
            limit: Optional limit on total laws to scrape

        Returns:
            Summary dictionary with statistics
        """
        if power_ids is None:
            power_ids = [1, 2, 3, 4]

        print(f"\n{'='*70}")
        print(f"🏛️  Comprehensive Scraping: {state_name} (ID: {state_id})")
        print(f"   Powers: {power_ids}")
        print(f"{'='*70}")

        # Collect laws from all powers, deduplicate by file_id
        seen_file_ids = set()
        all_laws = []

        for power_id in power_ids:
            laws = self.get_state_laws(state_id, power_id=power_id)
            for law in laws:
                if law["file_id"] not in seen_file_ids:
                    seen_file_ids.add(law["file_id"])
                    all_laws.append(law)

        print(f"\n   📊 Total unique laws across all powers: {len(all_laws)}")

        if limit:
            all_laws = all_laws[:limit]
            print(f"   ⚠️  Limited to {limit} laws for testing")

        state_dir = self.output_dir / state_name.lower().replace(" ", "_")
        state_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "state_id": state_id,
            "state_name": state_name,
            "power_ids_queried": power_ids,
            "total_found": len(all_laws),
            "successful": 0,
            "failed": 0,
            "laws": [],
            "failed_laws": [],
        }

        for i, law in enumerate(all_laws, 1):
            print(f"\n[{i}/{len(all_laws)}] Processing: {law['name'][:60]}...")
            self._download_law(law, state_dir, results)

        # Save metadata JSON
        metadata_file = state_dir / f"{state_name.lower()}_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*70}")
        print(f"✅ Comprehensive Scrape Complete: {state_name}")
        print(f"   Success: {results['successful']}/{results['total_found']}")
        print(f"   Failed: {results['failed']}")
        if results["failed_laws"]:
            print(f"   Failure details: {len(results['failed_laws'])} records")
        print(f"   Metadata saved: {metadata_file}")
        print(f"{'='*70}")

        return results

    def scrape_municipal_laws(
        self,
        state_id: int,
        state_name: str,
        power_ids: Optional[List[int]] = None,
        limit: Optional[int] = None,
    ) -> Dict:
        """
        Scrape municipal-scope laws for a state from OJN.

        Uses ambito="MUNICIPAL" when fetching law metadata.

        Args:
            state_id: State ID (1-32)
            state_name: State name for organizing files
            power_ids: List of power IDs to query (default: [1, 2, 3, 4])
            limit: Optional limit on total laws to scrape

        Returns:
            Summary dictionary with statistics
        """
        if power_ids is None:
            power_ids = [1, 2, 3, 4]

        print(f"\n{'='*70}")
        print(f"🏘️  Municipal Scraping: {state_name} (ID: {state_id})")
        print(f"   Powers: {power_ids}")
        print(f"{'='*70}")

        # Collect laws from all powers, deduplicate by file_id
        seen_file_ids = set()
        all_laws = []

        for power_id in power_ids:
            laws = self.get_state_laws(state_id, power_id=power_id)
            for law in laws:
                if law["file_id"] not in seen_file_ids:
                    seen_file_ids.add(law["file_id"])
                    all_laws.append(law)

        print(f"\n   📊 Total unique laws to probe: {len(all_laws)}")

        if limit:
            all_laws = all_laws[:limit]
            print(f"   ⚠️  Limited to {limit} laws for testing")

        # Output to municipal directory
        municipal_dir = Path(
            str(self.output_dir).replace("state_laws", "municipal_laws")
        )
        state_dir = municipal_dir / state_name.lower().replace(" ", "_")
        state_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "state_id": state_id,
            "state_name": state_name,
            "tier": "municipal",
            "power_ids_queried": power_ids,
            "total_found": len(all_laws),
            "successful": 0,
            "failed": 0,
            "laws": [],
            "failed_laws": [],
        }

        for i, law in enumerate(all_laws, 1):
            print(f"\n[{i}/{len(all_laws)}] Processing: {law['name'][:60]}...")

            # Check if already downloaded (any extension) — skip metadata fetch too
            safe_name = re.sub(r"[^\w\s-]", "", law["name"])[:100]
            safe_name = safe_name.replace(" ", "_").lower()
            existing = list(state_dir.glob(f"{safe_name}_{law['file_id']}.*"))
            if existing and existing[0].stat().st_size > 1024:
                print(f"   ⏭️  Already exists: {existing[0].name}")
                results["successful"] += 1
                results["laws"].append(
                    {
                        "file_id": law["file_id"],
                        "law_name": law["name"],
                        "local_path": str(existing[0]),
                        "skipped": True,
                    }
                )
                continue

            # Use MUNICIPAL ambito for metadata
            metadata = self.get_law_metadata(law["file_id"], ambito="MUNICIPAL")
            if not metadata:
                print("   ❌ Failed to fetch metadata")
                results["failed"] += 1
                results["failed_laws"].append(
                    self._make_failure_record(law, "no_metadata")
                )
                continue

            if "download_url" not in metadata:
                print("   ⚠️  No download URL found")
                results["failed"] += 1
                results["failed_laws"].append(
                    self._make_failure_record(law, "no_download_url", metadata)
                )
                continue

            # Determine file extension
            file_format = metadata.get("format", "pdf")
            file_ext = "doc" if file_format == "doc" else "pdf"

            # Create safe filename
            safe_name = re.sub(r"[^\w\s-]", "", law["name"])[:100]
            safe_name = safe_name.replace(" ", "_").lower()
            file_path = state_dir / f"{safe_name}_{law['file_id']}.{file_ext}"

            if self.download_document(metadata["download_url"], file_path):
                metadata["local_path"] = str(file_path)
                metadata["law_name"] = law["name"]
                results["successful"] += 1
                results["laws"].append(metadata)
            else:
                results["failed"] += 1
                results["failed_laws"].append(
                    self._make_failure_record(law, "download_failed", metadata)
                )

        # Save metadata JSON
        metadata_file = (
            state_dir
            / f"{state_name.lower().replace(' ', '_')}_municipal_metadata.json"
        )
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*70}")
        print(f"✅ Municipal Scrape Complete: {state_name}")
        print(f"   Success: {results['successful']}/{results['total_found']}")
        print(f"   Failed: {results['failed']}")
        if results["failed_laws"]:
            print(f"   Failure details: {len(results['failed_laws'])} records")
        print(f"   Metadata saved: {metadata_file}")
        print(f"{'='*70}")

        return results


def main():
    """Test scraper on single state"""
    import argparse

    parser = argparse.ArgumentParser(description="Scrape state laws from OJN")
    parser.add_argument("--state-id", type=int, default=11, help="State ID (1-32)")
    parser.add_argument(
        "--state-name", type=str, default="Guanajuato", help="State name"
    )
    parser.add_argument("--limit", type=int, help="Limit number of laws (for testing)")
    parser.add_argument(
        "--output-dir", type=str, default="data/state_laws", help="Output directory"
    )
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Scan all powers (not just Legislativo)",
    )
    parser.add_argument(
        "--municipal",
        action="store_true",
        help="Scrape municipal-scope laws",
    )

    args = parser.parse_args()

    scraper = OJNScraper(output_dir=args.output_dir)

    if args.municipal:
        results = scraper.scrape_municipal_laws(
            args.state_id, args.state_name, limit=args.limit
        )
    elif args.comprehensive:
        results = scraper.scrape_state_comprehensive(
            args.state_id, args.state_name, limit=args.limit
        )
    else:
        results = scraper.scrape_state(args.state_id, args.state_name, limit=args.limit)

    print(f"\n📊 Scraping Statistics:")
    print(f"   Total found: {results['total_found']}")
    print(f"   Downloaded: {results['successful']}")
    print(f"   Failed: {results['failed']}")
    if results["total_found"] > 0:
        print(
            f"   Success rate: {results['successful']/results['total_found']*100:.1f}%"
        )
    if results.get("failed_laws"):
        print(f"   Failure records: {len(results['failed_laws'])}")


if __name__ == "__main__":
    main()
