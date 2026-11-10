#!/usr/bin/env python3
"""Compare SAT's RMF publications with the pinned manifest; report what is new.

Why this runs outside the cluster: www.sat.gob.mx sits behind CloudFront, and
from the production egress (Hetzner, Europe) every request ends in a CloudFront
504 ("can't connect to the server for this app"). The in-cluster quarterly
``dataops.run_rmf_scraper`` therefore never sees SAT. The weekly
``.github/workflows/sat-rmf-watch.yml`` workflow runs this script on a
GitHub-hosted runner and opens/updates an issue when SAT lists an RMF document
(the DOF-format resolution, a resolución de modificaciones, or a compiled
edition) that the manifest does not know yet.

Detection only: pinning a document means verifying it and recording its
SHA-256, which an operator does (docs/runbooks/rmf-rule-ingestion.md).

Usage::

    python3 scripts/check_sat_rmf_compilations.py [--year 2026] [--report out.md]
    python3 scripts/check_sat_rmf_compilations.py --html saved_index.html

Exit codes: 0 = checked (new documents, if any, are in the report and in the
``new_count`` GitHub output), 2 = SAT unreachable or the page has no RMF links.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Set

SAT_DIR = "https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/"
REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "apps" / "parsers" / "rmf" / "manifests"
USER_AGENT = "Mozilla/5.0 (compatible; tezca-sat-rmf-watch)"

# documentos2026/rmf/rmf/... (DOF-format resolutions) and
# documentos2026/rmf/compiladas/... (SAT compiled editions). Versiones
# anticipadas (rmf/anticipadas/) are previews, not publications.
_LINK_RE = re.compile(
    r'href="(documentos(\d{4})/rmf/(rmf|compiladas)/([^"]+?\.pdf))"', re.IGNORECASE
)


def index_url(year: int) -> str:
    return f"{SAT_DIR}normatividad_rmf_rgce{year}.html"


def rmf_links(page: str, year: int) -> List[Dict[str, str]]:
    """RMF resolution and compiled-edition PDFs on the SAT page (no anexos,
    no RGCE). Returns ``[{"kind", "filename", "url"}]`` in page order."""
    out: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for path, link_year, folder, filename in _LINK_RE.findall(page):
        if int(link_year) != year:
            continue
        if "anexo" in filename.lower() or "rgce" in filename.lower():
            continue
        if filename in seen:
            continue
        seen.add(filename)
        out.append(
            {
                "kind": "compilada" if folder.lower() == "compiladas" else "resolucion",
                "filename": filename,
                "url": SAT_DIR + path,
            }
        )
    return out


def known_filenames(manifest: dict) -> Set[str]:
    names = {v["filename"] for v in manifest.get("versions", []) if v.get("filename")}
    for entry in manifest.get("instruments", []) + manifest.get("pending", []):
        url = entry.get("document_url") or ""
        if url.startswith(SAT_DIR):
            names.add(url.rsplit("/", 1)[-1])
    return names


def build_report(year: int, links: List[Dict[str, str]], manifest) -> tuple:
    if manifest is None:
        new = links
        header = f"No manifest `apps/parsers/rmf/manifests/rmf_{year}.json` yet."
    else:
        known = known_filenames(manifest)
        new = [link for link in links if link["filename"] not in known]
        header = f"Manifest `rmf_{year}.json` knows {len(known)} SAT document(s)."
    lines = [
        f"## SAT RMF {year}: {len(new)} publication(s) not in the manifest",
        "",
        f"Source: {index_url(year)} (checked {datetime.date.today().isoformat()}).",
        header,
        "",
    ]
    if new:
        lines += [
            "| Kind | File |",
            "|---|---|",
            *[f"| {n['kind']} | [{n['filename']}]({n['url']}) |" for n in new],
            "",
            "Next step: verify each document, add it to the manifest with its "
            "SHA-256 (a compiled edition becomes a new version; a resolution "
            "goes under `instruments`), then run `ingest_rmf_rules` and "
            "`index_laws --law-id rmf_<year>` as in "
            "`docs/runbooks/rmf-rule-ingestion.md`.",
        ]
    return new, "\n".join(lines) + "\n"


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        return response.read().decode("utf-8", errors="replace")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--year", type=int, default=datetime.date.today().year)
    parser.add_argument("--html", help="Read a saved SAT page instead of fetching")
    parser.add_argument("--manifest-dir", default=str(MANIFEST_DIR))
    parser.add_argument("--report", help="Write the markdown report here")
    args = parser.parse_args(argv)

    try:
        if args.html:
            page = Path(args.html).read_text(encoding="utf-8", errors="replace")
        else:
            page = fetch(index_url(args.year))
    except Exception as exc:  # network, HTTP 5xx, CloudFront errors
        print(f"SAT unreachable: {exc}", file=sys.stderr)
        return 2

    links = rmf_links(page, args.year)
    if not links:
        print(f"No RMF links for {args.year} on the SAT page", file=sys.stderr)
        return 2

    manifest_path = Path(args.manifest_dir) / f"rmf_{args.year}.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else None
    )
    new, report = build_report(args.year, links, manifest)
    print(report)
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"new_count={len(new)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
