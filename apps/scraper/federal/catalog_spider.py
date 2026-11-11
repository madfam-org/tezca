import json
import re
from pathlib import Path

import requests
from lxml import html

from apps.scraper.utils.law_name import parse_catalog_title

URL = "https://www.diputados.gob.mx/LeyesBiblio/index.htm"
BASE_URL = "https://www.diputados.gob.mx/LeyesBiblio/"


def fetch_catalog(local_file=None):
    if local_file:
        with open(local_file, "r", encoding="iso-8859-1") as f:
            content = f.read()
    else:
        response = requests.get(URL)
        response.encoding = "iso-8859-1"  # Site uses legacy encoding
        content = response.text

    tree = html.fromstring(content)

    laws = []

    # Analyze structure: usually tables or lists
    # Looking for links to PDF files in 'pdf/' folder
    # Pattern: Link to PDF is often in a specific column

    # We'll look for rows (blocks) that contain both a title and a PDF link
    # This is heuristic based on common layouts

    # Find all links to PDFs
    links = tree.xpath('//a[contains(@href, "pdf/")]')

    seen_urls = set()

    for link in links:
        href = link.get("href")
        if not href or not href.endswith(".pdf"):
            continue

        full_url = BASE_URL + href if not href.startswith("http") else href
        clean_url = full_url.split("#")[0]

        if clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)

        # Heuristic to find title:
        # 1. Check parent's previous sibling
        # 2. Check nearby text

        # In Diputados site, usually:
        # <tr>
        #   <td> Title </td>
        #   <td> Link to PDF </td>
        # </tr>

        row = link.xpath("./ancestor::tr[1]")
        if not row:
            continue
        row = row[0]

        cells = row.findall("td")
        if not cells:
            continue

        # Title is usually in the first or second cell
        title = ""
        for cell in cells:
            text = cell.text_content().strip()
            if len(text) > 10 and not text.endswith(".pdf"):
                title = text
                break

        if not title:
            # Fallback
            title = Path(href).stem.replace("_", " ").title()

        # Extract ID (slug) from filename
        filename = Path(href).name
        slug = filename.lower().replace(".pdf", "")

        # The index cell prints the title, its DOF publication date and a
        # status marker ("Nueva reforma") separated by tabs and line breaks.
        # Keep only the title as the name; the date and the markers are
        # recorded in their own fields instead of inside the name.
        parsed = parse_catalog_title(title)
        entry = {
            "id": slug,
            "name": parsed.name,
            "url": clean_url,
            "remote_path": href,
        }
        if parsed.publication_date:
            entry["publication_date"] = parsed.publication_date
        if parsed.notes:
            entry["catalog_notes"] = parsed.notes
        laws.append(entry)

    return laws


def main():
    print("🕷️  Crawling legislative catalog...")

    # Try local first if args provided, else remote
    import sys

    local_path = "leyes_fed_dump.html" if Path("leyes_fed_dump.html").exists() else None

    laws = fetch_catalog(local_path)

    print(f"Found {len(laws)} laws.")

    output_path = Path("data/discovered_laws.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(laws, f, indent=2, ensure_ascii=False)

    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
