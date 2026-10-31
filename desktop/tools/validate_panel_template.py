#!/usr/bin/env python3
"""Statically validate the optional TuskerOS Plasma panel layout template."""

from __future__ import annotations

import argparse
import configparser
import sys
from pathlib import Path


def validate(template: Path) -> list[str]:
    errors: list[str] = []
    metadata_path = template / "metadata.desktop"
    script_path = template / "contents" / "layout.js"

    if not metadata_path.is_file():
        return [f"missing template metadata: {metadata_path}"]
    if not script_path.is_file():
        errors.append(f"missing layout script: {script_path}")
        return errors

    metadata = configparser.ConfigParser(interpolation=None, strict=True)
    try:
        with metadata_path.open(encoding="utf-8") as stream:
            metadata.read_file(stream)
    except (OSError, UnicodeError, configparser.Error) as exc:
        return [f"invalid desktop metadata: {exc}"]

    entry = metadata["Desktop Entry"] if metadata.has_section("Desktop Entry") else {}
    required = ("Name", "Type", "X-KDE-ServiceTypes", "X-KDE-PluginInfo-Name", "X-KDE-PluginInfo-Version")
    for field in required:
        if not entry.get(field, "").strip():
            errors.append(f"Desktop Entry.{field} must be a non-empty value")

    if entry.get("Type") != "Service":
        errors.append('Desktop Entry.Type must equal "Service"')
    if entry.get("X-KDE-ServiceTypes") != "Plasma/LayoutTemplate":
        errors.append('Desktop Entry.X-KDE-ServiceTypes must equal "Plasma/LayoutTemplate"')
    if entry.get("X-Plasma-API") != "javascript":
        errors.append('Desktop Entry.X-Plasma-API must equal "javascript"')

    try:
        script = script_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read layout script: {exc}")
        return errors

    required_fragments = (
        "new plasma.Panel()",
        'dock.addWidget("org.kde.plasma.kickoff")',
        'dock.addWidget("org.kde.plasma.icontasks")',
        'dock.location = "bottom"',
    )
    for fragment in required_fragments:
        if fragment not in script:
            errors.append(f"layout script is missing required behavior: {fragment}")

    forbidden_fragments = ("removePanel(", "deletePanel(", "clearConfig(")
    for fragment in forbidden_fragments:
        if fragment in script:
            errors.append(f"layout script contains destructive operation: {fragment}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path, help="Path to the Plasma layout-template directory")
    args = parser.parse_args()
    errors = validate(args.template)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: Plasma panel template structure validated: {args.template}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
