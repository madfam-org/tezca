# Scraper Module

This module handles fetching legal texts from official sources.

## Tools

- **Juriscraper**: The core library for scraping court and legislative data.
- **Requests**: For simple HTTP fetching where Juriscraper isn't suitable.

## Scripts

### `dof_daily.py`

Fetches the daily edition of the *Diario Oficial de la Federación*.

**Usage:**

```bash
poetry run python apps/scraper/dof_daily.py --date=2024-01-01
```
