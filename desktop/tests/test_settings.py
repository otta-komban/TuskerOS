from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch
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

    def test_invalid_root_falls_back_to_defaults(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
        settings, errors = load_settings(self.path)
        self.assertTrue(any("root must be a JSON object" in error for error in errors))
        self.assertEqual(settings, DEFAULT_SETTINGS)

    def test_unsupported_schema_version_falls_back_to_defaults(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
        settings, errors = load_settings(self.path)
        self.assertTrue(any("schema_version must equal 1" in error for error in errors))
        self.assertEqual(settings, DEFAULT_SETTINGS)

    def test_broken_symlink_is_reported_not_treated_as_missing(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.symlink_to(self.path.parent / "missing-target.json")
        settings, errors = load_settings(self.path)
        self.assertTrue(any("symlink" in error for error in errors))
        self.assertEqual(settings, DEFAULT_SETTINGS)

    def test_valid_symlink_is_rejected_without_reading_target(self) -> None:
        self.path.parent.mkdir(parents=True)
        target = self.path.parent / "outside.json"
        target.write_text(json.dumps({"panel": {"icon_size": 72}}), encoding="utf-8")
        self.path.symlink_to(target)
        settings, errors = load_settings(self.path)
        self.assertTrue(errors)
        self.assertEqual(settings, DEFAULT_SETTINGS)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["panel"]["icon_size"], 72)

    def test_non_regular_settings_file_is_rejected_without_blocking(self) -> None:
        self.path.parent.mkdir(parents=True)
        os.mkfifo(self.path)
        settings, errors = load_settings(self.path)
        self.assertTrue(any("regular file" in error for error in errors))
        self.assertEqual(settings, DEFAULT_SETTINGS)

    def test_explicit_recovery_replaces_symlink_without_touching_target(self) -> None:
        self.path.parent.mkdir(parents=True)
        target = self.path.parent / "outside.json"
        original = json.dumps({"panel": {"icon_size": 72}})
        target.write_text(original, encoding="utf-8")
        self.path.symlink_to(target)

        save_settings(self.path, DEFAULT_SETTINGS, replace_symlink=True)

        self.assertFalse(self.path.is_symlink())
        loaded, errors = load_settings(self.path)
        self.assertEqual(errors, [])
        self.assertEqual(loaded, DEFAULT_SETTINGS)
        self.assertEqual(target.read_text(encoding="utf-8"), original)
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_save_refuses_symlink(self) -> None:
        self.path.parent.mkdir(parents=True)
        target = self.path.parent / "target.json"
        target.write_text("{}", encoding="utf-8")
        self.path.symlink_to(target)
        with self.assertRaises(ValueError):
            save_settings(self.path, {})

    def test_save_fsyncs_file_and_parent_directory(self) -> None:
        original_fsync = os.fsync
        with patch("desktop.config.settings.os.fsync", wraps=original_fsync) as fsync:
            save_settings(self.path, {"panel": {"icon_size": 64}})
        self.assertEqual(fsync.call_count, 2)

    def test_directory_fsync_failure_restores_previous_settings(self) -> None:
        self.path.parent.mkdir(parents=True)
        original = json.dumps({"panel": {"icon_size": 72}}) + "\\n"
        self.path.write_text(original, encoding="utf-8")
        real_fsync = os.fsync
        calls = 0

        def fail_directory_sync_once(descriptor: int) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated directory sync failure")
            real_fsync(descriptor)

        with patch("desktop.config.settings.os.fsync", side_effect=fail_directory_sync_once):
            with self.assertRaisesRegex(OSError, "directory sync failure"):
                save_settings(self.path, {"panel": {"icon_size": 64}})

        self.assertEqual(self.path.read_text(encoding="utf-8"), original)
        self.assertEqual(list(self.path.parent.glob(f".{self.path.name}.backup.*")), [])
        self.assertEqual(list(self.path.parent.glob(f".{self.path.name}.*")), [])

    def test_save_closes_temporary_file_when_file_fsync_fails(self) -> None:
        descriptors: list[int] = []

        def fail_fsync(descriptor: int) -> None:
            descriptors.append(descriptor)
            raise OSError("simulated file sync failure")

        with patch("desktop.config.settings.os.fsync", side_effect=fail_fsync):
            with self.assertRaisesRegex(OSError, "simulated file sync failure"):
                save_settings(self.path, {"panel": {"icon_size": 64}})

        self.assertEqual(len(descriptors), 1)
        with self.assertRaises(OSError):
            os.fstat(descriptors[0])
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.path.parent.glob(f".{self.path.name}.*")), [])

    def test_duplicate_top_level_json_keys_fall_back_to_defaults(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"panel":{"icon_size":64},"panel":{"icon_size":80}}', encoding="utf-8")
        settings, errors = load_settings(self.path)
        self.assertTrue(any("duplicate object key" in error for error in errors))
        self.assertEqual(settings, DEFAULT_SETTINGS)

    def test_duplicate_nested_json_keys_fall_back_to_defaults(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"panel":{"icon_size":64,"icon_size":80}}', encoding="utf-8")
        settings, errors = load_settings(self.path)
        self.assertTrue(any("duplicate object key" in error for error in errors))
        self.assertEqual(settings, DEFAULT_SETTINGS)

    def test_oversized_file_falls_back_to_defaults(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text(" " * (64 * 1024 + 1), encoding="utf-8")
        settings, errors = load_settings(self.path)
        self.assertTrue(errors)
        self.assertEqual(settings, DEFAULT_SETTINGS)


if __name__ == "__main__":
    unittest.main()
