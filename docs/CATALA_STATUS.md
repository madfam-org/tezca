# Catala Integration - Known Issue

## Status: Temporarily Disabled ⚠️

The OpenFisca tax calculation engine depends on Catala, a domain-specific language for tax code specification.

## Current State

**Catala Compiler**: ✅ Installed (v0.8.0 via opam)
**Python Runtime**: ❌ Not available in Python environment
**Impact**: `/api/v1/calculate/` endpoint returns placeholder response

## Root Cause

Catala is installed as an OCaml package via opam, but the Python bindings (`catala.runtime`) are not being generated or installed in the Python environment.

## Workaround Applied

**File**: `apps/api/views.py`
**Change**: Commented out OpenFisca imports and calculation logic
**Result**: API starts successfully, all other endpoints functional

```python
# BEFORE (crashed on startup)
from engines.openfisca.system import MexicanTaxSystem
system = MexicanTaxSystem()
sim = system.new_simulation()

# AFTER (temporary workaround)
# from engines.openfisca.system import MexicanTaxSystem
return Response({"message": "Calculation temporarily disabled..."})
```

## Impact Assessment

### ✅ Still Functional
- Law ingestion pipeline
- Law versioning and database
- Search and indexing
- Law viewer frontend
- Version history display

### ❌ Temporarily Unavailable
- Tax calculation API endpoint
- OpenFisca simulations
- Catala-based legal computations

## Permanent Fix Options

### Option 1: Install Catala Python Package (Recommended)
```dockerfile
# In Dockerfile after opam install
RUN eval $(opam env) && \
    catala python-runtime > /tmp/catala_runtime.py && \
    pip install /tmp/catala_runtime.py
```

### Option 2: Use Pre-compiled Catala
Check if Catala project provides pre-built Python wheels:
```bash
pip install catala-runtime  # If available
```

### Option 3: Separate Service Architecture
- Run Catala as standalone service
- API calls Catala via HTTP/gRPC
- Decouples concerns

### Option 4: Alternative Tax Engine
- Evaluate alternatives to OpenFisca+Catala
- Pure Python implementation
- Trade-off: Less formal verification

## Next Steps

1. **Research**: Check Catala documentation for Python runtime generation
2. **Test**: Try compiling Python runtime from Catala source
3. **Decide**: Choose permanent architecture (monolith vs microservices)
4. **Implement**: Apply chosen solution
5. **Verify**: Re-enable and test tax calculations

## For Now

The current disable is **acceptable** because:
- Law versioning (our current focus) doesn't depend on tax calculations
- API is stable and usable for all other features
- We can re-enable once we solve the Python binding issue

## References

- Catala: https://catala-lang.org/
- OpenFisca: https://openfisca.org/
- Issue Location: `apps/api/views.py:4`
