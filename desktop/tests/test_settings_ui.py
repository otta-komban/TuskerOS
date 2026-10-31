from pathlib import Path
import unittest
QML = Path(__file__).resolve().parents[1] / "settings" / "main.qml"
class SettingsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.source=QML.read_text(encoding="utf-8")
    def test_interactive_controls_have_accessible_names(self): self.assertGreaterEqual(self.source.count("Accessible.name:"),8)
    def test_restore_defaults_requires_confirmation(self):
        self.assertIn("resetDialog.open()",self.source); self.assertIn("Dialog.Yes | Dialog.Cancel",self.source)
    def test_writes_use_validated_backend(self):
        self.assertIn("settingsBackend.update(patch)",self.source); self.assertNotIn("Qt.labs.settings",self.source)
    def test_failures_are_announced_and_can_be_reloaded(self):
        self.assertIn("Accessible.Assertive",self.source); self.assertIn("reloadPreferences()",self.source)
    def test_system_palette_is_used(self): self.assertIn("color: palette.window",self.source)
if __name__ == "__main__": unittest.main()
