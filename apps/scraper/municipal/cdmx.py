import os
import re
import urllib.parse
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .base import MunicipalScraper
from .config import get_config


class CDMXScraper(MunicipalScraper):
    def __init__(self):
        config = get_config("cdmx")
        super().__init__(config=config)
        self.base_domain = "https://data.consejeria.cdmx.gob.mx"
        # Disable SSL verification for this legacy site
        self.session.verify = False

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrapes the CDMX laws portal for PDF links.
        Returns a list of dictionaries with metadata.
        """
        html = self.fetch_page(self.base_url + self.selectors.get("catalog_path", ""))
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        laws = []

        # Find all PDF links
        pdf_links = soup.find_all(
            "a", href=lambda href: href and href.lower().endswith(".pdf")
        )

        for a in pdf_links:
            href = a["href"]
            # Resolve relative URL
            full_url = urllib.parse.urljoin(self.base_domain, href)

            # Extract Title from Preceding Anchor (Hash Link)
            # The structure is typically: <a href="#slug">Title</a> ... <a href="file.docx">Icon</a> ... <a href="file.pdf">Icon</a>
            title = None
            # Search backwards for the title anchor
            for prev_anchor in a.find_all_previous("a", href=True):
                # Stop if we hit a '#' link (likely the title)
                if "#" in prev_anchor["href"]:
                    title_text = prev_anchor.get_text(separator=" ", strip=True)
                    if len(title_text) > 10:
                        title = title_text
                    break
                # Stop if we went too far (e.g. hit another PDF or a different law block)
                # Heuristic: if we hit 5 links back without finding #, give up
                # Or if we hit another PDF, maybe we crossed into another law? (Actually multiple formats are common)

            # Fallback: Parse Filename if no title found

            # Fallback: Parse Filename if no title found
            if not title:
                filename = os.path.basename(urllib.parse.unquote(full_url))
                name_body = os.path.splitext(filename)[0]
                title = name_body.replace("_", " ").replace("-", " ")

            # Clean up title
            if title:
                title = re.sub(r"\s+", " ", title).strip()

            law_entry = {
                "name": title,
                "municipality": self.municipality,
                "url": full_url,
                "status": "Discovered",
                "category": "Municipal",  # or State for CDMX
            }
            laws.append(law_entry)

        return laws


if __name__ == "__main__":
    # Test execution
    scraper = CDMXScraper()
    results = scraper.scrape_catalog()
    print(f"Found {len(results)} laws.")
    for l in results[:5]:
        print(l)
