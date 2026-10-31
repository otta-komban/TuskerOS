#!/usr/bin/env python3
"""Validate PILOT-08's implementation-neutral conformance case tables.

This tool checks documentation integrity only. It does not execute security tests,
validate runtime behavior, freeze shared contracts, or grant implementation approval.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

SPECS = {
    "PAIR": ("remote-control/verification/DEVICE-IDENTITY-AND-PAIRING-CONFORMANCE.md", 22),
    "SESS": ("remote-control/verification/SESSION-PROOF-AND-REVOCATION-CONFORMANCE.md", 40),
    "NET": ("remote-control/verification/TRANSPORT-AND-EXPOSURE-CONFORMANCE.md", 42),
}
CASE_ID = re.compile(r"^(PAIR|SESS|NET)-C(\d{2})$")


class SpecError(ValueError):
    """Raised when a conformance table is incomplete or malformed."""


def split_table_cells(line: str) -> list[str]:
    """Split a Markdown pipe-table row, honoring backslash parity before pipes."""
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]

    cells: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(row):
        if row[index] == "\\":
            end = index
            while end < len(row) and row[end] == "\\":
                end += 1
            slash_count = end - index
            if end < len(row) and row[end] == "|" and slash_count % 2:
                current.extend("\\" for _ in range(slash_count - 1))
                current.append("|")
                index = end + 1
                continue
            current.extend("\\" for _ in range(slash_count))
            index = end
            continue
        if row[index] == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(row[index])
        index += 1
    cells.append("".join(current).strip())
    return cells


def parse_case_rows(markdown: str, prefix: str) -> list[tuple[str, str, str]]:
    """Return (case id, condition, assertion) tuples from pipe-table rows."""
    cases: list[tuple[str, str, str]] = []
    for line_number, line in enumerate(markdown.splitlines(), 1):
        if not line.lstrip().startswith("|"):
            continue
        cells = split_table_cells(line)
        if not cells:
            continue
        if cells[0].startswith(prefix + "-C") and not CASE_ID.fullmatch(cells[0]):
            raise SpecError(f"{prefix}: line {line_number}: malformed case ID {cells[0]!r}")
        if not CASE_ID.fullmatch(cells[0]):
            continue
        if not cells[0].startswith(prefix + "-"):
            raise SpecError(
                f"{prefix}: line {line_number}: case ID {cells[0]!r} belongs to another specification"
            )
        if len(cells) != 3:
            raise SpecError(f"{prefix}: line {line_number}: expected 3 table cells, got {len(cells)}")
        case_id, condition, assertion = cells
        if not condition or not assertion:
            raise SpecError(f"{prefix}: line {line_number}: condition and assertion must be non-empty")
        cases.append((case_id, condition, assertion))
    return cases


def validate_spec(markdown: str, prefix: str, expected_count: int) -> list[str]:
    """Validate uniqueness, contiguous numbering, and complete assertions."""
    cases = parse_case_rows(markdown, prefix)
    ids = [case[0] for case in cases]
    seen: set[str] = set()
    duplicates_set: set[str] = set()
    for case_id in ids:
        if case_id in seen:
            duplicates_set.add(case_id)
        seen.add(case_id)
    duplicates = sorted(duplicates_set)
    if duplicates:
        raise SpecError(f"{prefix}: duplicate case IDs: {', '.join(duplicates)}")
    expected = [f"{prefix}-C{number:02d}" for number in range(1, expected_count + 1)]
    missing = [case_id for case_id in expected if case_id not in ids]
    unexpected = [case_id for case_id in ids if case_id not in expected]
    if missing or unexpected or len(ids) != expected_count:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        details.append(f"expected {expected_count} rows, found {len(ids)}")
        raise SpecError(f"{prefix}: " + "; ".join(details))
    return ids


def validate_repository(root: Path) -> list[str]:
    results = []
    for prefix, (relative_path, expected_count) in SPECS.items():
        path = root / relative_path
        if not path.is_file():
            raise SpecError(f"{prefix}: specification not found: {relative_path}")
        ids = validate_spec(path.read_text(encoding="utf-8"), prefix, expected_count)
        results.append(f"{prefix}: {len(ids)} unique, contiguous cases validated ({relative_path})")
    return results


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2],
                        help="TuskerOS repository root (defaults to this script's repository)")
    parser.add_argument("--json", action="store_true",
                        help="emit a machine-readable result (success or failure) as JSON")
    args = parser.parse_args(argv)
    try:
        results = validate_repository(args.root)
    except (OSError, UnicodeError, SpecError) as exc:
        if args.json:
            print(json.dumps({
                "ok": False,
                "error": str(exc),
                "scope": "documentation-integrity-only",
                "runtime_security_tested": False,
            }, sort_keys=True))
        else:
            print(f"FAIL {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({
            "ok": True,
            "scope": "documentation-integrity-only",
            "runtime_security_tested": False,
            "specifications": [
                {"prefix": prefix, "path": relative_path, "case_count": expected_count}
                for prefix, (relative_path, expected_count) in SPECS.items()
            ],
        }, sort_keys=True))
    else:
        for result in results:
            print("PASS " + result)
        print("NOTE: documentation integrity only; no runtime security behavior was tested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
