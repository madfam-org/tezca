#!/usr/bin/env python3
"""
Silent bare-except auditor.

Scans `apps/` for `except Exception:` blocks whose body is only `pass`,
`continue`, or `...` — i.e. the failure is swallowed without logging.
Returns non-zero exit when any are found, so it can wire into CI.

Override pattern: add `# noqa: BLE001` on the `except` line to opt out.
Override should include a one-line justification comment above it.

Usage:
    python scripts/utils/audit_silent_excepts.py            # scan apps/
    python scripts/utils/audit_silent_excepts.py --json     # machine output
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ["apps"]
EXCLUDE_PARTS = {"__pycache__", "migrations", "node_modules", ".venv", "venv"}


def is_silent_body(body: list[ast.stmt]) -> bool:
    """A handler body is 'silent' when it does only pass/continue/Ellipsis."""
    if not body:
        return False
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Continue):
            continue
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and stmt.value.value is Ellipsis
        ):
            continue
        return False
    return True


def has_noqa(source_line: str) -> bool:
    return "noqa: BLE001" in source_line or "noqa:BLE001" in source_line


def scan_file(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return []
    lines = text.splitlines()
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        # Only flag bare except or `except Exception` / `except BaseException`
        exc_type = node.type
        is_broad = exc_type is None or (
            isinstance(exc_type, ast.Name)
            and exc_type.id in {"Exception", "BaseException"}
        )
        if not is_broad:
            continue
        if not is_silent_body(node.body):
            continue
        # Scan the handler-header span (from `except` line to the first body
        # line) for `# noqa: BLE001`. Black sometimes wraps a long-comment
        # `except Exception:  # noqa: ...` into multi-line form, putting the
        # noqa on a later line.
        first_body_line = node.body[0].lineno if node.body else node.lineno + 1
        header_lines = lines[node.lineno - 1 : first_body_line - 1]
        if any(has_noqa(line) for line in header_lines):
            continue
        line_idx = node.lineno - 1
        findings.append(
            (node.lineno, lines[line_idx].strip() if line_idx < len(lines) else "")
        )
    return findings


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for top in SCAN_DIRS:
        base = ROOT / top
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if any(part in EXCLUDE_PARTS for part in p.parts):
                continue
            files.append(p)
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON instead of human output"
    )
    args = parser.parse_args()

    all_findings: dict[str, list[tuple[int, str]]] = {}
    for path in iter_python_files():
        hits = scan_file(path)
        if hits:
            rel = path.relative_to(ROOT).as_posix()
            all_findings[rel] = hits

    total = sum(len(v) for v in all_findings.values())

    if args.json:
        print(
            json.dumps(
                {"total": total, "findings": all_findings},
                indent=2,
                sort_keys=True,
            )
        )
    else:
        if total == 0:
            print("OK: no silent bare-except blocks found in apps/.")
        else:
            print(f"FAIL: {total} silent bare-except block(s) found:\n")
            for rel, hits in sorted(all_findings.items()):
                for lineno, snippet in hits:
                    print(f"  {rel}:{lineno}: {snippet}")
            print(
                "\nFix: replace silent `pass`/`continue` with "
                "`logger.debug(..., exc_info=True)` or catch a narrower exception.\n"
                "Override (rare, justify above the line): add `# noqa: BLE001`."
            )
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
