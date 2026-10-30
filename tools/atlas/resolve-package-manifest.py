#!/usr/bin/env python3
"""Resolve an ATLAS package CSV against Fedora 44 DNF5 metadata without installing anything."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

EXPECTED_RELEASE = "44"
EXPECTED_ARCH = "x86_64"
REQUIRED_COLUMNS = {"layer", "package", "owner", "required", "rationale"}
PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+_.:-]*$")
QUERY_FORMAT = "%{name}-%{epoch}:%{version}-%{release}.%{arch}\t%{repoid}"


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def fedora_release() -> str:
    values: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
    except OSError as exc:
        raise RuntimeError(f"Cannot read /etc/os-release: {exc}") from exc
    if values.get("ID") != "fedora":
        raise RuntimeError(f"Expected Fedora host; found ID={values.get('ID')!r}")
    return values.get("VERSION_ID", "")


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        lines = (line for line in stream if line.strip() and not line.lstrip().startswith("#"))
        reader = csv.DictReader(lines)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise RuntimeError(f"Manifest header must contain: {', '.join(sorted(REQUIRED_COLUMNS))}")
        rows = list(reader)
    if not rows:
        raise RuntimeError("Manifest contains no package rows; obtain owner-reviewed package names first.")
    seen: set[tuple[str, str]] = set()
    for row in rows:
        package = (row.get("package") or "").strip()
        layer = (row.get("layer") or "").strip()
        if not layer or not PACKAGE_RE.fullmatch(package):
            raise RuntimeError(f"Invalid layer/package row: {row!r}")
        if row.get("required", "").strip().lower() not in {"true", "false"}:
            raise RuntimeError(f"required must be true or false: {row!r}")
        key = (layer, package)
        if key in seen:
            raise RuntimeError(f"Duplicate package in layer: {layer}/{package}")
        seen.add(key)
        row["package"] = package
        row["layer"] = layer
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("os/package-manifest.csv"))
    parser.add_argument("--output", type=Path, default=Path("build/package-resolution.json"))
    args = parser.parse_args()

    release = fedora_release()
    arch = platform.machine()
    if release != EXPECTED_RELEASE or arch != EXPECTED_ARCH:
        raise RuntimeError(
            f"Expected Fedora {EXPECTED_RELEASE} {EXPECTED_ARCH}; found Fedora {release} {arch}"
        )
    if not shutil_which("dnf5"):
        raise RuntimeError("dnf5 is required; install/use the Fedora 44 DNF5 client.")

    rows = read_manifest(args.manifest)
    repo_evidence = run(["dnf5", "repo", "info"])
    resolved: list[dict[str, str]] = []
    failures: list[str] = []

    for row in rows:
        output = run([
            "dnf5", "repoquery", "--available", "--arch=x86_64,noarch",
            "--latest-limit=1", "--qf", QUERY_FORMAT, row["package"]
        ])
        matches = sorted({line.strip() for line in output.splitlines() if line.strip()})
        if not matches:
            failures.append(f"{row['layer']}/{row['package']}: no available match")
            continue
        nevras = {match.split("\t", 1)[0] for match in matches}
        if len(nevras) != 1:
            failures.append(
                f"{row['layer']}/{row['package']}: ambiguous NEVRA results: {', '.join(sorted(nevras))}"
            )
            continue
        for match in matches:
            nevra, repo_id = match.split("\t", 1)
            resolved.append({
                "layer": row["layer"],
                "package": row["package"],
                "owner": row["owner"],
                "required": row["required"].strip().lower() == "true",
                "rationale": row["rationale"],
                "nevra": nevra,
                "repository_id": repo_id,
            })

    if failures:
        raise RuntimeError("Package resolution failed:\n- " + "\n- ".join(failures))

    result = {
        "schema_version": 1,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fedora_release": release,
        "architecture": arch,
        "manifest_path": str(args.manifest),
        "manifest_sha256": __import__("hashlib").sha256(args.manifest.read_bytes()).hexdigest(),
        "dnf5_version": run(["dnf5", "--version"]).splitlines()[0],
        "enabled_repository_evidence": repo_evidence,
        "packages": resolved,
        "note": "Repository evidence is captured, but this file does not snapshot repository metadata or RPM payloads.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Resolved {len(resolved)} package/repository records to {args.output}")
    return 0


def shutil_which(command: str) -> str | None:
    from shutil import which
    return which(command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"atlas-package-resolver: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
