from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from desktop.tools.validate_plasmoid import validate


class ValidatePlasmoidTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.package = Path(self.temp.name)
        (self.package / "contents" / "ui").mkdir(parents=True)

    def write_valid_package(self) -> None:
        metadata = {
            "KPlugin": {
                "Id": "org.example.desktop",
                "Name": "Example",
                "Version": "0.1.0",
                "License": "MIT",
            },
            "X-Plasma-API-Minimum-Version": "6.0",
            "KPackageStructure": "Plasma/Applet",
        }
        (self.package / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (self.package / "contents" / "ui" / "main.qml").write_text(
            "import QtQuick\n"
            "import org.kde.plasma.components as PlasmaComponents\n"
            "PlasmoidItem { }\n",
            encoding="utf-8",
        )

    def test_accepts_minimal_plasma6_package(self) -> None:
        self.write_valid_package()
        self.assertEqual(validate(self.package), [])

    def test_rejects_invalid_metadata_json(self) -> None:
        (self.package / "metadata.json").write_text("{not json", encoding="utf-8")
        (self.package / "contents" / "ui" / "main.qml").write_text("PlasmoidItem {}", encoding="utf-8")
        self.assertTrue(any("invalid metadata JSON" in error for error in validate(self.package)))

    def test_rejects_wrong_package_structure(self) -> None:
        self.write_valid_package()
        metadata_path = self.package / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["KPackageStructure"] = "Plasma/Generic"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        self.assertTrue(any("KPackageStructure" in error for error in validate(self.package)))

    def test_rejects_non_plasma6_minimum_version(self) -> None:
        self.write_valid_package()
        metadata_path = self.package / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["X-Plasma-API-Minimum-Version"] = "5.0"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        self.assertTrue(any("Plasma 6" in error for error in validate(self.package)))

    def test_rejects_missing_plasmoid_root(self) -> None:
        self.write_valid_package()
        qml_path = self.package / "contents" / "ui" / "main.qml"
        qml_path.write_text("import QtQuick\nItem {}", encoding="utf-8")
        self.assertTrue(any("PlasmoidItem" in error for error in validate(self.package)))


if __name__ == "__main__":
    unittest.main()
