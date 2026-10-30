import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from profile_store import ProfileStore, ProfileStoreError

class ProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "profiles.json"
        self.store = ProfileStore(self.path)
    def tearDown(self):
        self.tmp.cleanup()
    def profile(self, name="Work"):
        return {"name": name, "base_theme": {"id": "classic-glass", "version": "1.0.0"},
                "mixins": ["accent-pack"], "mixin_winners": {"color.accent": "accent-pack"},
                "overrides": {"motion": {"duration_ms": 0}}}
    def test_missing_store_is_empty(self):
        self.assertEqual(self.store.load(), {"format_version": 1, "active_profile": None, "profiles": {}})
    def test_save_reload_and_private_permissions(self):
        self.store.save_profile("work", self.profile())
        self.store.activate_profile("work")
        self.assertEqual(self.store.load()["active_profile"], "work")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
    def test_activation_requires_existing_profile(self):
        with self.assertRaises(ProfileStoreError):
            self.store.activate_profile("missing")
    def test_active_delete_requires_fallback(self):
        self.store.save_profile("work", self.profile())
        self.store.save_profile("study", self.profile("Study"))
        self.store.activate_profile("work")
        with self.assertRaises(ProfileStoreError):
            self.store.delete_profile("work")
        self.store.delete_profile("work", activate_fallback="study")
        self.assertEqual(self.store.load()["active_profile"], "study")
    def test_bad_id_and_unknown_fields_rejected(self):
        with self.assertRaises(ProfileStoreError):
            self.store.save_profile("../bad", self.profile())
        bad = self.profile()
        bad["command"] = "arbitrary"
        with self.assertRaises(ProfileStoreError):
            self.store.save_profile("work", bad)
    def test_duplicate_mixins_rejected(self):
        bad = self.profile()
        bad["mixins"] = ["accent-pack", "accent-pack"]
        with self.assertRaises(ProfileStoreError):
            self.store.save_profile("work", bad)
    def test_winner_must_be_selected_mixin(self):
        bad = self.profile()
        bad["mixin_winners"] = {"color.accent": "not-selected"}
        with self.assertRaises(ProfileStoreError):
            self.store.save_profile("work", bad)
    def test_duplicate_json_keys_rejected(self):
        self.path.write_text('{"format_version":1,"active_profile":null,"profiles":{},"profiles":{}}')
        with self.assertRaises(ProfileStoreError):
            self.store.load()
    def test_symlink_store_rejected(self):
        target = Path(self.tmp.name) / "target.json"
        target.write_text("{}")
        self.path.symlink_to(target)
        with self.assertRaises(ProfileStoreError):
            self.store.load()
    def test_store_size_limit(self):
        self.path.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        with self.assertRaises(ProfileStoreError):
            self.store.load()
    def test_profile_reads_are_copies(self):
        self.store.save_profile("work", self.profile())
        value = self.store.get_profile("work")
        value["overrides"]["motion"]["duration_ms"] = 999
        self.assertEqual(self.store.get_profile("work")["overrides"]["motion"]["duration_ms"], 0)

if __name__ == "__main__":
    unittest.main()
