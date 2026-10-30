from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from desktop.tools.validate_panel_template import validate


class ValidatePanelTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.template = Path(self.temp.name)
        (self.template / "contents").mkdir()

    def write_valid_template(self) -> None:
        (self.template / "metadata.desktop").write_text(
            "[Desktop Entry]\n"
            "Name=TuskerOS Dock\n"
            "Type=Service\n"
            "X-KDE-ServiceTypes=Plasma/LayoutTemplate\n"
            "X-KDE-PluginInfo-Name=com.tuskeros.desktop.dock\n"
            "X-KDE-PluginInfo-Version=0.1.0\n"
            "X-Plasma-API=javascript\n",
            encoding="utf-8",
        )
        (self.template / "contents" / "layout.js").write_text(
            'var plasma = getApiVersion(1);\n'
            'var dock = new plasma.Panel();\n'
            'dock.location = "bottom";\n'
            'dock.addWidget("org.kde.plasma.kickoff");\n'
            'dock.addWidget("org.kde.plasma.icontasks");\n',
            encoding="utf-8",
        )

    def test_accepts_valid_panel_template(self) -> None:
        self.write_valid_template()
        self.assertEqual(validate(self.template), [])

    def test_rejects_missing_metadata(self) -> None:
        self.assertTrue(any("missing template metadata" in e for e in validate(self.template)))

    def test_rejects_wrong_service_type(self) -> None:
        self.write_valid_template()
        path = self.template / "metadata.desktop"
        path.write_text(path.read_text(encoding="utf-8").replace("Plasma/LayoutTemplate", "Plasma/Applet"), encoding="utf-8")
        self.assertTrue(any("X-KDE-ServiceTypes" in e for e in validate(self.template)))

    def test_rejects_missing_native_task_manager(self) -> None:
        self.write_valid_template()
        path = self.template / "contents" / "layout.js"
        path.write_text(path.read_text(encoding="utf-8").replace('dock.addWidget("org.kde.plasma.icontasks");\n', ""), encoding="utf-8")
        self.assertTrue(any("org.kde.plasma.icontasks" in e for e in validate(self.template)))

    def test_rejects_destructive_panel_operation(self) -> None:
        self.write_valid_template()
        path = self.template / "contents" / "layout.js"
        path.write_text(path.read_text(encoding="utf-8") + "removePanel(dock);\n", encoding="utf-8")
        self.assertTrue(any("destructive operation" in e for e in validate(self.template)))


if __name__ == "__main__":
    unittest.main()
