"""Validated, user-scoped desktop preferences with safe defaults and atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

MAX_SETTINGS_BYTES = 64 * 1024

DEFAULT_SETTINGS: dict[str, Any] = {
    "schema_version": 1,
    "panel": {
        "enabled": True,
        "edge": "bottom",
        "icon_size": 48,
        "auto_hide": False,
    },
    "assistant": {
        "enabled": False,
        "show_task_progress": True,
    },
    "accessibility": {
        "reduced_motion": False,
        "high_contrast": False,
    },
}

_ALLOWED: dict[str, Any] = {
    "schema_version": int,
    "panel": {
        "enabled": bool,
        "edge": ("bottom", "top", "left", "right"),
        "icon_size": (24, 32, 40, 48, 56, 64, 72, 80, 88, 96),
        "auto_hide": bool,
    },
    "assistant": {
        "enabled": bool,
        "show_task_progress": bool,
    },
    "accessibility": {
        "reduced_motion": bool,
        "high_contrast": bool,
    },
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


def load_settings(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Load preferences; missing or invalid files safely fall back to defaults."""
    path = Path(path)
    if not path.exists():
        return _merge(DEFAULT_SETTINGS, {}), []
    if path.is_symlink():
        return _merge(DEFAULT_SETTINGS, {}), ["settings file must not be a symlink"]
    try:
        if path.stat().st_size > MAX_SETTINGS_BYTES:
            raise ValueError(f"settings file exceeds {MAX_SETTINGS_BYTES} bytes")
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return _merge(DEFAULT_SETTINGS, {}), [f"cannot load settings: {exc}"]
    errors = validate_settings(raw)
    if errors:
        return _merge(DEFAULT_SETTINGS, {}), errors
    return _merge(DEFAULT_SETTINGS, raw), []


def save_settings(path: Path, value: Any) -> None:
    """Validate and atomically persist a complete effective configuration, mode 0600."""
    errors = validate_settings(value)
    if errors:
        raise ValueError("; ".join(errors))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("refusing to replace a symlink settings file")
    payload = json.dumps(_merge(DEFAULT_SETTINGS, value), indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > MAX_SETTINGS_BYTES:
        raise ValueError(f"settings file exceeds {MAX_SETTINGS_BYTES} bytes")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink():
            raise ValueError("refusing to replace a symlink settings file")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
