# Sources of Truth

This document tracks the official sources for the legal content in the system.

## Federal Legislation
- **Source**: Cámara de Diputados del H. Congreso de la Unión
- **URL**: [https://www.diputados.gob.mx/LeyesBiblio/index.htm](https://www.diputados.gob.mx/LeyesBiblio/index.htm)
- **Content**: Full catalog of active federal laws (Leyes Federales Vigentes).
- **Format**: PDF (primary), DOC (secondary).
- **Last Crawl**: 2026-02-03
- **Coverage**: 317 Laws identified.

## Extraction Method
The `apps/scraper/catalog_spider.py` script crawls the official index page and extracts:
- Law Name (including official abbreviation if available)
- Publication Date / Last Reform Date
- URL to the latest PDF version

## Data Storage
- **Registry**: `data/law_registry.json` (Curated list with metadata)
- **Discovery**: `data/discovered_laws.json` (Raw output from spider)
- **Artifacts**: `data/federal/*.xml` (Parsed Akoma Ntoso files)
