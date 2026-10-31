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
import tempfile
from pathlib import Path

EXPECTED_RELEASE = "44"
EXPECTED_ARCH = "x86_64"
REQUIRED_COLUMNS = {"layer", "package", "owner", "required", "rationale"}
PINNED_COLUMNS = {"pinned_nevra", "repository_id", "repository_snapshot", "rpm_license", "source_rpm", "source_repository_url", "upstream_url"}
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SOURCE_RPM_RE = re.compile(r"^[A-Za-z0-9+_.:-]+\.src\.rpm$")
PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+_.:-]*$")
QUERY_FORMAT = "%{full_nevra}\t%{repoid}\t%{license}\t%{sourcerpm}\t%{url}"


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    """Write JSON beside the destination, then atomically replace it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(payload, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


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


def read_manifest(path: Path, *, require_pins: bool = False) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        lines = (line for line in stream if line.strip() and not line.lstrip().startswith("#"))
        reader = csv.DictReader(lines)
        if (
            not reader.fieldnames
            or any(not name or not name.strip() for name in reader.fieldnames)
            or len(reader.fieldnames) != len(set(reader.fieldnames))
            or not REQUIRED_COLUMNS.issubset(reader.fieldnames)
            or (require_pins and not PINNED_COLUMNS.issubset(reader.fieldnames))
        ):
            raise RuntimeError(
                f"Manifest header must contain unique, non-empty columns including: "
                f"{', '.join(sorted(REQUIRED_COLUMNS))}"
            )
        rows = list(reader)
    if not rows:
        raise RuntimeError("Manifest contains no package rows; obtain owner-reviewed package names first.")
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if None in row:
            raise RuntimeError(f"Manifest row has more fields than its header: {row!r}")
        missing = [column for column in REQUIRED_COLUMNS if row.get(column) is None]
        if missing:
            raise RuntimeError(f"Manifest row is missing values for: {', '.join(sorted(missing))}")
        package = (row.get("package") or "").strip()
        layer = (row.get("layer") or "").strip()
        if not layer or not PACKAGE_RE.fullmatch(package):
            raise RuntimeError(f"Invalid layer/package row: {row!r}")
        if row.get("required", "").strip().lower() not in {"true", "false"}:
            raise RuntimeError(f"required must be true or false: {row!r}")
        if not (row.get("owner") or "").strip():
            raise RuntimeError(f"owner must be non-empty: {row!r}")
        if not (row.get("rationale") or "").strip():
            raise RuntimeError(f"rationale must be non-empty: {row!r}")
        if require_pins:
            pin = (row.get("pinned_nevra") or "").strip()
            suffix = pin[len(package) + 1:] if pin.startswith(f"{package}-") else ""
            if not re.match(r"^[0-9]+:.+\.(?:x86_64|noarch)$", suffix):
                raise RuntimeError(f"pinned_nevra must pin {package} to epoch/version/release and supported arch: {pin!r}")
            repository_id = (row.get("repository_id") or "").strip()
            if not REPOSITORY_RE.fullmatch(repository_id):
                raise RuntimeError(f"repository_id is invalid: {repository_id!r}")
            for column in ("repository_snapshot", "rpm_license", "source_rpm", "source_repository_url", "upstream_url"):
                if not (row.get(column) or "").strip():
                    raise RuntimeError(f"{column} must be non-empty for pinned package {package}")
            if not SOURCE_RPM_RE.fullmatch(row["source_rpm"].strip()):
                raise RuntimeError("source_rpm must be an RPM source package filename")
            source_repository_url = row["source_repository_url"].strip()
            if not source_repository_url.startswith("https://src.fedoraproject.org/rpms/"):
                raise RuntimeError("source_repository_url must be a Fedora dist-git HTTPS URL")
            upstream_url = row["upstream_url"].strip()
            if upstream_url != "NOASSERTION" and not upstream_url.startswith("https://"):
                raise RuntimeError("upstream_url must be HTTPS or the explicit NOASSERTION sentinel")
        key = (layer, package)
        if key in seen:
            raise RuntimeError(f"Duplicate package in layer: {layer}/{package}")
        seen.add(key)
        row["package"] = package
        row["layer"] = layer
    return rows


def parse_query_matches(
    output: str, expected_package: str | None = None
) -> tuple[str, str, str, str, str]:
    """Return one unambiguous NEVRA/repository/license/source-RPM/upstream-URL tuple."""
    # Preserve a trailing tab: an RPM with no upstream URL has an empty
    # fifth field, which is normalized to the explicit NOASSERTION sentinel.
    matches = {line.rstrip("\r\n") for line in output.splitlines() if line.strip()}
    if not matches:
        raise RuntimeError("no available match")
    parsed: set[tuple[str, str, str, str, str]] = set()
    for match in matches:
        fields = match.split("\t")
        if len(fields) != 5 or not all(field.strip() for field in fields[:4]):
            raise RuntimeError(f"unexpected DNF5 query output row: {match!r}")
        nevra, repository, license_expression, source_rpm, upstream_url = (field.strip() for field in fields)
        if upstream_url in {"", "(none)", "None"}:
            upstream_url = "NOASSERTION"
        if not nevra.endswith((".x86_64", ".noarch")):
            raise RuntimeError(f"DNF5 returned unsupported architecture in NEVRA: {nevra!r}")
        if expected_package is not None and not re.match(
            r"^" + re.escape(expected_package) + r"-[0-9]+:", nevra
        ):
            raise RuntimeError(
                f"DNF5 returned package outside requested name or malformed NEVRA "
                f"for {expected_package!r}: {nevra!r}"
            )
        if not SOURCE_RPM_RE.fullmatch(source_rpm):
            raise RuntimeError(f"DNF5 returned invalid source RPM metadata: {source_rpm!r}")
        if upstream_url != "NOASSERTION" and not upstream_url.startswith("https://"):
            raise RuntimeError(f"DNF5 returned a non-HTTPS upstream URL: {upstream_url!r}")
        parsed.add((nevra, repository, license_expression, source_rpm, upstream_url))
    nevras = {item[0] for item in parsed}
    repositories = {item[1] for item in parsed}
    if len(nevras) != 1:
        raise RuntimeError(f"ambiguous NEVRA results: {', '.join(sorted(nevras))}")
    if len(repositories) != 1:
        raise RuntimeError(
            f"ambiguous repository results for {next(iter(nevras))}: "
            f"{', '.join(sorted(repositories))}"
        )
    if len(parsed) != 1:
        raise RuntimeError(f"conflicting package provenance metadata for {next(iter(nevras))}")
    return next(iter(parsed))


def verify_pin(
    row: dict[str, str],
    actual_nevra: str,
    actual_repository: str,
    actual_license: str,
    actual_source_rpm: str,
    actual_upstream_url: str,
) -> None:
    expected = {
        "pinned_nevra": actual_nevra,
        "repository_id": actual_repository,
        "rpm_license": actual_license,
        "source_rpm": actual_source_rpm,
        "upstream_url": actual_upstream_url,
    }
    for field, actual in expected.items():
        pinned = row[field].strip()
        if actual != pinned:
            raise RuntimeError(f"resolved {field} {actual!r} does not match pinned value {pinned!r}")


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

    rows = read_manifest(args.manifest, require_pins=True)
    repo_evidence = run(["dnf5", "repo", "info"])
    resolved: list[dict[str, str]] = []
    failures: list[str] = []

    for row in rows:
        output = run([
            "dnf5", "repoquery", "--available", "--arch=x86_64,noarch",
            "--latest-limit=1", "--qf", QUERY_FORMAT, row["pinned_nevra"].strip()
        ])
        try:
            nevra, repo_id, rpm_license, source_rpm, upstream_url = parse_query_matches(output, row["package"])
            verify_pin(row, nevra, repo_id, rpm_license, source_rpm, upstream_url)
        except RuntimeError as exc:
            failures.append(f"{row['layer']}/{row['package']}: {exc}")
            continue
        resolved.append({
            "layer": row["layer"],
            "package": row["package"],
            "owner": row["owner"].strip(),
            "required": row["required"].strip().lower() == "true",
            "rationale": row["rationale"].strip(),
            "nevra": nevra,
            "repository_id": repo_id,
            "pinned_nevra": row["pinned_nevra"].strip(),
            "repository_snapshot": row["repository_snapshot"].strip(),
            "rpm_license": rpm_license,
            "source_rpm": source_rpm,
            "source_repository_url": row["source_repository_url"].strip(),
            "upstream_url": upstream_url,
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
    write_json_atomic(args.output, result)
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
