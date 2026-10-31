#!/usr/bin/env python3
"""Validate semantic invariants in a TuskerOS release validation report.

JSON Schema validation and evidence-byte verification are deliberately separate
stages. This tool uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
STATUSES = {"passed", "failed", "blocked", "not_run"}
OVERALL = {"passed", "failed", "blocked", "incomplete"}


def parse_utc(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(f"{field}: expected an RFC 3339 UTC timestamp ending in Z")
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        errors.append(f"{field}: invalid RFC 3339 timestamp")
        return None
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        errors.append(f"{field}: timestamp is not UTC")
        return None
    return parsed


def validate_report(report: Any, expected_manifest_digest: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report: expected a JSON object"]

    subject = report.get("subject")
    if not isinstance(subject, dict):
        return ["subject: expected an object"]
    digest = subject.get("manifest_sha256")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        errors.append("subject.manifest_sha256: expected 64 lowercase hexadecimal characters")
    if expected_manifest_digest is not None:
        if not DIGEST_RE.fullmatch(expected_manifest_digest):
            errors.append("--expected-manifest-digest: expected 64 lowercase hexadecimal characters")
        elif digest != expected_manifest_digest:
            errors.append("subject.manifest_sha256: does not match the expected manifest digest")

    started = parse_utc(report.get("started_at_utc"), "started_at_utc", errors)
    finished = parse_utc(report.get("finished_at_utc"), "finished_at_utc", errors)
    if started is not None and finished is not None and finished < started:
        errors.append("finished_at_utc: precedes started_at_utc")

    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("checks: expected a non-empty array")
        checks = []

    ids: set[str] = set()
    counts: Counter[str] = Counter()
    for index, check in enumerate(checks):
        prefix = f"checks[{index}]"
        if not isinstance(check, dict):
            errors.append(f"{prefix}: expected an object")
            continue
        check_id = check.get("check_id")
        if not isinstance(check_id, str) or not check_id:
            errors.append(f"{prefix}.check_id: expected a non-empty string")
        elif check_id in ids:
            errors.append(f"{prefix}.check_id: duplicate value {check_id!r}")
        else:
            ids.add(check_id)

        status = check.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f"{prefix}.status: unsupported value")
        else:
            counts[status] += 1

        if check.get("subject_digest") != digest:
            errors.append(f"{prefix}.subject_digest: does not match report manifest digest")

        check_started = check.get("started_at_utc")
        check_finished = check.get("finished_at_utc")
        parsed_check_started = None
        parsed_check_finished = None
        if check_started is not None:
            parsed_check_started = parse_utc(check_started, f"{prefix}.started_at_utc", errors)
        if check_finished is not None:
            parsed_check_finished = parse_utc(check_finished, f"{prefix}.finished_at_utc", errors)
        if parsed_check_started and parsed_check_finished and parsed_check_finished < parsed_check_started:
            errors.append(f"{prefix}: finished_at_utc precedes started_at_utc")
        if started and parsed_check_started and parsed_check_started < started:
            errors.append(f"{prefix}.started_at_utc: outside report interval")
        if finished and parsed_check_finished and parsed_check_finished > finished:
            errors.append(f"{prefix}.finished_at_utc: outside report interval")

    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary: expected an object")
        summary = {}
    expected_counts = {
        "total": len(checks),
        "passed": counts["passed"],
        "failed": counts["failed"],
        "blocked": counts["blocked"],
        "not_run": counts["not_run"],
    }
    for key, expected in expected_counts.items():
        if summary.get(key) != expected or isinstance(summary.get(key), bool):
            errors.append(f"summary.{key}: expected {expected}")

    if counts["failed"]:
        derived = "failed"
    elif counts["blocked"]:
        derived = "blocked"
    elif counts["not_run"]:
        derived = "incomplete"
    else:
        derived = "passed"
    overall_status = report.get("overall_status")
    if not isinstance(overall_status, str) or overall_status not in OVERALL or overall_status != derived:
        errors.append(f"overall_status: expected {derived}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="path to a validation report JSON file")
    parser.add_argument("--expected-manifest-digest", help="optional SHA-256 of the manifest being checked")
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"cannot read report: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 2

    errors = validate_report(report, args.expected_manifest_digest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAILED: {len(errors)} semantic error(s)", file=sys.stderr)
        return 1
    print("PASS: release validation report semantic invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
