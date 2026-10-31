from pathlib import Path
import unittest
APP = Path(__file__).resolve().parents[1] / "settings"
class SettingsAppTests(unittest.TestCase):
    def test_host_injects_backend_before_loading_qml(self):
        source=(APP/"app.py").read_text(encoding="utf-8")
        self.assertLess(source.index('setContextProperty("settingsBackend", backend)'),source.index("engine.load("))
        self.assertIn("SettingsController(default_settings_path())",source)
    def test_backend_exposes_only_preferences_operations(self):
        source=(APP/"app.py").read_text(encoding="utf-8")
        for operation in ("def read(", "def status(", "def update(", "def reset("): self.assertIn(operation,source)
        self.assertNotIn("subprocess",source); self.assertNotIn("os.system",source)
    def test_desktop_launcher_is_installed_entry_point(self):
        descriptor=(APP/"tuskeros-settings.desktop").read_text(encoding="utf-8")
        self.assertIn("Exec=/usr/libexec/tuskeros/settings",descriptor)
        self.assertIn("Type=Application",descriptor)
    def test_entry_point_uses_private_package_root(self):
        launcher=(APP/"tuskeros-settings").read_text(encoding="utf-8")
        self.assertIn('sys.path.insert(0, "/usr/lib/tuskeros")',launcher)
    def test_qml_uses_injected_backend_not_shadow_property(self):
        source=(APP/"main.qml").read_text(encoding="utf-8")
        self.assertNotIn("property var settingsBackend",source)
        self.assertIn("settingsBackend.status().needsRecovery",source)
if __name__ == "__main__": unittest.main()
