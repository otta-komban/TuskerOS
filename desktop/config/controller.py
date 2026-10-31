"""UI-facing controller with bounded, fail-closed legacy migration."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
from desktop.config.settings import DEFAULT_SETTINGS, save_settings, validate_settings, _read_settings_document
from desktop.config.migrations import migrate_settings


def _merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


class SettingsController:
    """Expose detached reads and transactional updates to the desktop settings UI."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.load_errors: list[str] = []
        try:
            # Parse once so validation and migration operate on the same opened
            # no-follow, bounded file snapshot.
            raw = _read_settings_document(self.path)
        except FileNotFoundError:
            self._settings = deepcopy(DEFAULT_SETTINGS)
            return
        except (OSError, UnicodeError, ValueError) as exc:
            self.load_errors = [f"cannot load settings: {exc}"]
            self._settings = deepcopy(DEFAULT_SETTINGS)
            return

        migrated, errors, changed = migrate_settings(raw)
        errors.extend(validate_settings(migrated) if not errors else [])
        if errors:
            self.load_errors = errors
            self._settings = deepcopy(DEFAULT_SETTINGS)
            return

        candidate = _merge(DEFAULT_SETTINGS, migrated)
        if changed:
            try:
                save_settings(self.path, candidate)
            except (OSError, ValueError) as exc:
                self.load_errors = [f"cannot persist settings migration: {exc}"]
                self._settings = deepcopy(DEFAULT_SETTINGS)
                return

        self._settings = candidate

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
        # Explicit recovery atomically replaces the final symlink entry; os.replace never follows its target.
        save_settings(self.path, candidate, replace_symlink=True)
        self._settings = candidate
        self.load_errors = []
        return self.read()
