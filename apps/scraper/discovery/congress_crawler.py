import csv
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from apps.scraper.http import government_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CongressCrawler:
    def __init__(self, state_name: str, base_url: str):
        self.state_name = state_name
        self.base_url = base_url
        self.session = government_session(base_url)

    def fetch_page(self, url: str) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def find_municipal_links(self) -> List[Dict]:
        """
        Generic crawler that looks for PDF links containing 'municipal' or 'ingreso'.
        Subclasses should override this for state-specific DOM traversal.
        """
        html = self.fetch_page(self.base_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        links = []

        # Generic heuristic: Find links with 'municip' or 'ingreso' in text or href
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True).lower()
            href_lower = href.lower()

            # Heuristics for municipal revenue laws or codes
            is_relevant = (
                ("municip" in text or "municip" in href_lower)
                and (
                    "ingreso" in text
                    or "bando" in text
                    or "hacienda" in text
                    or "ley" in text
                )
                and (".pdf" in href_lower)
            )

            if is_relevant:
                full_url = urljoin(self.base_url, href)
                links.append(
                    {
                        "State": self.state_name,
                        "Municipality": "Unknown",  # Needs parsing from text
                        "Source_Type": "State_Congress_Scraping",
                        "URL": full_url,
                        "Status": "Discovered",
                        "Notes": f"Found via crawler: {text[:50]}...",
                    }
                )

        return links


def crawl_congresses(csv_path: str):
    new_sources = []

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Source_Type"] == "Aggregator" and row["Status"] != "Check_Failed":
                logger.info(f"Crawling {row['State']} Congress: {row['URL']}")
                crawler = CongressCrawler(row["State"], row["URL"])
                links = crawler.find_municipal_links()
                logger.info(f"Found {len(links)} links for {row['State']}")
                new_sources.extend(links)

    # Append new sources
    if new_sources:
        with open(csv_path, "a") as f:
            writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
            writer.writerows(new_sources)
        print(f"Added {len(new_sources)} discovered municipal links to registry.")


if __name__ == "__main__":
    CSV_PATH = "docs/MUNICIPAL_SOURCES.csv"
    crawl_congresses(CSV_PATH)
