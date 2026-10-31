from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop.tools import install_panel_template
from desktop.tools.install_panel_template import MARKER, MARKER_CONTENT, install, uninstall


class PanelTemplateInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "source"
        (self.source / "contents").mkdir(parents=True)
        (self.source / "metadata.desktop").write_text("[Desktop Entry]\\nName=Test\\n", encoding="utf-8")
        (self.source / "contents" / "layout.js").write_text("var panel = true;\\n", encoding="utf-8")
        self.destination = root / "data" / "plasma" / "layout-templates" / "com.tuskeros.desktop.dock"

    def test_default_destination_uses_absolute_xdg_data_home(self) -> None:
        configured = Path(self.temp.name) / "xdg-data"
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(configured)}):
            self.assertEqual(
                install_panel_template.default_destination(),
                configured / "plasma" / "layout-templates" / install_panel_template.PLUGIN_ID,
            )

    def test_default_destination_falls_back_for_relative_xdg_data_home(self) -> None:
        with patch.dict(os.environ, {"XDG_DATA_HOME": "relative/data"}):
            self.assertEqual(
                install_panel_template.default_destination(),
                Path.home() / ".local" / "share" / "plasma" / "layout-templates" / install_panel_template.PLUGIN_ID,
            )

    def test_default_destination_expands_home_in_xdg_data_home(self) -> None:
        with patch.dict(os.environ, {"XDG_DATA_HOME": "~/custom-data"}):
            self.assertEqual(
                install_panel_template.default_destination(),
                Path.home() / "custom-data" / "plasma" / "layout-templates" / install_panel_template.PLUGIN_ID,
            )

    def test_install_copies_template_and_management_marker(self) -> None:
        install(self.source, self.destination)
        self.assertTrue((self.destination / "metadata.desktop").is_file())
        self.assertTrue((self.destination / "contents" / "layout.js").is_file())
        self.assertEqual((self.destination / MARKER).read_text(encoding="utf-8"), MARKER_CONTENT)
        marker_text = (self.destination / MARKER).read_text(encoding="utf-8")
        self.assertTrue(marker_text.endswith("\n"))
        self.assertFalse(marker_text.endswith("\\n"))

    def test_install_rejects_symlink_inside_source_tree(self) -> None:
        layout = self.source / "contents" / "layout.js"
        layout.unlink()
        external = Path(self.temp.name) / "outside.js"
        external.write_text("outside data", encoding="utf-8")
        layout.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "symlink or special file"):
            install(self.source, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(external.read_text(encoding="utf-8"), "outside data")

    def test_install_rejects_fifo_inside_source_tree(self) -> None:
        layout = self.source / "contents" / "layout.js"
        layout.unlink()
        os.mkfifo(layout)
        with self.assertRaisesRegex(ValueError, "symlink or special file"):
            install(self.source, self.destination)
        self.assertFalse(self.destination.exists())

    def test_install_does_not_replace_destination_created_during_publish(self) -> None:
        real_publish = install_panel_template._publish_directory_noreplace

        def create_destination_then_publish(source: Path, destination: Path) -> None:
            destination.mkdir()
            sentinel = destination / "created-by-concurrent-process.txt"
            sentinel.write_text("preserve me", encoding="utf-8")
            real_publish(source, destination)

        with patch.object(
            install_panel_template,
            "_publish_directory_noreplace",
            side_effect=create_destination_then_publish,
        ):
            with self.assertRaises(FileExistsError):
                install(self.source, self.destination)

        self.assertEqual(
            (self.destination / "created-by-concurrent-process.txt").read_text(encoding="utf-8"),
            "preserve me",
        )
        self.assertEqual(list(self.destination.parent.glob(".tusker-dock-staging-*")), [])

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
