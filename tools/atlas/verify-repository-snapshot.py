#!/usr/bin/env python3
"""Capture and verify immutable Fedora DNF repository metadata snapshots."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FEDORA_RELEASE = "44"
ARCHITECTURE = "x86_64"
MAX_DOWNLOAD = 512 * 1024 * 1024
USER_AGENT = "TuskerOS-ATLAS-repository-snapshot/1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_https(url: str) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError(f"repository metadata URL must use HTTPS: {url!r}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            final_url = response.geturl()
            if urllib.parse.urlparse(final_url).scheme != "https":
                raise RuntimeError(f"repository metadata redirect downgraded from HTTPS: {final_url}")
            data = response.read(MAX_DOWNLOAD + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(f"cannot fetch repository metadata {url}: {exc}") from exc
    if len(data) > MAX_DOWNLOAD:
        raise RuntimeError(f"repository metadata exceeds {MAX_DOWNLOAD} byte safety limit: {url}")
    return data


def parse_repomd(data: bytes) -> tuple[str, str, str, str]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise RuntimeError(f"repomd.xml is not valid XML: {exc}") from exc
    namespace = {"r": "http://linux.duke.edu/metadata/repo"}
    revision = root.findtext("r:revision", namespaces=namespace)
    primary = root.find("r:data[@type='primary']", namespace)
    if not revision or primary is None:
        raise RuntimeError("repomd.xml must contain a revision and primary metadata entry")
    location = primary.find("r:location", namespace)
    checksum = primary.find("r:checksum", namespace)
    if location is None or checksum is None:
        raise RuntimeError("repomd.xml primary entry is missing location or checksum")
    checksum_type = checksum.attrib.get("type", "").lower()
    checksum_value = (checksum.text or "").strip().lower()
    href = location.attrib.get("href", "")
    if checksum_type != "sha256" or len(checksum_value) != 64 or any(c not in "0123456789abcdef" for c in checksum_value):
        raise RuntimeError("repomd.xml primary checksum must be SHA-256")
    decoded_href = urllib.parse.unquote(href)
    parsed_href = urllib.parse.urlparse(href)
    if (
        not href or href.startswith("/") or href.startswith("//") or "\\" in href
        or parsed_href.scheme or parsed_href.netloc or parsed_href.query or parsed_href.fragment
        or ".." in Path(decoded_href).parts
    ):
        raise RuntimeError(f"unsafe primary metadata path in repomd.xml: {href!r}")
    return revision.strip(), href, checksum_value, checksum_type


def primary_metadata_url(repomd_url: str, href: str) -> str:
    # Fedora repomd.xml lives under repodata/, while href is relative to repo root.
    parsed_href = urllib.parse.urlparse(href)
    if href.startswith("//") or parsed_href.scheme or parsed_href.netloc:
        raise RuntimeError(f"primary metadata URL escaped its HTTPS repository origin: {href}")
    resolved = urllib.parse.urljoin(repomd_url, "../" + href)
    source = urllib.parse.urlparse(repomd_url)
    target = urllib.parse.urlparse(resolved)
    if target.scheme != "https" or target.netloc != source.netloc:
        raise RuntimeError(f"primary metadata URL escaped its HTTPS repository origin: {resolved}")
    return resolved


def capture_repository(repository_id: str, repomd_url: str) -> dict[str, str]:
    if not repository_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in repository_id):
        raise RuntimeError(f"invalid repository ID: {repository_id!r}")
    repomd = fetch_https(repomd_url)
    revision, primary_href, primary_sha256, _ = parse_repomd(repomd)
    primary_url = primary_metadata_url(repomd_url, primary_href)
    primary_data = fetch_https(primary_url)
    actual_primary_sha256 = sha256(primary_data)
    if actual_primary_sha256 != primary_sha256:
        raise RuntimeError(
            f"{repository_id}: downloaded primary metadata SHA-256 {actual_primary_sha256} "
            f"does not match repomd.xml {primary_sha256}"
        )
    repomd_sha256 = sha256(repomd)
    snapshot_id = f"fedora{FEDORA_RELEASE}/{repository_id}/{revision}/{repomd_sha256}"
    return {
        "repository_id": repository_id,
        "repomd_url": repomd_url,
        "repomd_sha256": repomd_sha256,
        "revision": revision,
        "primary_href": primary_href,
        "primary_sha256": primary_sha256,
        "snapshot_id": snapshot_id,
    }


def validate_lock(payload: object, *, require_repositories: bool = False) -> dict[str, dict[str, str]]:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RuntimeError("repository snapshot lock must be a schema_version 1 object")
    if payload.get("fedora_release") != FEDORA_RELEASE or payload.get("architecture") != ARCHITECTURE:
        raise RuntimeError("repository snapshot lock must target Fedora 44 x86_64")
    repositories = payload.get("repositories")
    if not isinstance(repositories, list):
        raise RuntimeError("repository snapshot lock repositories must be an array")
    if require_repositories and not repositories:
        raise RuntimeError("repository snapshot lock has no repositories; capture reviewed Fedora repositories first")
    indexed: dict[str, dict[str, str]] = {}
    for entry in repositories:
        if not isinstance(entry, dict):
            raise RuntimeError("repository snapshot entries must be objects")
        required = ("repository_id", "repomd_url", "repomd_sha256", "revision", "primary_href", "primary_sha256", "snapshot_id")
        if any(not isinstance(entry.get(key), str) or not entry[key].strip() for key in required):
            raise RuntimeError("repository snapshot entry is missing required string fields")
        repo_id = entry["repository_id"]
        if not repo_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in repo_id):
            raise RuntimeError(f"invalid repository ID in snapshot lock: {repo_id!r}")
        if repo_id in indexed:
            raise RuntimeError(f"duplicate repository snapshot ID: {repo_id}")
        for key in ("repomd_sha256", "primary_sha256"):
            digest = entry[key]
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
                raise RuntimeError(f"{repo_id}: {key} must be a SHA-256 hex digest")
        if not entry["repomd_url"].startswith("https://"):
            raise RuntimeError(f"{repo_id}: repomd_url must use HTTPS")
        expected_id = f"fedora{FEDORA_RELEASE}/{repo_id}/{entry['revision']}/{entry['repomd_sha256']}"
        if entry["snapshot_id"] != expected_id:
            raise RuntimeError(f"{repo_id}: snapshot_id does not match its revision and repomd digest")
        indexed[repo_id] = entry
    return indexed


def verify_lock(path: Path, *, require_repositories: bool = True) -> dict[str, dict[str, str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read repository snapshot lock {path}: {exc}") from exc
    indexed = validate_lock(payload, require_repositories=require_repositories)
    for repo_id, entry in indexed.items():
        repomd = fetch_https(entry["repomd_url"])
        actual_repomd_sha256 = sha256(repomd)
        if actual_repomd_sha256 != entry["repomd_sha256"]:
            raise RuntimeError(f"{repo_id}: repomd.xml SHA-256 changed: {actual_repomd_sha256}")
        revision, href, primary_sha256, _ = parse_repomd(repomd)
        if revision != entry["revision"] or href != entry["primary_href"] or primary_sha256 != entry["primary_sha256"]:
            raise RuntimeError(f"{repo_id}: repomd.xml revision or primary metadata identity changed")
        primary_url = primary_metadata_url(entry["repomd_url"], href)
        actual_primary_sha256 = sha256(fetch_https(primary_url))
        if actual_primary_sha256 != entry["primary_sha256"]:
            raise RuntimeError(f"{repo_id}: primary metadata SHA-256 changed: {actual_primary_sha256}")
    return indexed



def verify_manifest_snapshot_pins(manifest_path: Path, indexed: dict[str, dict[str, str]]) -> int:
    try:
        with manifest_path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(line for line in stream if line.strip() and not line.lstrip().startswith("#"))
            required = {"package", "repository_id", "repository_snapshot"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise RuntimeError("package manifest is missing repository snapshot columns")
            rows = list(reader)
    except OSError as exc:
        raise RuntimeError(f"cannot read package manifest {manifest_path}: {exc}") from exc
    if not rows:
        raise RuntimeError("package manifest has no rows; owner-reviewed RPM dependencies are required")
    for row in rows:
        package = (row.get("package") or "").strip()
        repo_id = (row.get("repository_id") or "").strip()
        snapshot_id = (row.get("repository_snapshot") or "").strip()
        if not package or repo_id not in indexed:
            raise RuntimeError(f"{package or '<unnamed package>'}: repository {repo_id!r} has no verified snapshot")
        if snapshot_id != indexed[repo_id]["snapshot_id"]:
            raise RuntimeError(
                f"{package}: repository_snapshot {snapshot_id!r} does not match verified "
                f"snapshot {indexed[repo_id]['snapshot_id']!r} for {repo_id}"
            )
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("os/repository-snapshot.lock.json"))
    parser.add_argument("--validate-only", action="store_true", help="validate lock structure without network access")
    parser.add_argument("--manifest", type=Path, help="also require every package row to reference its exact verified repository snapshot")
    parser.add_argument("--capture", action="append", default=[], metavar="REPO_ID=REPOMD_URL",
                        help="capture one repository's repomd.xml and primary metadata identity")
    args = parser.parse_args()
    if args.capture:
        entries = []
        for item in args.capture:
            if "=" not in item:
                raise RuntimeError("--capture values must be REPO_ID=REPOMD_URL")
            repo_id, url = item.split("=", 1)
            entries.append(capture_repository(repo_id, url))
        payload = {
            "schema_version": 1,
            "fedora_release": FEDORA_RELEASE,
            "architecture": ARCHITECTURE,
            "repositories": entries,
            "verification": "SHA-256 identity of repomd.xml and its primary metadata; HTTPS transport used during capture",
            "signature_verification": "not_performed",
        }
        validate_lock(payload, require_repositories=True)
        args.lock.parent.mkdir(parents=True, exist_ok=True)
        args.lock.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Captured {len(entries)} repository snapshot(s) to {args.lock}")
        return 0
    if args.validate_only:
        payload = json.loads(args.lock.read_text(encoding="utf-8"))
        indexed = validate_lock(payload)
        print(f"Validated repository snapshot lock structure: {len(indexed)} repository entries")
        return 0
    indexed = verify_lock(args.lock)
    package_count = verify_manifest_snapshot_pins(args.manifest, indexed) if args.manifest else None
    suffix = f" and {package_count} package snapshot pins" if package_count is not None else ""
    print(f"Verified immutable repomd.xml and primary metadata for {len(indexed)} Fedora 44 repositories{suffix}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        print(f"atlas-repository-snapshot: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
