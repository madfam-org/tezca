#!/usr/bin/env python3
"""
PDF analysis script for Ley de Amparo.
Extracts text and analyzes structure to prepare for Akoma Ntoso conversion.
"""

import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("❌ pdfplumber not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
    import pdfplumber

def analyze_pdf_structure(pdf_path: Path):
    """Analyze PDF structure and extract sample content."""
    
    print("=" * 70)
    print(f"Analyzing PDF: {pdf_path.name}")
    print("=" * 70)
    
    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
        print(f"\n📄 Total pages: {num_pages}")
        
        # Extract text from first 3 pages to see structure
        print("\n📋 Sample content from first 3 pages:")
        print("-" * 70)
        
        for i in range(min(3, num_pages)):
            page = pdf.pages[i]
            text = page.extract_text()
            
            print(f"\n--- Page {i+1} ---")
            # Show first 50 lines
            lines = text.split('\n')[:50]
            for line in lines:
                print(line)
        
        # Analyze structure patterns
        print("\n" * 2)
        print("=" * 70)
        print("STRUCTURE ANALYSIS")
        print("=" * 70)
        
        # Collect all text to analyze patterns
        all_text = ""
        for page in pdf.pages[:10]:  # Analyze first 10 pages
            all_text += page.extract_text() + "\n"
        
        # Look for structural markers
        markers = {
            "TÍTULO": all_text.count("TÍTULO"),
            "CAPÍTULO": all_text.count("CAPÍTULO"),
            "Artículo": all_text.count("Artículo"),
            "Artículo 1": "Artículo 1" in all_text,
            "TRANSITORIOS": "TRANSITORIOS" in all_text,
            "DOF": all_text.count("DOF"),
        }
        
        print("\n🔍 Structural markers found:")
        for marker, count in markers.items():
            if isinstance(count, bool):
                print(f"   {marker}: {'✅ Found' if count else '❌ Not found'}")
            else:
                print(f"   {marker}: {count} occurrences")
        
        # Check if text-based or scanned
        first_page_text = pdf.pages[0].extract_text()
        is_text_based = len(first_page_text.strip()) > 100
        
        print(f"\n📝 PDF Type: {'✅ Text-based (good!)' if is_text_based else '⚠️  Possibly scanned (OCR needed)'}")
        
        return {
            "pages": num_pages,
            "is_text_based": is_text_based,
            "markers": markers,
            "sample_text": all_text[:2000]
        }


def extract_articles(pdf_path: Path, output_path: Path):
    """Extract full text organized by articles."""
    
    print("\n" + "=" * 70)
    print("EXTRACTING FULL TEXT")
    print("=" * 70)
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for i, page in enumerate(pdf.pages):
            print(f"Processing page {i+1}/{len(pdf.pages)}...", end="\r")
            full_text += page.extract_text() + "\n\n"
        
        print(f"\n✅ Extracted {len(full_text):,} characters")
        
        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_text, encoding='utf-8')
        
        print(f"💾 Saved to: {output_path}")
        
        return full_text


if __name__ == "__main__":
    pdf_file = Path("data/raw/ley_amparo_LAmp.pdf")
    
    if not pdf_file.exists():
        print(f"❌ PDF not found: {pdf_file}")
        print("   Run test_dof_download.py first")
        sys.exit(1)
    
    # Analyze structure
    analysis = analyze_pdf_structure(pdf_file)
    
    # Extract full text
    output_txt = Path("data/raw/ley_amparo_extracted.txt")
    full_text = extract_articles(pdf_file, output_txt)
    
    # Summary
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"✅ PDF is text-based: {analysis['is_text_based']}")
    print(f"✅ Total pages: {analysis['pages']}")
    print(f"✅ Articles found: {analysis['markers'].get('Artículo', 0)}")
    print(f"✅ Full text extracted to: {output_txt}")
    print("\n📋 Next step: Build Akoma Ntoso parser based on structure")
