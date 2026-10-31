#!/usr/bin/env python3
"""Validate the repository's minimal Plasma 6 applet package without KDE runtime deps."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def validate(package: Path) -> list[str]:
    errors: list[str] = []
    metadata_path = package / "metadata.json"
    qml_path = package / "contents" / "ui" / "main.qml"

    if not metadata_path.is_file():
        return [f"missing package metadata: {metadata_path}"]
    if not qml_path.is_file():
        errors.append(f"missing applet entry point: {qml_path}")
        return errors

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"invalid metadata JSON: {exc}"]

    plugin = metadata.get("KPlugin")
    if not isinstance(plugin, dict):
        errors.append("metadata must contain a KPlugin object")
        plugin = {}

    for field in ("Id", "Name", "Version", "License"):
        if not isinstance(plugin.get(field), str) or not plugin[field].strip():
            errors.append(f"KPlugin.{field} must be a non-empty string")

    if metadata.get("KPackageStructure") != "Plasma/Applet":
        errors.append('KPackageStructure must equal "Plasma/Applet"')

    minimum = metadata.get("X-Plasma-API-Minimum-Version")
    if not isinstance(minimum, str) or not minimum.startswith("6."):
        errors.append('X-Plasma-API-Minimum-Version must target Plasma 6 (for example "6.0")')

    try:
        qml = qml_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read QML entry point: {exc}")
        return errors

    if "PlasmoidItem" not in qml:
        errors.append("Plasma 6 QML entry point must declare PlasmoidItem")
    if "import QtQuick" not in qml:
        errors.append("QML entry point must import QtQuick")
    if "import org.kde.plasma.components" not in qml:
        errors.append("QML entry point must import Plasma Components")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="Path to the Plasma applet package directory")
    args = parser.parse_args()
    errors = validate(args.package)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: Plasma 6 applet package structure validated: {args.package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
