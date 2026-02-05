"""
DOF API Client for downloading Mexican federal laws.

This module provides a client for interacting with the Diario Oficial
de la Federación (DOF) API to download legal documents.
"""

import datetime
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DOFAPIClient:
    """
    Client for interacting with DOF Open Data API.
    
    Documentation: https://www.dof.gob.mx/datos_abiertos.php
    """
    
    BASE_URL = "http://diariooficial.gob.mx"
    CHAMBER_DEPUTIES_URL = "https://www.diputados.gob.mx"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LeyesComoCodigo/1.0 (+https://github.com/madfam-org/leyes-como-codigo-mx)'
        })
    
    def get_daily_pdf(
        self, 
        date: datetime.date, 
        edition: str = "MAT",
        save_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Download the complete daily DOF edition PDF.
        
        Args:
            date: Publication date
            edition: Edition type ("MAT", "VES", or "EXT")
            save_path: Where to save the PDF
            
        Returns:
            Path to downloaded PDF, or None if failed
        """
        url = (
            f"{self.BASE_URL}/WS_getDiarioPDF.php"
            f"?day={date.day:02d}"
            f"&month={date.month:02d}"
            f"&year={date.year}"
            f"&edicion={edition}"
        )
        
        logger.info(f"Fetching DOF PDF for {date} ({edition} edition)")
        logger.debug(f"URL: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            if save_path is None:
                save_path = Path(f"dof_{date.isoformat()}_{edition}.pdf")
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(response.content)
            
            file_size = len(response.content)
            logger.info(f"Downloaded {file_size:,} bytes to {save_path}")
            
            return save_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to download DOF PDF: {e}")
            return None
    
    def download_law_from_diputados(
        self,
        law_slug: str,
        save_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Download law from Chamber of Deputies website.
        
        The Chamber maintains official texts of all federal laws,
        often with better formatting than raw DOF PDFs.
        
        Args:
            law_slug: Law identifier (e.g., "Ley_de_Amparo")
            save_path: Where to save the downloaded file
            
        Returns:
            Path to downloaded file, or None if failed
        """
        # Note: This is a placeholder. The actual URL structure needs
        # to be determined from the Chamber of Deputies website.
        
        url = f"{self.CHAMBER_DEPUTIES_URL}/LeyesBiblio/pdf/{law_slug}.pdf"
        logger.info(f"Attempting to download {law_slug} from Chamber of Deputies")
        logger.debug(f"URL: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            if save_path is None:
                save_path = Path(f"{law_slug}.pdf")
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(response.content)
            
            file_size = len(response.content)
            logger.info(f"Downloaded {file_size:,} bytes to {save_path}")
            
            return save_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to download from Chamber: {e}")
            return None


def main():
    """Example usage: Download Ley de Amparo"""
    client = DOFAPIClient()
    
    # Option 1: Download from DOF for the publication date (April 2, 2013)
    publication_date = datetime.date(2013, 4, 2)
    dof_pdf = client.get_daily_pdf(
        date=publication_date,
        save_path=Path("data/raw/dof_2013-04-02.pdf")
    )
    
    if dof_pdf:
        print(f"✅ DOF edition downloaded: {dof_pdf}")
    
    # Option 2: Download directly from Chamber of Deputies
    # Note: Exact slug needs verification
    chamber_pdf = client.download_law_from_diputados(
        law_slug="Ley_de_Amparo",
        save_path=Path("data/raw/ley_de_amparo.pdf")
    )
    
    if chamber_pdf:
        print(f"✅ Law downloaded from Chamber: {chamber_pdf}")


if __name__ == "__main__":
    main()
