#!/usr/bin/env python3
"""
Quick test: Ingest IVA (VAT Law) to validate parser diversity.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'apps'))

from scraper.dof_api_client import DOFAPIClient
from parsers.akn_generator import AkomaNtosoGenerator
import datetime

def ingest_iva():
    """Ingest Ley del IVA as second test case."""
    
    print("=" * 70)
    print("INGESTING: Ley del Impuesto al Valor Agregado (IVA)")
    print("=" * 70)
    
    client = DOFAPIClient()
    
    # Try common slugs for IVA
    slugs_to_try = ["LIVA", "IVA", "Ley_IVA"]
    
    pdf_path = None
    for slug in slugs_to_try:
        print(f"\n📥 Trying slug: {slug}")
        pdf = client.download_law_from_diputados(
            law_slug=slug,
            save_path=Path(f"data/raw/iva_{slug}.pdf")
        )
        if pdf and pdf.exists():
            pdf_path = pdf
            print(f"✅ Found with slug: {slug}")
            break
    
    if not pdf_path:
        print("❌ Could not download IVA. Try manual URL verification.")
        return
    
    # Extract text
    print("\n📄 Extracting text...")
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n\n"
        
        text_path = Path("data/raw/iva_extracted.txt")
        text_path.write_text(full_text, encoding='utf-8')
        print(f"✅ Extracted {len(full_text):,} characters")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return
    
    # Generate XML
    print("\n🔨 Generating Akoma Ntoso XML...")
    generator = AkomaNtosoGenerator()
    
    metadata = generator.create_frbr_metadata(
        law_type='ley',
        date_str='1978-12-29',  # Original IVA publication
        slug='iva',
        title='Ley del Impuesto al Valor Agregado'
    )
    
    output_path = Path("data/federal/mx-fed-iva.xml")
    try:
        generator.generate_xml(full_text, metadata, output_path)
        print(f"✅ Generated: {output_path}")
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Validate
    print("\n🔍 Validating XML...")
    from lxml import etree
    
    tree = etree.parse(str(output_path))
    root = tree.getroot()
    
    articles = len(root.findall('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}article'))
    chapters = len(root.findall('.//{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}chapter'))
    
    print(f"✅ Articles: {articles}")
    print(f"✅ Chapters: {chapters}")
    
    print("\n" + "=" * 70)
    print("🎉 IVA INGESTION COMPLETE")
    print("=" * 70)
    print(f"\nComparison:")
    print(f"  Ley de Amparo: 285 articles, 31 chapters")
    print(f"  Ley del IVA:   {articles} articles, {chapters} chapters")
    
    if articles > 0:
        print("\n✅ Parser handles multiple law types!")
    else:
        print("\n⚠️  Parser may need tuning for tax law structure")

if __name__ == "__main__":
    ingest_iva()
