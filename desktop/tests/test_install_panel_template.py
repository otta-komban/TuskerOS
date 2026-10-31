from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from desktop.tools.install_panel_template import MARKER, MARKER_CONTENT, install, uninstall


class PanelTemplateInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "source"
        (self.source / "contents").mkdir(parents=True)
        (self.source / "metadata.desktop").write_text("[Desktop Entry]\nName=Test\n", encoding="utf-8")
        (self.source / "contents" / "layout.js").write_text("var panel = true;\n", encoding="utf-8")
        self.destination = root / "data" / "plasma" / "layout-templates" / "com.tuskeros.desktop.dock"

    def test_install_copies_template_and_management_marker(self) -> None:
        install(self.source, self.destination)
        self.assertTrue((self.destination / "metadata.desktop").is_file())
        self.assertTrue((self.destination / "contents" / "layout.js").is_file())
        self.assertEqual((self.destination / MARKER).read_text(encoding="utf-8"), MARKER_CONTENT)

    def test_install_refuses_to_overwrite_existing_directory(self) -> None:
        self.destination.mkdir(parents=True)
        sentinel = self.destination / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            install(self.source, self.destination)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_install_refuses_symlink_destination(self) -> None:
        self.destination.parent.mkdir(parents=True)
        elsewhere = self.destination.parent / "elsewhere"
        elsewhere.mkdir()
        self.destination.symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaises(FileExistsError):
            install(self.source, self.destination)
        self.assertTrue(elsewhere.is_dir())

    def test_uninstall_removes_only_marked_installation(self) -> None:
        install(self.source, self.destination)
        uninstall(self.destination)
        self.assertFalse(self.destination.exists())

    def test_uninstall_refuses_unmanaged_directory(self) -> None:
        self.destination.mkdir(parents=True)
        sentinel = self.destination / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises(PermissionError):
            uninstall(self.destination)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
