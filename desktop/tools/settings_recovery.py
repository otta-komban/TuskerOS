#!/usr/bin/env python3
"""Inspect or explicitly reset the user-scoped desktop settings file."""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from typing import Sequence, TextIO
from desktop.config.settings import DEFAULT_SETTINGS, load_settings, save_settings

def default_settings_path() -> Path:
    """Resolve the standard XDG config location without accepting relative XDG paths."""
    configured_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(configured_home).expanduser() if configured_home else Path.home() / ".config"
    if not base.is_absolute():
        base = Path.home() / ".config"
    return base / "tuskeros" / "desktop.json"

def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    out, err = stdout or sys.stdout, stderr or sys.stderr
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "reset"), help="check settings or restore safe defaults")
    parser.add_argument("--config", type=Path, help="settings file (defaults to the XDG user config path)")
    parser.add_argument("--yes", action="store_true", help="confirm the destructive reset action")
    args = parser.parse_args(argv)
    path = args.config.expanduser() if args.config else default_settings_path()
    if args.action == "check":
        _, errors = load_settings(path)
        if errors:
            print("Invalid settings; safe defaults are active.", file=err)
            for error in errors:
                print(f"- {error}", file=err)
            return 1
        if path.is_file():
            print(f"Settings are valid: {path}", file=out)
        else:
            print(f"Settings file is missing; safe defaults are active: {path}", file=out)
        return 0
    if not args.yes:
        print("Reset not performed; rerun with --yes to confirm.", file=err)
        return 2
    try:
        save_settings(path, DEFAULT_SETTINGS)
    except (OSError, ValueError) as exc:
        print(f"Could not reset settings: {exc}", file=err)
        return 1
    print(f"Settings reset to schema-v1 defaults: {path}", file=out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
