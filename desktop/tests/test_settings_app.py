from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from desktop.config.controller import SettingsController

try:
    from desktop.settings.app import SettingsBackend
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise
    SettingsBackend = None

APP = Path(__file__).resolve().parents[1] / "settings"


class SettingsAppTests(unittest.TestCase):
    def test_host_injects_backend_before_loading_qml(self):
        source = (APP / "app.py").read_text(encoding="utf-8")
        self.assertLess(
            source.index('setContextProperty("settingsBackend", backend)'),
            source.index("engine.load("),
        )
        self.assertIn("SettingsController(default_settings_path())", source)

    def test_backend_exposes_only_preferences_operations(self):
        source = (APP / "app.py").read_text(encoding="utf-8")
        for operation in ("def read(", "def status(", "def update(", "def reset("):
            self.assertIn(operation, source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("os.system", source)

    @unittest.skipIf(SettingsBackend is None, "PySide6 is installed in the Qt runtime CI job")
    def test_backend_recovery_round_trip_requires_explicit_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "desktop.json"
            original = '{"panel":{"edge":"unsafe"}}'
            path.write_text(original, encoding="utf-8")
            backend = SettingsBackend(SettingsController(path))

            self.assertEqual(backend.status(), {"needsRecovery": True})
            self.assertEqual(backend.update({"panel": {"icon_size": 64}}), {"ok": False})
            self.assertEqual(path.read_text(encoding="utf-8"), original)

            reset = backend.reset()
            self.assertTrue(reset["ok"])
            self.assertEqual(backend.status(), {"needsRecovery": False})
            self.assertEqual(backend.read(), reset["settings"])

            update = backend.update({"panel": {"icon_size": 64}})
            self.assertTrue(update["ok"])
            self.assertEqual(update["settings"]["panel"]["icon_size"], 64)

    @unittest.skipIf(SettingsBackend is None, "PySide6 is installed in the Qt runtime CI job")
    def test_backend_reset_failure_keeps_recovery_mode_and_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "desktop.json"
            original = '{"panel":{"edge":"unsafe"}}'
            path.write_text(original, encoding="utf-8")
            backend = SettingsBackend(SettingsController(path))
            with patch("desktop.config.controller.save_settings", side_effect=OSError("disk full")):
                self.assertEqual(backend.reset(), {"ok": False})
            self.assertEqual(backend.status(), {"needsRecovery": True})
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertEqual(backend.update({"panel": {"icon_size": 64}), {"ok": False})

    def test_desktop_launcher_is_installed_entry_point(self):
        descriptor = (APP / "tuskeros-settings.desktop").read_text(encoding="utf-8")
        self.assertIn("Exec=/usr/libexec/tuskeros/settings", descriptor)
        self.assertIn("Type=Application", descriptor)

    def test_entry_point_uses_private_package_root(self):
        launcher = (APP / "tuskeros-settings").read_text(encoding="utf-8")
        self.assertIn('sys.path.insert(0, "/usr/lib/tuskeros")', launcher)

    def test_qml_uses_injected_backend_not_shadow_property(self):
        source = (APP / "main.qml").read_text(encoding="utf-8")
        self.assertNotIn("property var settingsBackend", source)
        self.assertIn("settingsBackend.status().needsRecovery", source)


if __name__ == "__main__":
    unittest.main()
