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
CASE_ID = re.compile(r"^(PAIR|SESS|NET)-C([0-9]{2})$")


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


def _iter_table_rows(markdown: str) -> Iterable[tuple[int, str]]:
    """Yield pipe-table rows outside fenced and indented Markdown code blocks."""
    fence_char: str | None = None
    fence_size = 0
    for line_number, line in enumerate(markdown.splitlines(), 1):
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)

        if fence_char is not None:
            if indent <= 3 and stripped:
                marker = stripped[0]
                run = len(stripped) - len(stripped.lstrip(marker)) if marker in "`~" else 0
                if marker == fence_char and run >= fence_size and not stripped[run:].strip():
                    fence_char = None
                    fence_size = 0
            continue

        # CommonMark indented code blocks must not contribute example rows.
        if indent >= 4 or line.startswith("\\t"):
            continue

        if indent <= 3 and stripped and stripped[0] in "`~":
            marker = stripped[0]
            run = len(stripped) - len(stripped.lstrip(marker))
            info = stripped[run:]
            if run >= 3 and (marker != "`" or "`" not in info):
                fence_char = marker
                fence_size = run
                continue

        if line.lstrip().startswith("|"):
            yield line_number, line


def parse_case_rows(markdown: str, prefix: str) -> list[tuple[str, str, str]]:
    """Return (case id, condition, assertion) tuples from pipe-table rows."""
    cases: list[tuple[str, str, str]] = []
    for line_number, line in _iter_table_rows(markdown):
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
    lines_by_id: dict[str, list[int]] = {}
    for line_number, line in _iter_table_rows(markdown):
        cells = split_table_cells(line)
        if cells and CASE_ID.fullmatch(cells[0]) and cells[0].startswith(prefix + "-"):
            lines_by_id.setdefault(cells[0], []).append(line_number)
    duplicates = sorted(case_id for case_id, lines in lines_by_id.items() if len(lines) > 1)
    if duplicates:
        details = [
            f"{case_id} (lines {', '.join(str(line) for line in lines_by_id[case_id])})"
            for case_id in duplicates
        ]
        raise SpecError(f"{prefix}: duplicate case IDs: {', '.join(details)}")
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
    """Validate every specification and report all independent failures together."""
    results = []
    errors = []
    for prefix, (relative_path, expected_count) in SPECS.items():
        path = root / relative_path
        try:
            if not path.is_file():
                raise SpecError(f"specification not found: {relative_path}")
            ids = validate_spec(path.read_text(encoding="utf-8"), prefix, expected_count)
        except (OSError, UnicodeError, SpecError) as exc:
            detail = str(exc)
            if not detail.startswith(prefix + ":"):
                detail = f"{prefix}: {detail}"
            errors.append(detail)
            continue
        results.append(f"{prefix}: {len(ids)} unique, contiguous cases validated ({relative_path})")
    if errors:
        raise SpecError("repository validation failed: " + " | ".join(errors))
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
