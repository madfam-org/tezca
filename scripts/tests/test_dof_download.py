#!/usr/bin/env python3
"""
Test script for DOF API client.
Downloads Ley de Amparo and analyzes the PDF structure.
"""

import sys
import os
from pathlib import Path

# Add apps directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'apps'))

from scraper.dof_api_client import DOFAPIClient
import datetime

def test_download_amparo():
    """Test downloading Ley de Amparo from various sources."""
    
    client = DOFAPIClient()
    
    print("=" * 60)
    print("Testing DOF API Client - Ley de Amparo Download")
    print("=" * 60)
    
    # Test 1: Download from DOF (full daily edition)
    print("\n📥 Test 1: Downloading DOF daily edition (2013-04-02)...")
    publication_date = datetime.date(2013, 4, 2)
    
    dof_pdf = client.get_daily_pdf(
        date=publication_date,
        save_path=Path("data/raw/dof_2013-04-02_MAT.pdf")
    )
    
    if dof_pdf and dof_pdf.exists():
        size_mb = dof_pdf.stat().st_size / (1024 * 1024)
        print(f"✅ DOF edition downloaded: {dof_pdf}")
        print(f"   Size: {size_mb:.2f} MB")
    else:
        print("❌ Failed to download DOF edition")
    
    # Test 2: Try Chamber of Deputies
    print("\n📥 Test 2: Trying Chamber of Deputies...")
    
    # Try various possible URL patterns
    potential_urls = [
        "LAmp",  # Common abbreviation
        "Ley_de_Amparo",
        "LeyAmparo",
        "LAMPARO",
    ]
    
    chamber_pdf = None
    for slug in potential_urls:
        print(f"   Trying slug: {slug}")
        chamber_pdf = client.download_law_from_diputados(
            law_slug=slug,
            save_path=Path(f"data/raw/ley_amparo_{slug}.pdf")
        )
        
        if chamber_pdf and chamber_pdf.exists():
            size_mb = chamber_pdf.stat().st_size / (1024 * 1024)
            print(f"✅ Downloaded from Chamber: {chamber_pdf}")
            print(f"   Size: {size_mb:.2f} MB")
            break
    
    if not chamber_pdf or not chamber_pdf.exists():
        print("❌ Failed all Chamber of Deputies URL attempts")
        print("   Manual verification needed for correct URL")
    
    print("\n" + "=" * 60)
    print("Download test complete")
    print("=" * 60)
    
    # Return path to downloaded file for further analysis
    if chamber_pdf and chamber_pdf.exists():
        return chamber_pdf
    elif dof_pdf and dof_pdf.exists():
        return dof_pdf
    else:
        return None


if __name__ == "__main__":
    downloaded_file = test_download_amparo()
    
    if downloaded_file:
        print(f"\n✅ Successfully downloaded file for analysis: {downloaded_file}")
        print("\n📋 Next steps:")
        print("   1. Manually inspect the PDF")
        print("   2. Verify it's text-based (not scanned)")
        print("   3. Analyze structure for parser configuration")
    else:
        print("\n⚠️  No file downloaded. Check error messages above.")
        print("   May need to manually download from:")
        print("   https://www.diputados.gob.mx/LeyesBiblio/index.htm")
