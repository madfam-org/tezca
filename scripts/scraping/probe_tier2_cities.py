#!/usr/bin/env python3
"""
Probe Tier-2 municipal city URLs to check which are reachable.

HEAD requests each city's base_url + catalog_path from MUNICIPALITY_CONFIGS.
Outputs a confirmed vs needs-reconfig list.

Usage:
    python scripts/scraping/probe_tier2_cities.py
    python scripts/scraping/probe_tier2_cities.py --timeout 15
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.scraper.municipal.config import MUNICIPALITY_CONFIGS, get_tier2_municipalities


def probe_city(city_key: str, config: dict, timeout: int = 10) -> dict:
    """Probe a single city's catalog URL."""
    base_url = config["base_url"].rstrip("/")
    catalog_path = config["selectors"]["catalog_path"]
    full_url = f"{base_url}{catalog_path}"

    result = {
        "city": city_key,
        "name": config["name"],
        "state": config["state"],
        "url": full_url,
        "base_url": base_url,
        "status": "unknown",
        "http_status": None,
        "response_time_ms": None,
        "error": None,
    }

    # First probe base_url
    try:
        start = time.time()
        resp = requests.head(
            base_url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TezaBot/1.0)"},
        )
        base_ok = resp.status_code < 500
    except Exception:
        base_ok = False

    if not base_ok:
        # Try GET as some servers reject HEAD
        try:
            resp = requests.get(
                base_url,
                timeout=timeout,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; TezaBot/1.0)"},
            )
            base_ok = resp.status_code < 500
        except Exception as e:
            result["status"] = "base_unreachable"
            result["error"] = str(e)[:200]
            return result

    # Probe catalog URL
    try:
        start = time.time()
        resp = requests.get(
            full_url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TezaBot/1.0)"},
        )
        elapsed_ms = int((time.time() - start) * 1000)

        result["http_status"] = resp.status_code
        result["response_time_ms"] = elapsed_ms

        if resp.status_code == 200:
            result["status"] = "confirmed"
        elif resp.status_code in (301, 302, 303, 307, 308):
            result["status"] = "redirect"
            result["error"] = f"Redirected to: {resp.headers.get('Location', '?')}"
        elif resp.status_code == 403:
            result["status"] = "waf_blocked"
            result["error"] = "403 Forbidden (WAF?)"
        elif resp.status_code == 404:
            result["status"] = "needs_reconfig"
            result["error"] = "Catalog path not found"
        else:
            result["status"] = "error"
            result["error"] = f"HTTP {resp.status_code}"

    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = f"Timeout after {timeout}s"
    except requests.exceptions.ConnectionError as e:
        result["status"] = "connection_error"
        result["error"] = str(e)[:200]
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]

    return result


def main():
    parser = argparse.ArgumentParser(description="Probe Tier-2 city URLs")
    parser.add_argument(
        "--timeout", type=int, default=10, help="Request timeout in seconds"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/municipal/tier2_probe_results.json",
        help="Output JSON file",
    )
    args = parser.parse_args()

    tier2_cities = get_tier2_municipalities()
    print(f"Probing {len(tier2_cities)} Tier-2 cities...\n")

    results = []
    confirmed = []
    needs_reconfig = []

    for city_key in tier2_cities:
        config = MUNICIPALITY_CONFIGS[city_key]
        print(f"  {config['name']:25} ", end="", flush=True)

        result = probe_city(city_key, config, timeout=args.timeout)
        results.append(result)

        status = result["status"]
        if status == "confirmed":
            print(f"✅ OK ({result['response_time_ms']}ms)")
            confirmed.append(city_key)
        elif status == "redirect":
            print(f"↪️  Redirect — may work ({result['error']})")
            confirmed.append(city_key)  # Redirects often work
        elif status == "needs_reconfig":
            print(f"❌ 404 — needs reconfig")
            needs_reconfig.append(city_key)
        elif status == "waf_blocked":
            print(f"🛡️  WAF blocked")
            needs_reconfig.append(city_key)
        else:
            print(f"⚠️  {status}: {result.get('error', '')[:60]}")
            needs_reconfig.append(city_key)

        time.sleep(0.5)  # Rate limit

    # Summary
    print(f"\n{'='*60}")
    print("PROBE SUMMARY")
    print(f"{'='*60}")
    print(f"Total probed:     {len(results)}")
    print(f"Confirmed:        {len(confirmed)}")
    print(f"Needs reconfig:   {len(needs_reconfig)}")

    if confirmed:
        print(f"\n✅ Ready for scraping ({len(confirmed)}):")
        for c in confirmed:
            print(f"   - {c}")

    if needs_reconfig:
        print(f"\n❌ Need reconfig ({len(needs_reconfig)}):")
        for c in needs_reconfig:
            r = next(r for r in results if r["city"] == c)
            print(f"   - {c}: {r.get('error', 'unknown')}")

    # Save results
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "probe_date": datetime.now().isoformat(),
        "total": len(results),
        "confirmed": confirmed,
        "needs_reconfig": needs_reconfig,
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
