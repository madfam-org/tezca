"""
Error tracking and categorization for ingestion pipeline.

Captures errors with full context and stack traces for debugging.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import traceback
import json


@dataclass
class ErrorRecord:
    """Record of an error that occurred during ingestion."""
    
    law_id: str
    category: str
    message: str
    stack_trace: str
    context: Dict[str, Any]
    timestamp: str
    stage: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def summary(self) -> str:
        """Get one-line summary."""
        return f"[{self.category}] {self.law_id}: {self.message}"


class ErrorTracker:
    """
    Track and categorize errors during ingestion.
    
    Error Categories:
    - DOWNLOAD_ERROR: PDF download failures
    - EXTRACTION_ERROR: PDF text extraction issues  
    - PARSE_ERROR: XML generation failures
    - VALIDATION_ERROR: Schema/completeness issues
    - QUALITY_ERROR: Low quality scores
    - UNKNOWN_ERROR: Uncategorized errors
    
    Usage:
        tracker = ErrorTracker()
        
        try:
            download_pdf(url)
        except Exception as e:
            tracker.track(
                law_id='amparo',
                category='DOWNLOAD_ERROR',
                exception=e,
                stage='download',
                context={'url': url}
            )
        
        # Get summary
        summary = tracker.get_summary()
        print(f"Total errors: {summary['total_errors']}")
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize error tracker.
        
        Args:
            log_file: Optional path to save error log
        """
        self.errors: List[ErrorRecord] = []
        self.log_file = log_file
        
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def track(self,
              law_id: str,
              category: str,
              exception: Exception,
              stage: Optional[str] = None,
              context: Optional[Dict] = None):
        """
        Track an error.
        
        Args:
            law_id: ID of law being processed
            category: Error category (e.g., DOWNLOAD_ERROR)
            exception: The exception that occurred
            stage: Pipeline stage where error occurred
            context: Additional context information
        """
        record = ErrorRecord(
            law_id=law_id,
            category=category,
            message=str(exception),
            stack_trace=traceback.format_exc(),
            context=context or {},
            timestamp=datetime.now().isoformat(),
            stage=stage
        )
        
        self.errors.append(record)
        
        # Write to log file if configured
        if self.log_file:
            self._write_to_log(record)
    
    def _write_to_log(self, record: ErrorRecord):
        """Write error record to log file."""
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(record.to_dict()) + '\n')
    
    def categorize_exception(self, exception: Exception, stage: str = None) -> str:
        """
        Auto-categorize an exception based on type and context.
        
        Args:
            exception: The exception to categorize
            stage: Pipeline stage where it occurred
        
        Returns:
            Error category string
        """
        exc_type = type(exception).__name__
        exc_msg = str(exception).lower()
        
        # Download errors
        if stage == 'download' or 'download' in exc_msg:
            return 'DOWNLOAD_ERROR'
        if 'request' in exc_type.lower() or 'http' in exc_msg:
            return 'DOWNLOAD_ERROR'
        
        # Extraction errors
        if stage == 'extract' or 'extract' in exc_msg:
            return 'EXTRACTION_ERROR'
        if 'pdf' in exc_msg or 'pdfplumber' in exc_msg:
            return 'EXTRACTION_ERROR'
        
        # Parse errors
        if stage == 'parse' or 'parse' in exc_msg:
            return 'PARSE_ERROR'
        if 'xml' in exc_msg.lower():
            return 'PARSE_ERROR'
        
        # Validation errors
        if stage == 'validate' or 'validat' in exc_msg:
            return 'VALIDATION_ERROR'
        if 'schema' in exc_msg:
            return 'VALIDATION_ERROR'
        
        # Quality errors
        if 'quality' in exc_msg or 'grade' in exc_msg:
            return 'QUALITY_ERROR'
        
        return 'UNKNOWN_ERROR'
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all tracked errors.
        
        Returns:
            Dictionary with error statistics
        """
        if not self.errors:
            return {
                'total_errors': 0,
                'by_category': {},
                'by_law': {},
                'by_stage': {}
            }
        
        return {
            'total_errors': len(self.errors),
            'by_category': self._count_by_field('category'),
            'by_law': self._count_by_field('law_id'),
            'by_stage': self._count_by_field('stage'),
            'recent': [e.summary() for e in self.errors[-5:]]
        }
    
    def _count_by_field(self, field: str) -> Dict[str, int]:
        """Count errors grouped by field value."""
        counts = {}
        for error in self.errors:
            value = getattr(error, field, 'unknown')
            if value:
                counts[value] = counts.get(value, 0) + 1
        return counts
    
    def get_errors_for_law(self, law_id: str) -> List[ErrorRecord]:
        """Get all errors for a specific law."""
        return [e for e in self.errors if e.law_id == law_id]
    
    def get_errors_by_category(self, category: str) -> List[ErrorRecord]:
        """Get all errors of a specific category."""
        return [e for e in self.errors if e.category == category]
    
    def clear(self):
        """Clear all tracked errors."""
        self.errors.clear()
    
    def print_summary(self):
        """Print formatted error summary."""
        summary = self.get_summary()
        
        print("=" * 70)
        print("ERROR SUMMARY")
        print("=" * 70)
        
        print(f"\nTotal errors: {summary['total_errors']}")
        
        if summary['by_category']:
            print(f"\nBy category:")
            for category, count in sorted(summary['by_category'].items()):
                print(f"  {category}: {count}")
        
        if summary['by_law']:
            print(f"\nBy law:")
            for law_id, count in sorted(summary['by_law'].items()):
                print(f"  {law_id}: {count}")
        
        if summary.get('recent'):
            print(f"\nRecent errors:")
            for error_summary in summary['recent']:
                print(f"  • {error_summary}")
        
        print("=" * 70)


def main():
    """Test error tracker."""
    
    print("Testing Error Tracker\n")
    
    # Create tracker with log file
    log_file = Path('data/logs/errors.log')
    tracker = ErrorTracker(log_file=log_file)
    
    # Simulate various errors
    try:
        raise ConnectionError("Failed to connect to server")
    except Exception as e:
        tracker.track('amparo', 'DOWNLOAD_ERROR', e, 'download', {'url': 'http://example.com'})
    
    try:
        raise ValueError("Invalid PDF format")
    except Exception as e:
        tracker.track('iva', 'EXTRACTION_ERROR', e, 'extract', {'pdf': 'iva.pdf'})
    
    try:
        raise RuntimeError("XML generation failed")
    except Exception as e:
        tracker.track('lft', 'PARSE_ERROR', e, 'parse', {'line': 1234})
    
    try:
        raise AssertionError("Quality score too low: 65%")
    except Exception as e:
        cat = tracker.categorize_exception(e, 'quality')
        tracker.track('ccf', cat, e, context={'score': 65})
    
    # Print summary
    tracker.print_summary()
    
    print(f"\n✅ Error log written to: {log_file}")


if __name__ == "__main__":
    main()
