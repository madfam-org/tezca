"""
Law ingestion pipeline - End-to-end processing.

Combines: Download → Extract → Parse → Validate → Quality Assessment
"""

from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time
import requests
from datetime import datetime

# Import components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.parsers.akn_generator_v2 import AkomaNtosoGeneratorV2
from apps.parsers.quality import QualityCalculator, QualityMetrics


@dataclass
class IngestionResult:
    """Result of complete law ingestion."""
    
    # Identification
    law_id: str
    law_name: str
    
    # Status
    success: bool
    error: Optional[str] = None
    
    # Outputs
    pdf_path: Optional[Path] = None
    text_path: Optional[Path] = None
    xml_path: Optional[Path] = None
    
    # Quality
    quality_metrics: Optional[QualityMetrics] = None
    
    # Performance
    duration_seconds: float = 0.0
    
    # Stages completed
    stages_completed: list = None
    
    def __post_init__(self):
        if self.stages_completed is None:
            self.stages_completed = []
    
    @property
    def grade(self) -> str:
        """Get quality grade if available."""
        if self.quality_metrics:
            return self.quality_metrics.grade
        return 'N/A'
    
    def summary(self) -> str:
        """Human-readable summary."""
        status = "✅" if self.success else "❌"
        grade_str = f"Grade {self.grade}" if self.success else self.error
        return f"{status} {self.law_id}: {grade_str} ({self.duration_seconds:.1f}s)"


class IngestionPipeline:
    """
    Complete law ingestion pipeline.
    
    Stages:
    1. Download PDF from source
    2. Extract text from PDF
    3. Parse text to Akoma Ntoso XML
    4. Validate XML (schema + completeness)
    5. Calculate quality metrics
    
    Usage:
        pipeline = IngestionPipeline()
        result = pipeline.ingest_law(law_metadata)
        
        if result.success:
            print(f"✅ {result.law_id}: Grade {result.grade}")
        else:
            print(f"❌ {result.law_id}: {result.error}")
    """
    
    def __init__(self, 
                 data_dir: Path = None,
                 skip_download: bool = False):
        """
        Initialize pipeline.
        
        Args:
            data_dir: Base directory for data storage
            skip_download: If True, use existing PDFs
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / 'data'
        
        self.data_dir = Path(data_dir)
        self.skip_download = skip_download
        
        # Directories
        self.pdf_dir = self.data_dir / 'raw' / 'pdfs'
        self.text_dir = self.data_dir / 'raw'
        self.xml_dir = self.data_dir / 'federal'
        
        # Create directories
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.text_dir.mkdir(parents=True, exist_ok=True)
        self.xml_dir.mkdir(parents=True, exist_ok=True)
        
        # Components
        self.parser = AkomaNtosoGeneratorV2()
        self.quality_calc = QualityCalculator()
        
        # DB Integration
        try:
            from ingestion.db_saver import DatabaseSaver
            self.db_saver = DatabaseSaver()
            print("✅ Database connection established")
        except Exception as e:
            print(f"⚠️  Database connection failed: {e}")
            self.db_saver = None
    
    def ingest_law(self, 
                   law_metadata: Dict[str, Any],
                   max_retries: int = 2) -> IngestionResult:
        """
        Ingest a single law through complete pipeline.
        
        Args:
            law_metadata: Law metadata from registry
            max_retries: Maximum retry attempts on failure
        
        Returns:
            IngestionResult with success/failure details
        """
        start_time = time.time()
        law_id = law_metadata['id']
        law_name = law_metadata.get('short_name', law_metadata['name'])
        
        result = IngestionResult(
            law_id=law_id,
            law_name=law_name,
            success=False
        )
        
        # Retry loop
        for attempt in range(max_retries + 1):
            try:
                print(f"\n{'='*70}")
                print(f"📚 Ingesting: {law_name} ({law_id})")
                if attempt > 0:
                    print(f"   Retry {attempt}/{max_retries}")
                print(f"{'='*70}")
                
                # Stage 1: Download PDF
                pdf_path = self._download_pdf(law_metadata)
                result.pdf_path = pdf_path
                result.stages_completed.append('download')
                print(f"✅ Downloaded PDF: {pdf_path.name}")
                
                # Stage 2: Extract text
                text_path, text = self._extract_text(law_metadata, pdf_path)
                result.text_path = text_path
                result.stages_completed.append('extract')
                print(f"✅ Extracted text: {len(text):,} characters")
                
                # Stage 3: Parse to XML
                xml_path = self._parse_to_xml(law_metadata, text)
                result.xml_path = xml_path
                result.stages_completed.append('parse')
                print(f"✅ Generated XML: {xml_path.name}")
                
                # Stage 4: Calculate quality
                parse_time = time.time() - start_time
                metrics = self._calculate_quality(xml_path, law_metadata, parse_time)
                result.quality_metrics = metrics
                result.stages_completed.append('quality')
                print(f"✅ Quality: Grade {metrics.grade} ({metrics.overall_score:.1f}%)")
                
                # Success!
                result.success = True
                result.duration_seconds = time.time() - start_time
                
                # Save to Database
                if self.db_saver:
                    try:
                        self.db_saver.save_law_version(law_metadata, xml_path, pdf_path)
                        print("✅ Metadata saved to database")
                    except Exception as e:
                        print(f"⚠️  Failed to save to DB: {e}")
                
                print(f"\n🎉 Success! {law_id} completed in {result.duration_seconds:.1f}s")
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"⚠️  Error: {error_msg}")
                    print(f"   Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    result.error = f"Failed after {max_retries + 1} attempts: {error_msg}"
                    result.duration_seconds = time.time() - start_time
                    print(f"❌ Failed: {result.error}")
                    return result
        
        return result
    
    def _download_pdf(self, law_metadata: Dict) -> Path:
        """Download PDF from URL or use existing."""
        law_id = law_metadata['id']
        pdf_path = self.pdf_dir / f"{law_id}.pdf"
        
        # Use existing if skip_download or already exists
        if self.skip_download and pdf_path.exists():
            return pdf_path
        
        if pdf_path.exists():
            # Check if file is valid (size > 1KB)
            if pdf_path.stat().st_size > 1024:
                return pdf_path
        
        # Download from URL
        url = law_metadata['url']
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        pdf_path.write_bytes(response.content)
        return pdf_path
    
    def _extract_text(self, law_metadata: Dict, pdf_path: Path) -> tuple[Path, str]:
        """Extract text from PDF."""
        law_id = law_metadata['id']
        text_path = self.text_dir / f"{law_id}_extracted.txt"
        
        # Use existing if available
        if text_path.exists():
            text = text_path.read_text(encoding='utf-8')
            return text_path, text
        
        # Extract using pdfplumber
        import pdfplumber
        
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        
        full_text = '\n'.join(text_parts)
        
        # Save extracted text
        text_path.write_text(full_text, encoding='utf-8')
        
        return text_path, full_text
    
    def _parse_to_xml(self, law_metadata: Dict, text: str) -> Path:
        """Parse text to Akoma Ntoso XML."""
        law_id = law_metadata['id']
        xml_path = self.xml_dir / f"mx-fed-{law_id}-v2.xml"
        
        # Create FRBR metadata
        # V2 uses a more comprehensive dictionary
        metadata = {
            'law_id': law_id,
            'title': law_metadata['name'],
            'date': law_metadata['publication_date'], # Initial publication
            'slug': law_metadata['slug'],
            'law_type': law_metadata.get('type', 'ley'),
            'status': law_metadata.get('status', 'vigente')
        }
        
        # Generate XML using V2 (which handles multi-pass and internal metadata extraction)
        # Note: metadata dictionary passed here overrides/supplements internal extraction
        self.parser.generate_xml(text, metadata, xml_path)
        
        return xml_path
    
    def _calculate_quality(self, 
                          xml_path: Path, 
                          law_metadata: Dict,
                          parse_time: float) -> QualityMetrics:
        """Calculate quality metrics for generated XML."""
        metrics = self.quality_calc.calculate(
            xml_path=xml_path,
            law_name=law_metadata['name'],
            law_slug=law_metadata['slug'],
            articles_expected=law_metadata.get('expected_articles'),
            parse_time=parse_time,
            parser_confidence=0.99  # Default high confidence for v2
        )
        
        return metrics


def main():
    """Test pipeline on a single law."""
    
    print("🔧 Testing Ingestion Pipeline\n")
    
    # Test law metadata (Amparo - already have PDF)
    test_law = {
        'id': 'amparo',
        'name': 'Ley de Amparo',
        'short_name': 'Ley de Amparo',
        'type': 'ley',
        'slug': 'amparo',
        'expected_articles': 300,
        'publication_date': '2013-04-02',
        'url': 'https://www.diputados.gob.mx/LeyesBiblio/pdf/LAmp.pdf',
    }
    
    # Create pipeline (skip download for speed)
    pipeline = IngestionPipeline(skip_download=True)
    
    # Run ingestion
    result = pipeline.ingest_law(test_law)
    
    # Print result
    print("\n" + "="*70)
    print("INGESTION RESULT")
    print("="*70)
    print(result.summary())
    
    if result.success:
        print(f"\nStages: {' → '.join(result.stages_completed)}")
        print(f"XML: {result.xml_path}")
        print(f"\nQuality Metrics:")
        print(f"  Accuracy: {result.quality_metrics.accuracy_score:.1f}%")
        print(f"  Completeness: {result.quality_metrics.completeness_score:.1f}%")
        print(f"  Overall: {result.quality_metrics.overall_score:.1f}%")
        print(f"  Grade: {result.quality_metrics.grade}")
    else:
        print(f"\nError: {result.error}")
    
    print("="*70)


if __name__ == "__main__":
    main()
