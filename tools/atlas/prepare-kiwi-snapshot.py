#!/usr/bin/env python3
"""Create a pinned KIWI source overlay that uses verified local RPM-MD snapshots."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path


def prepare_overlay(description_root: Path, snapshot_root: Path, lock_path: Path) -> dict[str, str]:
    root = description_root.resolve(strict=True)
    snapshots = snapshot_root.resolve(strict=True)
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or payload.get("fedora_release") != "44" or payload.get("architecture") != "x86_64":
        raise RuntimeError("repository snapshot lock must target Fedora 44 x86_64 schema version 1")
    entries = payload.get("repositories")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("repository snapshot lock has no repositories")
    expected_ids = {entry.get("repository_id") for entry in entries if isinstance(entry, dict)}
    if len(expected_ids) != len(entries) or not all(isinstance(item, str) and item for item in expected_ids):
        raise RuntimeError("repository snapshot lock has invalid or duplicate repository IDs")

    description = root / "Fedora.kiwi"
    if not description.is_file() or 'this://./repositories/core.xml' not in description.read_text(encoding="utf-8"):
        raise RuntimeError("pinned Fedora.kiwi does not contain the expected repositories/core.xml include")
    try:
        core_file = (root / "repositories" / "core.xml").resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"cannot resolve pinned repositories/core.xml include: {exc}") from exc
    if not core_file.is_relative_to(root):
        raise RuntimeError("repositories/core.xml resolves outside the pinned KIWI source tree")

    try:
        tree = ET.parse(core_file)
    except ET.ParseError as exc:
        raise RuntimeError(f"pinned Fedora core repository XML is invalid: {exc}") from exc
    repositories = tree.getroot().findall("repository")
    indexed: dict[str, ET.Element] = {}
    for repository in repositories:
        alias = repository.attrib.get("alias", "")
        if not alias or alias in indexed:
            raise RuntimeError(f"pinned Fedora repository XML has an empty or duplicate alias: {alias!r}")
        indexed[alias] = repository
    if set(indexed) != expected_ids:
        raise RuntimeError(
            "repository lock IDs do not exactly match pinned Fedora KIWI repository aliases: "
            f"lock={sorted(expected_ids)}, KIWI={sorted(indexed)}"
        )

    output: dict[str, str] = {}
    for repository_id, repository in indexed.items():
        if repository.attrib.get("type") != "rpm-md":
            raise RuntimeError(f"{repository_id}: pinned KIWI repository is not rpm-md")
        sources = repository.findall("source")
        if len(sources) != 1:
            raise RuntimeError(f"{repository_id}: expected exactly one source element")
        source = sources[0]
        signing = source.find("signing")
        if signing is None or not signing.attrib.get("key", "").startswith("file://"):
            raise RuntimeError(f"{repository_id}: Fedora RPM signing-key reference is missing")
        signing_key_url = urllib.parse.urlparse(signing.attrib["key"])
        signing_key_path = Path(urllib.parse.unquote(signing_key_url.path).replace("$releasever", "44"))
        if not signing_key_path.is_file():
            raise RuntimeError(f"{repository_id}: Fedora RPM signing key is not installed: {signing_key_path}")
        signing.set("key", signing_key_path.as_uri())
        repository.set("repository_gpgcheck", "true")
        repository.set("package_gpgcheck", "true")
        repository_path = (snapshots / repository_id).resolve(strict=True)
        if not repository_path.is_relative_to(snapshots):
            raise RuntimeError(f"{repository_id}: local repository path escapes snapshot root")
        if not (repository_path / "repodata" / "repomd.xml").is_file():
            raise RuntimeError(f"{repository_id}: local snapshot lacks repodata/repomd.xml")
        source.set("path", repository_path.as_uri())
        source.attrib.pop("sourcetype", None)
        output[repository_id] = repository_path.as_uri()

    tree.write(core_file, encoding="utf-8", xml_declaration=True)
    verified = ET.parse(core_file).getroot()
    for repository in verified.findall("repository"):
        source = repository.find("source")
        if source is None or not source.attrib.get("path", "").startswith("file://"):
            raise RuntimeError(f"{repository.attrib.get('alias')}: generated KIWI overlay still has a non-local source")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--description-root", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    args = parser.parse_args()
    paths = prepare_overlay(args.description_root, args.snapshot_root, args.lock)
    for repository_id, uri in sorted(paths.items()):
        print(f"KIWI repository {repository_id}: {uri}")
    print(f"Prepared local-only KIWI source overlay with {len(paths)} repositories")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, ET.ParseError) as exc:
        print(f"atlas-kiwi-snapshot: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
