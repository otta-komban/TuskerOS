from pathlib import Path
import unittest
QML = Path(__file__).resolve().parents[1] / "settings" / "main.qml"
class SettingsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.source=QML.read_text(encoding="utf-8")
    def test_interactive_controls_have_accessible_names(self): self.assertGreaterEqual(self.source.count("Accessible.name:"),8)
    def test_restore_defaults_requires_confirmation(self):
        self.assertIn("resetDialog.open()",self.source); self.assertIn("Dialog.Yes | Dialog.Cancel",self.source)
    def test_invalid_settings_disable_preference_groups_until_reset(self):
        self.assertIn("property bool needsRecovery: false", self.source)
        self.assertIn("needsRecovery = settingsBackend.status().needsRecovery", self.source)
        self.assertEqual(self.source.count("enabled: !window.needsRecovery"), 3)
        self.assertIn("needsRecovery=false", self.source)
        self.assertIn("Button { text: qsTr(\"Restore defaults…\")", self.source)

    def test_writes_use_validated_backend(self):
        self.assertIn("settingsBackend.update(patch)",self.source); self.assertNotIn("Qt.labs.settings",self.source)
    def test_failures_are_announced_and_remain_visible(self):
        self.assertIn("Accessible.announce(message, Accessible.Assertive)",self.source)
        self.assertIn("Accessible.role: Accessible.AlertMessage",self.source)
        self.assertIn("Your previous preferences are unchanged.",self.source)
    def test_system_palette_is_used(self): self.assertIn("color: palette.window",self.source)
if __name__ == "__main__": unittest.main()
