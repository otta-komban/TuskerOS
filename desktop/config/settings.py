"""Validated, user-scoped desktop preferences with safe defaults and atomic writes."""

from __future__ import annotations

import errno
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

MAX_SETTINGS_BYTES = 64 * 1024

DEFAULT_SETTINGS: dict[str, Any] = {
    "schema_version": 1,
    "panel": {"enabled": True, "edge": "bottom", "icon_size": 48, "auto_hide": False},
    "assistant": {"enabled": False, "show_task_progress": True},
    "accessibility": {"reduced_motion": False, "high_contrast": False},
}
_ALLOWED: dict[str, Any] = {
    "schema_version": int,
    "panel": {"enabled": bool, "edge": ("bottom", "top", "left", "right"),
              "icon_size": (24, 32, 40, 48, 56, 64, 72, 80, 88, 96), "auto_hide": bool},
    "assistant": {"enabled": bool, "show_task_progress": bool},
    "accessibility": {"reduced_motion": bool, "high_contrast": bool},
}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = {key: value.copy() if isinstance(value, dict) else value for key, value in base.items()}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def validate_settings(value: Any) -> list[str]:
    """Return validation errors for a partial settings object; unknown keys fail closed."""
    if not isinstance(value, dict):
        return ["settings root must be a JSON object"]
    errors: list[str] = []
    for key, item in value.items():
        if key not in _ALLOWED:
            errors.append(f"unknown setting: {key}")
            continue
        expected = _ALLOWED[key]
        if isinstance(expected, dict):
            if not isinstance(item, dict):
                errors.append(f"{key} must be an object")
                continue
            for child, child_value in item.items():
                if child not in expected:
                    errors.append(f"unknown setting: {key}.{child}")
                elif isinstance(expected[child], tuple):
                    if child_value not in expected[child] or isinstance(child_value, bool):
                        errors.append(f"{key}.{child} must be one of {', '.join(map(str, expected[child]))}")
                elif expected[child] is int:
                    if not isinstance(child_value, int) or isinstance(child_value, bool) or child_value != 1:
                        errors.append(f"{key}.{child} must equal 1")
                elif not isinstance(child_value, expected[child]):
                    errors.append(f"{key}.{child} must be {expected[child].__name__}")
        elif not isinstance(item, int) or isinstance(item, bool) or item != 1:
            errors.append("schema_version must equal 1")
    return errors


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject ambiguous JSON objects instead of silently keeping the last key."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("settings JSON contains a duplicate object key")
        result[key] = value
    return result


def _read_settings_document(path: Path) -> Any:
    """Read bounded JSON through a no-follow descriptor for the opened regular file."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(Path(path), flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError("settings file must not be a symlink") from exc
        raise
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("settings file must be a regular file")
        if info.st_size > MAX_SETTINGS_BYTES:
            raise ValueError(f"settings file exceeds {MAX_SETTINGS_BYTES} bytes")
        chunks: list[bytes] = []
        remaining = MAX_SETTINGS_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(8192, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > MAX_SETTINGS_BYTES:
            raise ValueError(f"settings file exceeds {MAX_SETTINGS_BYTES} bytes")
    finally:
        os.close(descriptor)
    return json.loads(payload.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)


def _fsync_directory(path: Path) -> None:
    """Persist directory-entry changes after an atomic rename."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_fd = os.open(path, flags)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def load_settings(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Load preferences without following symlinks or blocking on special files."""
    try:
        raw = _read_settings_document(Path(path))
    except FileNotFoundError:
        return _merge(DEFAULT_SETTINGS, {}), []
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return _merge(DEFAULT_SETTINGS, {}), [f"cannot load settings: {exc}"]
    errors = validate_settings(raw)
    if errors:
        return _merge(DEFAULT_SETTINGS, {}), errors
    return _merge(DEFAULT_SETTINGS, raw), []


def save_settings(path: Path, value: Any, *, replace_symlink: bool = False) -> None:
    """Validate and atomically persist settings; recovery may replace the final symlink entry."""
    errors = validate_settings(value)
    if errors:
        raise ValueError("; ".join(errors))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() and not replace_symlink:
        raise ValueError("refusing to replace a symlink settings file")
    payload = json.dumps(_merge(DEFAULT_SETTINGS, value), indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > MAX_SETTINGS_BYTES:
        raise ValueError(f"settings file exceeds {MAX_SETTINGS_BYTES} bytes")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink() and not replace_symlink:
            raise ValueError("refusing to replace a symlink settings file")
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
