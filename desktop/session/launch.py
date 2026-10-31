#!/usr/bin/python3
"""Start the stock KDE Plasma 6 Wayland session for TuskerOS.

This is a thin, auditable session entry point. It does not replace KWin,
plasmashell, SDDM, systemd --user, or any privileged system service.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence, TextIO

PLASMA_WAYLAND = Path("/usr/bin/startplasma-wayland")
SESSION_ENVIRONMENT = {
    "XDG_SESSION_TYPE": "wayland",
    "XDG_CURRENT_DESKTOP": "KDE",
    "XDG_SESSION_DESKTOP": "KDE",
    "KDE_FULL_SESSION": "true",
    "KDE_SESSION_VERSION": "6",
}


def build_session_environment(source: Mapping[str, str]) -> dict[str, str]:
    """Preserve the login-manager environment and declare the supported session."""
    environment = dict(source)
    environment.update(SESSION_ENVIRONMENT)
    return environment


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    executable: Path = PLASMA_WAYLAND,
    is_executable: Callable[[Path], bool] = _is_executable,
    execve: Callable[[str, list[str], dict[str, str]], object] = os.execve,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Validate and exec Plasma without a shell or an intermediate daemon."""
    out, err = stdout or sys.stdout, stderr or sys.stderr
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="check that the configured Plasma Wayland launcher is executable",
    )
    parser.add_argument("plasma_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not is_executable(executable):
        print(f"TuskerOS session: required executable is unavailable: {executable}", file=err)
        return 127

    if args.check:
        print(f"TuskerOS session launcher ready: {executable}", file=out)
        return 0

    environment = build_session_environment(environ if environ is not None else os.environ)
    command = [str(executable), *args.plasma_args]
    try:
        execve(str(executable), command, environment)
    except OSError as exc:
        print(f"TuskerOS session: could not start Plasma: {exc}", file=err)
        return 126
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
