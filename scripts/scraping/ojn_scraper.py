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
"""

import requests
from bs4 import BeautifulSoup
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
import re
from datetime import datetime

class OJNScraper:
    """Scraper for Orden Jurídico Nacional state laws"""
    
    BASE_URL = "http://compilacion.ordenjuridico.gob.mx"
    
    # Rate limiting
    REQUEST_DELAY = 1.0  # seconds between requests
    
    def __init__(self, output_dir: str = "data/state_laws"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
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
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all law links in the table
        laws = []
        for link in soup.find_all('a', href=re.compile(r'fichaOrdenamiento2\.php')):
            href = link.get('href')
            match = re.search(r'idArchivo=(\d+)', href)
            if match:
                file_id = int(match.group(1))
                law_name = link.get_text(strip=True)
                laws.append({
                    'file_id': file_id,
                    'name': law_name,
                    'state_id': state_id,
                    'power_id': power_id
                })
        
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
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        metadata = {
            'file_id': file_id,
            'ambito': ambito,
            'url': url
        }
        
        # Extract metadata from table
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) == 2:
                key = cells[0].get_text(strip=True).rstrip(':')
                value = cells[1].get_text(strip=True)
                
                # Map Spanish field names to English keys
                field_mapping = {
                    'Fecha de publicación': 'publication_date',
                    'Poder': 'power',
                    'Ámbito': 'ambito_full',
                    'Estatus': 'status',
                    'Tipo': 'type',
                    'Localidad': 'locality'
                }
                
                if key in field_mapping:
                    metadata[field_mapping[key]] = value
        
        # Find download link
        download_link = soup.find('a', href=re.compile(r'obtenerdoc\.php'))
        if download_link:
            href = download_link.get('href')
            metadata['download_url'] = f"{self.BASE_URL}/{href}" if not href.startswith('http') else href
            
            # Determine file format from URL
            if '.doc' in href.lower():
                metadata['format'] = 'doc'
            elif '.pdf' in href.lower():
                metadata['format'] = 'pdf'
            else:
                metadata['format'] = 'unknown'
        
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
    
    def scrape_state(self, state_id: int, state_name: str, limit: Optional[int] = None) -> Dict:
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
        
        state_dir = self.output_dir / state_name.lower().replace(' ', '_')
        state_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'state_id': state_id,
            'state_name': state_name,
            'total_found': len(laws),
            'successful': 0,
            'failed': 0,
            'laws': []
        }
        
        for i, law in enumerate(laws, 1):
            print(f"\n[{i}/{len(laws)}] Processing: {law['name'][:60]}...")
            
            # Fetch metadata
            metadata = self.get_law_metadata(law['file_id'])
            if not metadata:
                print("   ❌ Failed to fetch metadata")
                results['failed'] += 1
                continue
            
            # Skip if no download URL
            if 'download_url' not in metadata:
                print("   ⚠️  No download URL found")
                results['failed'] += 1
                continue
            
            # Determine file extension
            file_format = metadata.get('format', 'pdf')
            file_ext = 'doc' if file_format == 'doc' else 'pdf'
            
            # Create safe filename
            safe_name = re.sub(r'[^\w\s-]', '', law['name'])[:100]
            safe_name = safe_name.replace(' ', '_').lower()
            file_path = state_dir / f"{safe_name}_{law['file_id']}.{file_ext}"
            
            # Download
            if self.download_document(metadata['download_url'], file_path):
                metadata['local_path'] = str(file_path)
                metadata['law_name'] = law['name']
                results['successful'] += 1
                results['laws'].append(metadata)
            else:
                results['failed'] += 1
        
        # Save metadata JSON
        metadata_file = state_dir / f"{state_name.lower()}_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*70}")
        print(f"✅ State Complete: {state_name}")
        print(f"   Success: {results['successful']}/{results['total_found']}")
        print(f"   Failed: {results['failed']}")
        print(f"   Metadata saved: {metadata_file}")
        print(f"{'='*70}")
        
        return results


def main():
    """Test scraper on single state"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape state laws from OJN')
    parser.add_argument('--state-id', type=int, default=11, help='State ID (1-32)')
    parser.add_argument('--state-name', type=str, default='Guanajuato', help='State name')
    parser.add_argument('--limit', type=int, help='Limit number of laws (for testing)')
    parser.add_argument('--output-dir', type=str, default='data/state_laws', help='Output directory')
    
    args = parser.parse_args()
    
    scraper = OJNScraper(output_dir=args.output_dir)
    results = scraper.scrape_state(args.state_id, args.state_name, limit=args.limit)
    
    print(f"\n📊 Scraping Statistics:")
    print(f"   Total found: {results['total_found']}")
    print(f"   Downloaded: {results['successful']}")
    print(f"   Failed: {results['failed']}")
    print(f"   Success rate: {results['successful']/results['total_found']*100:.1f}%")


if __name__ == "__main__":
    main()
