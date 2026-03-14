import json
import sys

import requests

API_BASE = "http://localhost:8000/api/v1"


def test_endpoint(name, url):
    print(f"Testing {name} ({url})...", end=" ")
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            print("✅ OK")
            return res.json()
        else:
            print(f"❌ Failed ({res.status_code})")
            print(res.text)
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def verify_system():
    print("🔍 Starting End-to-End System Verification\n")

    # 1. Test Law List
    laws = test_endpoint("Law List", f"{API_BASE}/laws/")
    if laws and len(laws) > 0:
        print(f"   found {len(laws)} laws registered in DB.")
        print(f"   sample: {laws[0]['id']} ({laws[0]['versions']} versions)")
    else:
        print(
            "   ⚠️ No laws found in DB list (might be expected if ingestion is fresh)"
        )

    # 2. Test Law Detail (Amparo)
    law_id = "amparo"
    detail = test_endpoint(f"Law Detail ({law_id})", f"{API_BASE}/laws/{law_id}/")
    if detail:
        print(f"   Name: {detail['name']}")
        versions = detail.get("versions", [])
        print(f"   Versions: {len(versions)}")
        if versions:
            v1 = versions[0]
            print(f"   Latest Version: {v1['publication_date']}")
            print(f"   XML File: {v1['xml_file']}")
            if v1["xml_file"]:
                print("   ✅ XML link present")
            else:
                print("   ❌ XML link missing")

    # 3. Test Search
    query = "amparo"
    search = test_endpoint(f"Search ('{query}')", f"{API_BASE}/search/?q={query}")
    if search:
        results = search.get("results", [])
        print(f"   Results found: {len(results)}")
        if len(results) > 0:
            first = results[0]
            print(f"   Top Result: {first['law']} - {first['article']}")
            if "date" in first:
                print(f"   ✅ Date present: {first['date']}")
            else:
                print("   ❌ Date missing in search result")
        else:
            print("   ⚠️ No search results found")

    print("\n🏁 Verification Complete")


if __name__ == "__main__":
    verify_system()
