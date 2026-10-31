"""UI-facing controller with bounded, fail-closed legacy migration."""
from __future__ import annotations
from copy import deepcopy
import json
import os
import stat
from pathlib import Path
from typing import Any
from desktop.config.settings import DEFAULT_SETTINGS, MAX_SETTINGS_BYTES, load_settings, save_settings, validate_settings
from desktop.config.migrations import migrate_settings

def _merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result

def _read_legacy_document(path: Path) -> dict[str, Any]:
    """Read only a bounded regular file without following a final-component symlink."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("settings file must be a regular file")
        if info.st_size > MAX_SETTINGS_BYTES:
            raise ValueError(f"settings file exceeds {MAX_SETTINGS_BYTES} bytes")
        chunks: list[bytes] = []
        remaining = MAX_SETTINGS_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(8192, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > MAX_SETTINGS_BYTES:
            raise ValueError(f"settings file exceeds {MAX_SETTINGS_BYTES} bytes")
    finally:
        os.close(fd)
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("settings JSON contains a duplicate object key")
            result[key] = value
        return result
    return json.loads(payload.decode("utf-8"), object_pairs_hook=reject_duplicates)

class SettingsController:
    """Expose detached reads and transactional updates to the desktop settings UI."""
    def __init__(self, path: Path):
        self.path = Path(path)
        self.load_errors: list[str] = []
        self._settings, self.load_errors = load_settings(self.path)
        if self.path.is_symlink():
            return
        try:
            raw = _read_legacy_document(self.path)
        except FileNotFoundError:
            return
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            self.load_errors = [f"cannot migrate settings: {exc}"]
            self._settings = deepcopy(DEFAULT_SETTINGS)
            return
        migrated, errors, changed = migrate_settings(raw)
        errors.extend(validate_settings(migrated) if not errors else [])
        if errors:
            self.load_errors = errors
            self._settings = deepcopy(DEFAULT_SETTINGS)
        elif changed:
            candidate = _merge(DEFAULT_SETTINGS, migrated)
            try:
                save_settings(self.path, candidate)
            except (OSError, ValueError) as exc:
                self.load_errors = [f"cannot persist settings migration: {exc}"]
                self._settings = deepcopy(DEFAULT_SETTINGS)
            else:
                self._settings = candidate
                self.load_errors = []

    def read(self) -> dict[str, Any]:
        return deepcopy(self._settings)

    def update(self, patch: Any) -> dict[str, Any]:
        if self.load_errors:
            raise ValueError("settings need recovery; restore defaults before editing")
        if not isinstance(patch, dict):
            raise ValueError("settings update must be an object")
        errors = validate_settings(patch)
        if errors:
            raise ValueError("; ".join(errors))
        candidate = _merge(self._settings, patch)
        errors = validate_settings(candidate)
        if errors:
            raise ValueError("; ".join(errors))
        save_settings(self.path, candidate)
        self._settings = candidate
        return self.read()

    def reset(self) -> dict[str, Any]:
        candidate = deepcopy(DEFAULT_SETTINGS)
        save_settings(self.path, candidate)
        self._settings = candidate
        self.load_errors = []
        return self.read()
