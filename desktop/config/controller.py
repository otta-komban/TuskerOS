"""UI-facing controller; persistence remains in the validated config layer."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from typing import Any
from desktop.config.settings import DEFAULT_SETTINGS, load_settings, save_settings, validate_settings
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
        self._settings, self.load_errors = load_settings(self.path)
        # Migrate valid legacy files through the same atomic writer. Preserve bad/future input.
        if self.path.is_file() and not self.path.is_symlink():
            try:
                def reject_duplicates(pairs):
                    result = {}
                    for key, value in pairs:
                        if key in result:
                            raise ValueError("settings JSON contains a duplicate object key")
                        result[key] = value
                    return result
                raw = json.loads(self.path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
                migrated, errors, changed = migrate_settings(raw)
                errors.extend(validate_settings(migrated) if not errors else [])
                if errors:
                    self.load_errors = errors
                    self._settings = deepcopy(DEFAULT_SETTINGS)
                elif changed:
                    candidate = _merge(DEFAULT_SETTINGS, migrated)
                    save_settings(self.path, candidate)
                    self._settings = candidate
                    self.load_errors = []
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                self.load_errors = [f"cannot migrate settings: {exc}"]
                self._settings = deepcopy(DEFAULT_SETTINGS)

    def read(self) -> dict[str, Any]:
        return deepcopy(self._settings)

    def update(self, patch: Any) -> dict[str, Any]:
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
        self.load_errors = []
        return self.read()

    def reset(self) -> dict[str, Any]:
        candidate = deepcopy(DEFAULT_SETTINGS)
        save_settings(self.path, candidate)
        self._settings = candidate
        self.load_errors = []
        return self.read()
