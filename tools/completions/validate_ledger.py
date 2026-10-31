#!/usr/bin/env python3
"""Validate TuskerOS append-only response completion JSONL ledgers."""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

AGENT_BRANCHES = {
    "ATLAS-01": "agent/01-fedora-base",
    "NOVA-02": "agent/02-desktop-shell",
    "PIXEL-03": "agent/03-theme-studio",
    "TUSKER-04": "agent/04-tusker-core",
    "ORBIT-05": "agent/05-ai-runtime",
    "AEGIS-06": "agent/06-security-gatekeeper",
    "NEXUS-07": "agent/07-system-integration",
    "PILOT-08": "agent/08-remote-control",
    "FORGE-09": "agent/09-ecosystem",
    "PHOENIX-10": "agent/10-installer-recovery",
    # Coordinator responses are tracked separately from the ten specialist agents.
    "COORDINATOR": "main",
}
REQUIRED = {
    "completion_id", "response_id", "agent_id", "branch",
    "response_summary", "evidence_refs", "recorded_at_utc", "record_version",
}


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_responses: set[tuple[str, str]] = set()
    next_sequence = {agent: 1 for agent in AGENT_BRANCHES}

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read {path}: {exc}"]

    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            errors.append(f"line {line_number}: blank lines are not allowed")
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(record, dict):
            errors.append(f"line {line_number}: record must be a JSON object")
            continue

        missing = REQUIRED - record.keys()
        if missing:
            errors.append(f"line {line_number}: missing fields: {', '.join(sorted(missing))}")
            continue
        agent = record["agent_id"]
        if agent not in AGENT_BRANCHES:
            errors.append(f"line {line_number}: unknown agent_id {agent!r}")
            continue
        if record["branch"] != AGENT_BRANCHES[agent]:
            errors.append(f"line {line_number}: branch does not match {agent}")
        expected = f"{agent}-{next_sequence[agent]:06d}"
        if record["completion_id"] != expected:
            errors.append(f"line {line_number}: expected completion_id {expected}")
        next_sequence[agent] += 1

        completion_id = record["completion_id"]
        if completion_id in seen_ids:
            errors.append(f"line {line_number}: duplicate completion_id {completion_id}")
        seen_ids.add(completion_id)

        response_id = record["response_id"]
        try:
            uuid.UUID(response_id)
        except (ValueError, TypeError, AttributeError):
            errors.append(f"line {line_number}: response_id must be a UUID")
        pair = (agent, str(response_id))
        if pair in seen_responses:
            errors.append(f"line {line_number}: duplicate response_id for {agent}")
        seen_responses.add(pair)

        if not isinstance(record["response_summary"], str) or not record["response_summary"].strip():
            errors.append(f"line {line_number}: response_summary must be non-empty")
        refs = record["evidence_refs"]
        if not isinstance(refs, list) or not refs or not all(isinstance(x, str) and x.strip() for x in refs):
            errors.append(f"line {line_number}: evidence_refs must be a non-empty string list")
        if record["record_version"] != 1:
            errors.append(f"line {line_number}: unsupported record_version")

        stamp = record["recorded_at_utc"]
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            errors.append(f"line {line_number}: recorded_at_utc must be an ISO-8601 UTC timestamp ending in Z or +00:00")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_ledger.py PATH", file=sys.stderr)
        return 2
    errors = validate(Path(sys.argv[1]))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"valid response completion ledger: {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
