#!/usr/bin/env python3
"""Safely install or remove the optional TuskerOS Plasma dock template."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

PLUGIN_ID = "com.tuskeros.desktop.dock"
MARKER = ".tuskeros-managed"
MARKER_CONTENT = "TuskerOS managed Plasma layout template; safe to remove with this installer.\n"
MAX_SOURCE_FILES = 256
MAX_SOURCE_BYTES = 8 * 1024 * 1024


def default_destination() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return data_home / "plasma" / "layout-templates" / PLUGIN_ID


def _validate_source_entry(path: Path, totals: list[int]) -> None:
    """Reject links/special files and bound the amount of data copied."""
    try:
        info = path.lstat()
        mode = info.st_mode
    except OSError as exc:
        raise ValueError(f"cannot inspect panel template source entry: {path}: {exc}") from exc

    if stat.S_ISDIR(mode):
        try:
            children = sorted(path.iterdir(), key=lambda child: child.name)
        except OSError as exc:
            raise ValueError(f"cannot read panel template source directory: {path}: {exc}") from exc
        for child in children:
            _validate_source_entry(child, totals)
        return

    if not stat.S_ISREG(mode):
        raise ValueError(f"panel template source contains a symlink or special file: {path}")

    totals[0] += 1
    totals[1] += info.st_size
    if totals[0] > MAX_SOURCE_FILES:
        raise ValueError(f"panel template source exceeds {MAX_SOURCE_FILES} files")
    if totals[1] > MAX_SOURCE_BYTES:
        raise ValueError(f"panel template source exceeds {MAX_SOURCE_BYTES} bytes")


def install(source: Path, destination: Path) -> None:
    source = source.resolve()
    metadata = source / "metadata.desktop"
    contents = source / "contents"
    totals = [0, 0]
    _validate_source_entry(metadata, totals)
    _validate_source_entry(contents, totals)
    if destination.is_symlink():
        raise FileExistsError(f"refusing symlink destination: {destination}")
    if destination.exists():
        raise FileExistsError(f"destination already exists; refusing to overwrite: {destination}")

    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging: Path | None = None
    try:
        staging = Path(tempfile.mkdtemp(prefix=".tusker-dock-staging-", dir=parent))
        shutil.copy2(metadata, staging / "metadata.desktop")
        shutil.copytree(contents, staging / "contents")
        (staging / MARKER).write_text(MARKER_CONTENT, encoding="utf-8")
        # Destination is required not to exist; rename publishes the complete tree atomically.
        os.replace(staging, destination)
        staging = None
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)


def uninstall(destination: Path) -> None:
    if destination.is_symlink():
        raise ValueError(f"refusing to follow or remove symlink destination: {destination}")
    if not destination.is_dir():
        raise FileNotFoundError(f"installed template directory not found: {destination}")
    marker = destination / MARKER
    if not marker.is_file() or marker.read_text(encoding="utf-8") != MARKER_CONTENT:
        raise PermissionError(f"refusing to remove directory not marked as TuskerOS-managed: {destination}")
    shutil.rmtree(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "panel-template")
    parser.add_argument("--destination", type=Path, default=default_destination())
    parser.add_argument("--remove", action="store_true", help="remove only a directory carrying this installer's marker")
    args = parser.parse_args()
    try:
        if args.remove:
            uninstall(args.destination)
            print(f"Removed TuskerOS dock template: {args.destination}")
        else:
            install(args.source, args.destination)
            print(f"Installed TuskerOS dock template: {args.destination}")
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
