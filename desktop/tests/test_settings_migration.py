from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from desktop.config.controller import SettingsController
from desktop.config.migrations import CURRENT_SCHEMA_VERSION, migrate_settings

class MigrationTests(unittest.TestCase):
    def test_unversioned_document_migrates_to_v1(self):
        candidate, errors, changed=migrate_settings({"panel":{"icon_size":64}})
        self.assertEqual(errors,[]); self.assertTrue(changed)
        self.assertEqual(candidate["schema_version"],CURRENT_SCHEMA_VERSION)
    def test_explicit_v0_document_migrates_to_v1(self):
        candidate, errors, changed=migrate_settings({"schema_version":0,"panel":{"icon_size":56}})
        self.assertEqual(errors,[]); self.assertTrue(changed); self.assertEqual(candidate["schema_version"],1)
    def test_future_version_is_rejected_without_downgrade(self):
        candidate, errors, changed=migrate_settings({"schema_version":99})
        self.assertEqual(candidate,{}); self.assertTrue(errors); self.assertFalse(changed)
    def test_deepcopy_recursion_is_returned_as_migration_error(self):
        with patch("desktop.config.migrations.deepcopy", side_effect=RecursionError):
            candidate, errors, changed = migrate_settings({"panel": {"icon_size": 64}})
        self.assertEqual(candidate, {})
        self.assertIn("nesting", " ".join(errors))
        self.assertFalse(changed)
    def test_controller_persists_legacy_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"desktop.json"; path.write_text(json.dumps({"panel":{"icon_size":64}}))
            controller=SettingsController(path); self.assertEqual(controller.load_errors,[])
            stored=json.loads(path.read_text())
            self.assertEqual(stored["schema_version"],1); self.assertEqual(stored["panel"]["icon_size"],64)
    def test_controller_migrates_explicit_v0_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"desktop.json"; path.write_text('{"schema_version":0,"panel":{"icon_size":56}}')
            controller=SettingsController(path); self.assertEqual(controller.load_errors,[])
            self.assertEqual(json.loads(path.read_text())["schema_version"],1)
    def test_failed_migration_write_preserves_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"desktop.json"; original='{"panel":{"icon_size":64}}'; path.write_text(original)
            with patch("desktop.config.controller.save_settings",side_effect=OSError("disk full")):
                controller=SettingsController(path)
            self.assertEqual(path.read_text(),original); self.assertTrue(controller.load_errors)

if __name__ == "__main__": unittest.main()
