# Setup Guide

Complete installation and configuration guide for the Leyes Como Código pipeline.

## Prerequisites

- **Python**: 3.11 or higher
- **pip**: Latest version
- **Git**: For cloning repository
- **pdfplumber**: PDF text extraction (auto-installed)
- **lxml**: XML processing (auto-installed)

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/madfam-org/leyes-como-codigo-mx.git
cd leyes-como-codigo-mx
```

### 2. Create Virtual Environment (Recommended)

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key dependencies**:
- `pdfplumber` - PDF text extraction
- `lxml` - XML processing
- `requests` - HTTP downloads
- `pytest` - Testing framework

### 4. Verify Installation

```bash
python -c "from apps.parsers import AkomaNtosoGeneratorV2; print('✅ Installation successful!')"
```

## Quick Start

### Parse a Single Law

```python
from pathlib import Path
from apps.parsers import AkomaNtosoGeneratorV2

# Load law text
text = Path('data/raw/ley_amparo_extracted.txt').read_text()

# Create parser
parser = AkomaNtosoGeneratorV2()

# Generate FRBR metadata
metadata = parser.create_frbr_metadata(
    law_type='ley',
    date_str='2013-04-02',
    slug='amparo',
    title='Ley de Amparo'
)

# Parse to XML
xml_path, result = parser.generate_xml(
    text,
    metadata,
    Path('output/amparo.xml')
)

print(f"✅ Generated: {xml_path}")
print(f"Confidence: {result.metadata['confidence']*100:.1f}%")
```

### Batch Ingest Laws

```bash
# Ingest specific laws
python scripts/bulk_ingest.py --laws amparo,iva --workers 2

# Ingest by priority
python scripts/bulk_ingest.py --priority 1 --workers 4

# Ingest all laws
python scripts/bulk_ingest.py --all --workers 8

# Skip re-downloading PDFs
python scripts/bulk_ingest.py --all --skip-download
```

### Validate Quality

```python
from apps.parsers.quality import QualityCalculator

calc = QualityCalculator()
metrics = calc.calculate(
    xml_path='data/federal/mx-fed-amparo-v2.xml',
    law_name='Ley de Amparo',
    law_slug='amparo',
    articles_expected=300
)

print(f"Grade: {metrics.grade} ({metrics.overall_score:.1f}%)")
```

### Monitor Progress

```bash
# View dashboard
python scripts/ingestion_status.py

# View specific law
python scripts/ingestion_status.py --law amparo

# Last 48 hours
python scripts/ingestion_status.py --last 48
```

## Directory Structure

```
leyes-como-codigo-mx/
├── apps/
│   ├── parsers/           # Core parsing modules
│   │   ├── akn_generator_v2.py
│   │   ├── patterns/      # Pattern library
│   │   ├── validators/    # Quality validators
│   │   ├── quality.py     # Quality metrics
│   │   ├── pipeline.py    # Ingestion pipeline
│   │   ├── logger.py      # Structured logging
│   │   └── error_tracker.py
│   └── scraper/
│       └── law_registry.py
├── data/
│   ├── law_registry.json  # Law metadata
│   ├── federal/           # Generated XMLs
│   ├── raw/              # PDFs and extracted text
│   └── logs/             # Application logs
├── scripts/
│   ├── bulk_ingest.py    # Batch processing CLI
│   └── ingestion_status.py
├── tests/                # Test suite
└── docs/                 # Documentation
```

## Configuration

### Law Registry

Edit `data/law_registry.json` to add new laws:

```json
{
  "federal_laws": [
    {
      "id": "new-law",
      "name": "Official Law Name",
      "short_name": "Short Name",
      "type": "ley",
      "slug": "new-law",
      "expected_articles": 100,
      "publication_date": "2020-01-01",
      "url": "https://example.com/law.pdf",
      "priority": 1,
      "tier": "category"
    }
  ]
}
```

## Troubleshooting

### Import Errors

```bash
# Ensure Python path is set
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### PDF Download Failures

```bash
# Use --skip-download for existing PDFs
python scripts/bulk_ingest.py --laws amparo --skip-download
```

### Memory Issues

```bash
# Reduce worker count
python scripts/bulk_ingest.py --all --workers 2
```

### Test Failures

```bash
# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_patterns.py -v
```

## Next Steps

- Read [Architecture Guide](ARCHITECTURE.md)
- Explore [Examples](examples/)
- Run [Tests](../tests/)
- Check [API Reference](API.md)

## Support

- Issues: https://github.com/madfam-org/leyes-como-codigo-mx/issues
- Documentation: https://github.com/madfam-org/leyes-como-codigo-mx/docs
