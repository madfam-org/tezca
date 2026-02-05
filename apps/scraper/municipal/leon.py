"""
León Municipal Scraper

Scrapes regulations from León's municipal transparency portal.
"""

from typing import List, Dict, Optional
from .base import MunicipalScraper
from .config import get_config
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class LeonScraper(MunicipalScraper):
    def __init__(self):
        config = get_config('leon')
        super().__init__(config=config)
        logger.info(f"Initialized {self.municipality} scraper - {self.base_url}")

    def scrape_catalog(self) -> List[Dict]:
        """
        Scrape León's regulations catalog.
        
        León (Guanajuato) - major industrial city.
        """
        # Try transparency path from config
        catalog_path = self.selectors.get('catalog_path', '/transparencia')
        catalog_url = self.normalize_url(catalog_path)
        
        html = self.fetch_page(catalog_url)
        if not html:
            logger.warning(f"Failed to fetch catalog from {catalog_url}, trying alternatives")
            # Try alternative paths
            alternatives = [
                '/transparencia/normatividad',
                '/normatividad',
                '/reglamentos-municipales',
                '/marco-juridico'
            ]
            for alt_path in alternatives:
                alt_url = self.normalize_url(alt_path)
                html = self.fetch_page(alt_url)
                if html:
                    catalog_url = alt_url
                    logger.info(f"Found catalog at alternative path: {alt_url}")
                    break
            
        if not html:
            logger.error(f"Could not fetch any catalog page for {self.municipality}")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        laws = []
        
        # Search for regulation links
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            text = link.get_text(strip=True)
            
            # Skip short/empty links
            if not text or len(text) < 10:
                continue
            
            if self._is_regulation_link(text, href):
                absolute_url = self.normalize_url(href, base=catalog_url)
                
                law = {
                    'name': text,
                    'url': absolute_url,
                    'municipality': self.municipality,
                    'state': self.state,
                    'tier': 'municipal',
                    'category': self.extract_category(text)
                }
                
                if self.validate_law_data(law):
                    laws.append(law)
                    logger.debug(f"Found regulation: {text}")
        
        logger.info(f"Scraped {len(laws)} regulations from {self.municipality}")
        return laws
    
    def _is_regulation_link(self, text: str, href: str) -> bool:
        """Check if link appears to be a regulation."""
        text_lower = text.lower()
        href_lower = href.lower()
        
        keywords = [
            'reglamento', 'código', 'codigo', 'bando',
            'normativ', 'ley municipal', 'marco jurídico'
        ]
        return any(keyword in text_lower or keyword in href_lower for keyword in keywords)

    def scrape_law_content(self, url: str) -> Optional[Dict]:
        """Fetch content of a specific law."""
        return {
            'url': url,
            'file_type': 'pdf' if self.is_pdf(url) else 'html'
        }
