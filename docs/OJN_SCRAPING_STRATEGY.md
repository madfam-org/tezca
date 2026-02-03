# Orden Jurídico Nacional (OJN) - Technical Findings

## Executive Summary

**Conclusion**: No API available, but **web scraping is highly feasible** due to structured URL patterns and predictable numeric IDs.

### Key Findings
- ✅ **Structured URLs**: Predictable patterns for all 32 states
- ⚠️ **Mixed formats**: PDFs and Word documents (.doc)
- ✅ **Rich metadata**: Publication dates, status (Vigente), law types
- ⚠️ **No bulk download**: Must scrape individually
- ✅ **High volume**: Est. 10,000+ state/municipal documents

## URL Structure Analysis

### Base Domain
- **Secure Portal**: `https://www.ordenjuridico.gob.mx/`
- **Data Subdomain**: `http://compilacion.ordenjuridico.gob.mx/` (HTTP only)

> **Note**: Modern browsers block mixed content, so must access `compilacion` subdomain directly

### URL Patterns

#### 1. State Selection
```
http://compilacion.ordenjuridico.gob.mx/poderes2.php?edo=[1-32]
```
- `edo=1`: Aguascalientes
- `edo=7`: Chiapas
- `edo=11`: Guanajuato
- `edo=32`: Zacatecas

#### 2. Power/Branch Selection
```
http://compilacion.ordenjuridico.gob.mx/listPoder2.php?edo=[EDO_ID]&idPoder=[1-4]
```
- `idPoder=1`: Poder Ejecutivo
- `idPoder=2`: **Poder Legislativo** (Main state laws - highest priority)
- `idPoder=3`: Poder Judicial
- `idPoder=4`: Órganos Autónomos

#### 3. Law Metadata (Ficha Técnica)
```
http://compilacion.ordenjuridico.gob.mx/fichaOrdenamiento2.php?idArchivo=[FILE_ID]&ambito=ESTATAL
```

Example: `idArchivo=38863` = Código Civil para el Estado de Guanajuato

#### 4. Document Download
```
http://compilacion.ordenjuridico.gob.mx/obtenerdoc.php?path=[PATH]&nombreclave=[FILENAME]
```

### Municipal Laws
```
http://compilacion.ordenjuridico.gob.mx/listPoder4.php?edo=[EDO_ID]&orderSelectionado=[MUN_ID]&catTipo=[MUN_ID]
```

Each state has unique municipality IDs accessible via dropdown

## Data Structure

### Metadata Available
From the "Ficha Técnica" page:

| Field | Example | Notes |
|-------|---------|-------|
| **Nombre Completo** | Código Civil para el Estado de Guanajuato | Full law name |
| **Fecha de publicación** | 14 de Mayo de 1967 | Publication date |
| **Poder** | Legislativo | Legislative branch |
| **Ámbito** | Estatal | State level |
| **Estatus** | Vigente | Active status |
| **Tipo** | Código | Law type (Ley, Código, Reglamento) |
| **Localidad** | Guanajuato | State/Municipality name |

### File Formats
- **PDF**: Common for recent laws
- **Word (.doc)**: Very common for state laws (requires conversion)
- **No XML**: Must convert from PDFs/Word

## Scraping Strategy

### Phase 1: State Legislative Laws (Priority)
**Target**: `idPoder=2` (Poder Legislativo) for all 32 states

**Estimated Volume**:
- Guanajuato alone: 700+ laws
- Conservative estimate across 32 states: **2,000-3,000 laws**

**Implementation**:
```python
def scrape_state_laws():
    for state_id in range(1, 33):  # 32 states
        url = f"http://compilacion.ordenjuridico.gob.mx/listPoder2.php?edo={state_id}&idPoder=2"
        laws = parse_law_list(url)
        
        for law in laws:
            metadata = fetch_ficha(law['file_id'])
            doc_url = build_download_url(metadata['path'], metadata['filename'])
            
            # Download and process
            if doc_url.endswith('.doc'):
                convert_word_to_pdf(doc_url)
            
            ingest_law(metadata, doc_path)
```

### Phase 2: State Constitutions
**Target**: State constitutions (one per state)

**Volume**: 32 documents

### Phase 3: Other State Powers
**Target**: Ejecutivo, Judicial, Órganos Autónomos

**Volume**: Est. 1,000+ additional documents

### Phase 4: Municipal Laws
**Target**: 2,465 municipalities

**Challenge**: Very high volume, many non-digitized

## Technical Challenges

### 1. Word Document Conversion
**Problem**: Many state laws are .doc files, not PDFs

**Solutions**:
- **LibreOffice**: `libreoffice --headless --convert-to pdf file.doc`
- **Python docx2pdf**: `from docx2pdf import convert`
- **Cloud service**: Microsoft Graph API for conversion

### 2. Metadata Extraction
**Problem**: No structured JSON, must parse HTML

**Solution**: BeautifulSoup + regex patterns

### 3. Rate Limiting
**Problem**: Scraping 10,000+ documents may trigger blocks

**Solution**: 
- Respectful scraping (1-2 requests/second)
- Rotating user agents
- Contact SEGOB for permission

### 4. Mixed Content Security
**Problem**: HTTP subdomain blocked by HTTPS main site

**Solution**: Direct access to http://compilacion.ordenjuridico.gob.mx/

## Implementation Roadmap

### Week 1: Scraper Development
```python
# scripts/scraping/ojn_scraper.py

class OJNScraper:
    BASE_URL = "http://compilacion.ordenjuridico.gob.mx"
    
    def get_state_laws(self, state_id: int, power_id: int = 2):
        """Fetch all laws for a given state and power"""
        
    def get_law_metadata(self, file_id: int):
        """Fetch ficha técnica for a specific law"""
        
    def download_document(self, path: str, filename: str):
        """Download PDF or Word document"""
        
    def convert_word_to_pdf(self, doc_path: str):
        """Convert .doc to .pdf for processing"""
```

### Week 2: Test on Sample States
- Test on 3 diverse states (small, medium, large)
- Validate metadata extraction
- Test Word→PDF conversion pipeline

### Week 3-4: Full State Ingestion
- Scrape all 32 states (Poder Legislativo)
- Process ~2,000-3,000 laws
- Ingest into database via existing pipeline

### Month 2: Expand to Other Powers
- Add Ejecutivo, Judicial, Autónomos
- Est. +1,000 laws

### Long-term: Municipal
- Phased approach by population
- Partnership with municipalities for digital access

## Cost-Benefit Analysis

### Benefits
- Access to official state law database
- Structured metadata
- All 32 states in one place

### Costs
- Must build and maintain scraper
- Word document conversion overhead
- Slower than API (no bulk download)

### Comparison to Manual Approach
| Method | Time | Coverage | Reliability |
|--------|------|----------|-------------|
| **OJN Scraping** | 2-3 months | ~3,000 laws | High |
| **Per-State Gazettes** | 6-12 months | ~3,000 laws | Medium |
| **Manual Collection** | 12+ months | Partial | Low |

**Recommendation**: OJN scraping is the most efficient path to state coverage

## Next Steps

1. **Get Permission**: Contact SEGOB (Secretaría de Gobernación) for authorization
2. **Build Scraper**: Implement OJNScraper class
3. **Test Pipeline**: Pilot with 3 states
4. **Full Rollout**: Ingest all 32 states

## Example: Guanajuato Civil Code

**URL Pattern**:
```
# Law list
http://compilacion.ordenjuridico.gob.mx/listPoder2.php?edo=11&idPoder=2

# Metadata
http://compilacion.ordenjuridico.gob.mx/fichaOrdenamiento2.php?idArchivo=38863&ambito=ESTATAL

# Download
http://compilacion.ordenjuridico.gob.mx/obtenerdoc.php?path=[path]&nombreclave=[filename]
```

**Metadata**:
- Name: Código Civil para el Estado de Guanajuato
- Publication: 14 de Mayo de 1967
- Status: Vigente
- Type: Código
- Format: .doc (requires conversion)

## Screenshot Reference

![OJN Law Metadata](file:///Users/aldoruizluna/.gemini/antigravity/brain/3ec34962-a9c9-40c7-a4b1-3ebf35f1db9c/law_ficha_metadata_1770109558007.png)

Shows the structured metadata available for each law.

## Conclusion

**OJN is scrapable** and provides a centralized path to 2,000-3,000 state laws. While not as fast as an API, it's significantly more efficient than scraping 32 different state gazettes.

**Estimated Timeline**: 2-3 months to full state legislative coverage

---

**Research Date**: 2026-02-03 
**Source**: Orden Jurídico Nacional (SEGOB)  
**Status**: Ready for implementation
