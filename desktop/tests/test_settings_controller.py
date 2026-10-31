from __future__ import annotations
import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from desktop.config.controller import SettingsController
from desktop.config.settings import DEFAULT_SETTINGS, MAX_SETTINGS_BYTES

class SettingsControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "desktop.json"
    def test_startup_reads_settings_once_for_validation_and_migration(self):
        self.path.write_text(json.dumps(DEFAULT_SETTINGS))
        with patch("desktop.config.settings.os.open", wraps=os.open) as open_file:
            controller = SettingsController(self.path)
        self.assertEqual(open_file.call_count, 1)
        self.assertEqual(controller.load_errors, [])
        self.assertEqual(controller.read(), DEFAULT_SETTINGS)
    def test_update_persists_across_controller_restart(self):
        SettingsController(self.path).update({"panel":{"icon_size":72},"accessibility":{"high_contrast":True}})
        restarted = SettingsController(self.path)
        self.assertEqual(restarted.read()["panel"]["icon_size"],72)
        self.assertTrue(restarted.read()["accessibility"]["high_contrast"])
    def test_invalid_update_does_not_change_memory_or_disk(self):
        controller=SettingsController(self.path); before=controller.read()
        with self.assertRaises(ValueError): controller.update({"panel":{"edge":"center"}})
        self.assertEqual(controller.read(),before); self.assertFalse(self.path.exists())
    def test_write_failure_does_not_publish_candidate(self):
        controller=SettingsController(self.path); before=controller.read()
        with patch("desktop.config.controller.save_settings",side_effect=OSError("disk full")):
            with self.assertRaises(OSError): controller.update({"panel":{"icon_size":80}})
        self.assertEqual(controller.read(),before)
    def test_reset_restores_and_persists_defaults(self):
        controller=SettingsController(self.path); controller.update({"assistant":{"enabled":True}})
        self.assertEqual(controller.reset(),DEFAULT_SETTINGS)
        self.assertEqual(json.loads(self.path.read_text()),DEFAULT_SETTINGS)
    def test_failed_reset_preserves_existing_settings_and_memory(self):
        controller=SettingsController(self.path)
        controller.update({"panel":{"icon_size":72}})
        original=self.path.read_text()
        before=controller.read()
        with patch("desktop.config.controller.save_settings",side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError,"disk full"):
                controller.reset()
        self.assertEqual(self.path.read_text(),original)
        self.assertEqual(controller.read(),before)
        self.assertEqual(controller.load_errors,[])
    def test_failed_recovery_reset_keeps_original_file_and_edit_lock(self):
        original='{"panel":{"edge":"unsafe"}}'
        self.path.write_text(original)
        controller=SettingsController(self.path)
        self.assertTrue(controller.load_errors)
        with patch("desktop.config.controller.save_settings",side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError,"disk full"):
                controller.reset()
        self.assertEqual(self.path.read_text(),original)
        self.assertTrue(controller.load_errors)
        with self.assertRaisesRegex(ValueError,"restore defaults"):
            controller.update({"panel":{"icon_size":64}})
    def test_read_returns_detached_copy(self):
        controller=SettingsController(self.path); exposed=controller.read(); exposed["panel"]["icon_size"]=1
        self.assertEqual(controller.read()["panel"]["icon_size"],DEFAULT_SETTINGS["panel"]["icon_size"])
    def test_excessively_nested_json_enters_recovery_without_rewrite(self):
        original = '{"a":' * 10000 + "0" + "}" * 10000
        self.path.write_text(original)
        controller = SettingsController(self.path)
        self.assertTrue(controller.load_errors)
        self.assertIn("nesting", " ".join(controller.load_errors))
        self.assertEqual(self.path.read_text(), original)
        with self.assertRaisesRegex(ValueError, "restore defaults"):
            controller.update({"panel": {"icon_size": 64}})
        self.assertEqual(controller.reset(), DEFAULT_SETTINGS)
        self.assertEqual(json.loads(self.path.read_text()), DEFAULT_SETTINGS)

    def test_parser_accepted_nesting_that_breaks_migration_enters_recovery(self):
        original = '{"a":' * 500 + "0" + "}" * 500
        json.loads(original)
        self.path.write_text(original)
        controller = SettingsController(self.path)
        self.assertTrue(controller.load_errors)
        self.assertIn("migration limit", " ".join(controller.load_errors))
        self.assertEqual(self.path.read_text(), original)
        with self.assertRaisesRegex(ValueError, "restore defaults"):
            controller.update({"panel": {"icon_size": 64}})

    def test_corrupt_input_is_not_echoed_in_errors(self):
        self.path.write_text('{"token":"do-not-print"}')
        controller=SettingsController(self.path)
        self.assertTrue(controller.load_errors); self.assertNotIn("do-not-print"," ".join(controller.load_errors))
    def test_oversized_legacy_file_is_not_migrated_or_rewritten(self):
        original='{"legacy":"' + ("x" * MAX_SETTINGS_BYTES) + '"}'
        self.path.write_text(original)
        controller=SettingsController(self.path)
        self.assertTrue(controller.load_errors); self.assertEqual(self.path.read_text(),original)
    def test_duplicate_legacy_keys_are_not_migrated(self):
        original='{"panel":{"icon_size":48,"icon_size":72}}'
        self.path.write_text(original)
        controller=SettingsController(self.path)
        self.assertTrue(controller.load_errors); self.assertEqual(self.path.read_text(),original)
    def test_symlink_legacy_file_is_not_followed(self):
        target=Path(self.tmp.name)/"target.json"; target.write_text('{"panel":{"icon_size":72}}')
        self.path.symlink_to(target)
        controller=SettingsController(self.path)
        self.assertTrue(controller.load_errors); self.assertEqual(target.read_text(),'{"panel":{"icon_size":72}}')
    def test_explicit_reset_recovers_valid_and_broken_symlinks(self):
        target=Path(self.tmp.name)/"outside.json"
        original='{"panel":{"icon_size":72}}'
        target.write_text(original)
        self.path.symlink_to(target)
        controller=SettingsController(self.path)
        self.assertTrue(controller.load_errors)
        self.assertEqual(controller.reset(),DEFAULT_SETTINGS)
        self.assertFalse(self.path.is_symlink())
        self.assertEqual(target.read_text(),original)
        self.assertEqual(json.loads(self.path.read_text()),DEFAULT_SETTINGS)

        self.path.unlink()
        self.path.symlink_to(Path(self.tmp.name)/"missing-target.json")
        broken=SettingsController(self.path)
        self.assertTrue(broken.load_errors)
        self.assertEqual(broken.reset(),DEFAULT_SETTINGS)
        self.assertFalse(self.path.is_symlink())
        self.assertEqual(json.loads(self.path.read_text()),DEFAULT_SETTINGS)

    def test_invalid_existing_file_requires_explicit_reset_before_update(self):
        original='{"panel":{"edge":"unsafe"}}'; self.path.write_text(original)
        controller=SettingsController(self.path)
        with self.assertRaisesRegex(ValueError,"restore defaults"):
            controller.update({"panel":{"icon_size":64}})
        self.assertEqual(self.path.read_text(),original)
        controller.reset()
        self.assertEqual(json.loads(self.path.read_text()),DEFAULT_SETTINGS)

if __name__ == "__main__": unittest.main()
