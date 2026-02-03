"""
Structured logging for ingestion pipeline.

Provides JSON-formatted logging with contextual information for better observability.
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'law_id'):
            log_data['law_id'] = record.law_id
        if hasattr(record, 'stage'):
            log_data['stage'] = record.stage
        if hasattr(record, 'duration_seconds'):
            log_data['duration_seconds'] = record.duration_seconds
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data)


class StructuredLogger:
    """
    Structured logger for ingestion pipeline.
    
    Provides semantic logging methods with automatic context capture.
    
    Usage:
        logger = StructuredLogger('ingestion')
        logger.log_ingestion_start('amparo', 'Ley de Amparo')
        logger.log_stage_complete('amparo', 'parse', 23.5)
        logger.log_quality_check('amparo', {'grade': 'A', 'score': 99.2})
    """
    
    def __init__(self, 
                 name: str,
                 log_file: Optional[Path] = None,
                 json_format: bool = False):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            log_file: Optional file path for log output
            json_format: If True, use JSON formatting
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()  # Clear any existing handlers
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        if json_format:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(JSONFormatter())  # Always JSON for files
            self.logger.addHandler(file_handler)
    
    def log_ingestion_start(self, law_id: str, law_name: str):
        """Log start of law ingestion."""
        self.logger.info(
            f'Starting ingestion: {law_id}',
            extra={
                'law_id': law_id,
                'extra_data': {
                    'law_name': law_name,
                    'event': 'ingestion_start'
                }
            }
        )
    
    def log_ingestion_complete(self, law_id: str, duration: float, success: bool):
        """Log completion of law ingestion."""
        status = 'success' if success else 'failure'
        self.logger.info(
            f'Ingestion {status}: {law_id} ({duration:.1f}s)',
            extra={
                'law_id': law_id,
                'duration_seconds': duration,
                'extra_data': {
                    'event': 'ingestion_complete',
                    'success': success
                }
            }
        )
    
    def log_stage_start(self, law_id: str, stage: str):
        """Log start of pipeline stage."""
        self.logger.info(
            f'Stage start: {stage} ({law_id})',
            extra={
                'law_id': law_id,
                'stage': stage,
                'extra_data': {'event': 'stage_start'}
            }
        )
    
    def log_stage_complete(self, law_id: str, stage: str, duration: float):
        """Log completion of pipeline stage."""
        self.logger.info(
            f'Stage complete: {stage} ({law_id}, {duration:.1f}s)',
            extra={
                'law_id': law_id,
                'stage': stage,
                'duration_seconds': duration,
                'extra_data': {'event': 'stage_complete'}
            }
        )
    
    def log_quality_check(self, law_id: str, metrics: Dict[str, Any]):
        """Log quality check results."""
        self.logger.info(
            f'Quality check: {law_id} - Grade {metrics.get("grade")}',
            extra={
                'law_id': law_id,
                'extra_data': {
                    'event': 'quality_check',
                    'metrics': metrics
                }
            }
        )
    
    def log_error(self, law_id: str, stage: str, error: str, context: Dict = None):
        """Log error with context."""
        self.logger.error(
            f'Error in {stage}: {law_id} - {error}',
            extra={
                'law_id': law_id,
                'stage': stage,
                'extra_data': {
                    'event': 'error',
                    'error': error,
                    'context': context or {}
                }
            }
        )
    
    def log_warning(self, law_id: str, message: str, context: Dict = None):
        """Log warning with context."""
        self.logger.warning(
            f'Warning: {law_id} - {message}',
            extra={
                'law_id': law_id,
                'extra_data': {
                    'event': 'warning',
                    'context': context or {}
                }
            }
        )
    
    def log_batch_start(self, total_laws: int, workers: int):
        """Log start of batch processing."""
        self.logger.info(
            f'Batch start: {total_laws} laws with {workers} workers',
            extra={
                'extra_data': {
                    'event': 'batch_start',
                    'total_laws': total_laws,
                    'workers': workers
                }
            }
        )
    
    def log_batch_complete(self, total: int, success: int, failed: int, duration: float):
        """Log batch processing completion."""
        self.logger.info(
            f'Batch complete: {success}/{total} success ({duration:.1f}s)',
            extra={
                'duration_seconds': duration,
                'extra_data': {
                    'event': 'batch_complete',
                    'total': total,
                    'success': success,
                    'failed': failed,
                    'success_rate': success / total if total > 0 else 0
                }
            }
        )


def main():
    """Test structured logger."""
    
    print("Testing Structured Logger\n")
    
    # Create logger
    log_file = Path('data/logs/ingestion.log')
    logger = StructuredLogger('test', log_file=log_file, json_format=False)
    
    # Test various log types
    logger.log_batch_start(5, 4)
    
    logger.log_ingestion_start('amparo', 'Ley de Amparo')
    logger.log_stage_start('amparo', 'download')
    logger.log_stage_complete('amparo', 'download', 1.2)
    logger.log_stage_start('amparo', 'parse')
    logger.log_stage_complete('amparo', 'parse', 23.5)
    logger.log_quality_check('amparo', {
        'grade': 'A',
        'accuracy': 98.3,
        'overall': 99.2
    })
    logger.log_ingestion_complete('amparo', 25.0, True)
    
    logger.log_ingestion_start('iva', 'Ley del IVA')
    logger.log_warning('iva', 'Article gap detected', {'gap': '43-89'})
    logger.log_ingestion_complete('iva', 20.5, True)
    
    logger.log_ingestion_start('lft', 'Ley Federal del Trabajo')
    logger.log_error('lft', 'parse', 'Failed to extract text', {'pdf_path': 'lft.pdf'})
    logger.log_ingestion_complete('lft', 5.0, False)
    
    logger.log_batch_complete(3, 2, 1, 50.5)
    
    print(f"\n✅ Logs written to: {log_file}")


if __name__ == "__main__":
    main()
