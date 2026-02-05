# Parser Gap Analysis - POC Issues

## Executive Summary

**POC Parser Accuracy**: ~90-95% (good, but below 95% target)
**Critical Gaps**: 3 issues blocking 95% threshold
**Recommendation**: Implement v2 parser with enhanced patterns

---

## Issue 1: Article Detection Gaps

### Observed
- **Ley de Amparo**: 285 articles parsed vs ~300 expected (~5% missing)
- **Ley del IVA**: 94 articles (appears correct)

### Root Cause Analysis

**Current Regex**:
```python
r'^Artículo\s+\d+[a-z]?\.?'
```

**Problems**:
1. **Doesn't match letter ed articles**: "Artículo 27-A" (dash format)
2. **Case sensitive**: Won't match "ARTÍCULO" or "artículo"
3. **Spacing variations**: Won't match "Artículo  5" (double space)

### Proposed Fix
```python
ARTICLE_PATTERNS = [
    r'^Art[íi]culo\s+\d+[A-Z]?\.?',      # Standard: Artículo 5
    r'^Art[íi]culo\s+\d+-[A-Z]\.?',      # Dash: Artículo 27-A  
    r'^Art[íi]culo\s+\d+\s+[A-Z]\.?',    # Space: Artículo 27 A
    r'^ART[ÍI]CULO\s+\d+',                # Uppercase
]
```

**Expected Improvement**: 95% → 98% article coverage

---

## Issue 2: TÍTULO Detection Failure

### Observed
- **Ley de Amparo**: 0 titles found
- **Ley del IVA**: 1 title found ✅

### Analysis

Manual PDF review of Amparo:
- PDF structure: `LIBRO PRIMERO` → `TÍTULO` → `CAPÍTULO`
- **Hypothesis**: Amparo uses `LIBRO` not `TÍTULO` as top level

**Current Pattern**:
```python
r'^TÍTULO\s+[IVX]+'  # Only matches TÍTULO
```

**Missing Patterns**:
- `LIBRO` (Book)
- `PARTE` (Part)
- Title case: "Título"

### Proposed Fix
```python
TITLE_PATTERNS = [
    r'^T[ÍI]TULO\s+[IVX]+',
    r'^LIBRO\s+[IVX]+',
    r'^LIBRO\s+(PRIMERO|SEGUNDO|TERCERO)',
    r'^PARTE\s+[IVX]+',
]
```

**Expected Improvement**: 0% → 100% when present

---

## Issue 3: TRANSITORIOS Missing

### Observed
- **All laws**: 0 transitory articles parsed
- **Impact**: Legal temporal transitions not captured

### Analysis

Transitory sections use different numbering:
```
TRANSITORIOS

PRIMERO.- Esta Ley entrará en vigor...
SEGUNDO.- Se abrogan las disposiciones...  
TERCERO.- Los juicios de garantías...
```

**vs regular articles**:
```
Artículo 1o.- El juicio de amparo...
Artículo 2o.- El amparo se tramitará ...
```

### Proposed Implementation

```python
def _find_transitorios(self, text: str) -> List[Dict]:
    """
    Parse TRANSITORIOS section with ordinal numbering.
    """
    # Find start of transitorios
    trans_start = re.search(
        r'^\s*(ART[ÍI]CULOS?\s+)?TRANSITORIOS?\s*$', 
        text, 
        re.MULTILINE | re.IGNORECASE
    )
    
    if not trans_start:
        return []
    
    # Ordinal patterns
    ORDINALS = {
        'PRIMER[OA]': 1,
        'SEGUND[OA]': 2, 
        'TERCER[OA]': 3,
        'CUART[OA]': 4,
        'QUINT[OA]': 5,
        # ... up to VIGÉSIMO or more
    }
    
    # Parse each transitorio
    transitorios = []
    for pattern, num in ORDINALS.items():
        matches = re.finditer(
            f'^({pattern})\\.-\\s+(.+?)(?=^[A-Z]+\\.-|$)',
            text[trans_start.end():],
            re.MULTILINE | re.DOTALL
        )
        for match in matches:
            transitorios.append({
                'type': 'transitorio',
                'number': num,
                'content': match.group(2).strip()
            })
    
    return sorted(transitorios, key=lambda x: x['number'])
```

**Expected Impact**: Capture 100% of transitory articles

---

## Issue 4: Reform Metadata Inline

### Observed
Text like:
```
Fracción reformada DOF 13-03-2025
Párrafo adicionado DOF 16-10-2025
```

Currently treated as part of content, not as metadata.

### Proposed Solution

```python
def _extract_reform_metadata(self, content: str) -> List[Dict]:
    """Extract reform annotations from content."""
    
    pattern = r'(Fracción|Párrafo|Artículo|Inciso)\s+(reformad[oa]|adicionad[oa]|derogad[oa])\s+DOF\s+(\d{2}-\d{2}-\d{4})'
    
    reforms = []
    for match in re.finditer(pattern, content):
        reforms.append({
            'element': match.group(1),
            'action': match.group(2),
            'date': match.group(3)
        })
    
    # Strip from content
    cleaned_content = re.sub(pattern, '', content)
    
    return cleaned_content, reforms
```

**Usage in XML**:
```xml
<article id="art-5">
  <num>Artículo 5</num>
  <content>...</content>
  <note placementBase="#art-5" placement="bottom">
    <p>Fracción I reformada DOF 13-03-2025</p>
  </note>
</article>
```

---

## Minor Issues (Lower Priority)

### Table Detection
**Status**: Not implemented
**Impact**: Tables rendered as text blob
**Priority**: Low (few laws have complex tables)

### Cross-References
**Example**: "en términos del artículo 5o"
**Status**: Not parsed as links
**Priority**: Low (enhancement for v3)

###Lettered Sub-Articles
**Example**: Artículo 27 fracción VI inciso a)
**Status**: Flat hierarchy
**Priority**: Medium (affects deeply nested laws)

---

## Testing Strategy

### Test Corpus (5 Laws)

| Law | Articles | Why Selected |
|-----|----------|--------------|
| **Amparo** | ~300 | LIBRO structure, many reforms |
| **IVA** | ~94 | TÍTULO structure, tables |
| **LFT** | ~1,010 | Largest, complex fractions |
| **CCF** | ~3,000 | Traditional structure, oldest |
| **LIC** | ~150 | Financial terminology, definitions |

### Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Article Coverage | 95% | 98% |
| TÍTULO Detection | 50% | 100% |
| TRANSITORIOS | 0% | 100% |
| Reform Metadata | 0% | 100% |
| **Overall Accuracy** | **90-95%** | **>95%** |

---

## Recommended Approach

### Phase 1: Pattern Library (Days 1-2)
Create reusable pattern modules:
- `apps/parsers/patterns/articles.py`
- `apps/parsers/patterns/structure.py`  
- `apps/parsers/patterns/metadata.py`

### Phase 2: Parser v2 (Days 3-7)
Implement `akn_generator_v2.py` with:
1. Multi-pattern matching
2. Confidence scoring
3. Warning/error reporting
4. Metadata extraction

### Phase 3: Validation (Days 8-10)
- Run on 5 test laws
- Compare v1 vs v2 metrics
- Document improvements

---

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|------------|
| **Patterns too brittle** | Medium | Test on diverse laws, add fallbacks |
| **Performance regression** | Low | Profile code, optimize |
| **95% still unreachable** | Low | Accept 93-94% if consistent across laws |

---

## Conclusion

The POC parser is **very good** (~90-95%) but has **3 critical gaps**:
1. Article detection edge cases
2. TÍTULO/LIBRO detection  
3. TRANSITORIOS parsing

All gaps are **fixable** with enhanced pattern matching. Estimated effort: **1-2 weeks** for v2 parser achieving >95% accuracy.

**Recommendation**: ✅ Proceed with v2 implementation per Week 1-2 plan.
