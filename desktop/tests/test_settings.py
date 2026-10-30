from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from desktop.config.settings import DEFAULT_SETTINGS, load_settings, save_settings, validate_settings


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config" / "desktop.json"

    def test_missing_file_returns_safe_defaults(self) -> None:
        settings, errors = load_settings(self.path)
        self.assertEqual(errors, [])
        self.assertEqual(settings, DEFAULT_SETTINGS)
        self.assertFalse(settings["assistant"]["enabled"])

    def test_partial_settings_merge_with_defaults(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"panel": {"icon_size": 64}}), encoding="utf-8")
        settings, errors = load_settings(self.path)
        self.assertEqual(errors, [])
        self.assertEqual(settings["panel"]["icon_size"], 64)
        self.assertEqual(settings["panel"]["edge"], "bottom")

    def test_rejects_unknown_keys(self) -> None:
        self.assertTrue(any("unknown setting" in error for error in validate_settings({"panel": {"mystery": True}})))

    def test_rejects_invalid_enum_and_bool_as_integer(self) -> None:
        self.assertTrue(validate_settings({"panel": {"edge": "center"}}))
        self.assertTrue(validate_settings({"schema_version": True}))

    def test_invalid_file_falls_back_to_defaults(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text("not json", encoding="utf-8")
        settings, errors = load_settings(self.path)
        self.assertTrue(errors)
        self.assertEqual(settings, DEFAULT_SETTINGS)

    def test_save_round_trip_and_private_mode(self) -> None:
        settings = {"panel": {"icon_size": 64}}
        save_settings(self.path, settings)
        loaded, errors = load_settings(self.path)
        self.assertEqual(errors, [])
        self.assertEqual(loaded["panel"]["icon_size"], 64)
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_save_refuses_symlink(self) -> None:
        self.path.parent.mkdir(parents=True)
        target = self.path.parent / "target.json"
        target.write_text("{}", encoding="utf-8")
        self.path.symlink_to(target)
        with self.assertRaises(ValueError):
            save_settings(self.path, {})

    def test_oversized_file_falls_back_to_defaults(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text(" " * (64 * 1024 + 1), encoding="utf-8")
        settings, errors = load_settings(self.path)
        self.assertTrue(errors)
        self.assertEqual(settings, DEFAULT_SETTINGS)


if __name__ == "__main__":
    unittest.main()
