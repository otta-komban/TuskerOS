from __future__ import annotations
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from desktop.config.settings import DEFAULT_SETTINGS
from desktop.tools.settings_recovery import default_settings_path, main

class SettingsRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config" / "desktop.json"

    def invoke(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        result = main(args, stdout=stdout, stderr=stderr)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_check_missing_file_reports_safe_defaults(self) -> None:
        result, stdout, stderr = self.invoke("check", "--config", str(self.path))
        self.assertEqual(result, 0)
        self.assertIn("safe defaults are active", stdout)
        self.assertEqual(stderr, "")

    def test_check_invalid_file_reports_errors_without_printing_contents(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"private-note":"do not echo"}', encoding="utf-8")
        result, stdout, stderr = self.invoke("check", "--config", str(self.path))
        self.assertEqual(result, 1)
        self.assertIn("unknown setting: private-note", stderr)
        self.assertNotIn("do not echo", stdout + stderr)

    def test_reset_requires_explicit_confirmation(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"panel":{"icon_size":64}}', encoding="utf-8")
        before = self.path.read_text(encoding="utf-8")
        result, _, stderr = self.invoke("reset", "--config", str(self.path))
        self.assertEqual(result, 2)
        self.assertIn("--yes", stderr)
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_reset_restores_defaults_with_private_permissions(self) -> None:
        result, stdout, stderr = self.invoke("reset", "--config", str(self.path), "--yes")
        self.assertEqual(result, 0)
        self.assertIn("schema-v1 defaults", stdout)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), DEFAULT_SETTINGS)
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_reset_refuses_symlink_destination(self) -> None:
        self.path.parent.mkdir(parents=True)
        target = self.path.parent / "target.json"
        target.write_text("{}", encoding="utf-8")
        self.path.symlink_to(target)
        result, _, stderr = self.invoke("reset", "--config", str(self.path), "--yes")
        self.assertEqual(result, 1)
        self.assertIn("symlink", stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "{}")

    def test_default_path_uses_absolute_xdg_config_home(self) -> None:
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(Path(self.temp.name) / "xdg")}):
            self.assertEqual(default_settings_path(), Path(self.temp.name) / "xdg" / "tuskeros" / "desktop.json")

if __name__ == "__main__":
    unittest.main()
