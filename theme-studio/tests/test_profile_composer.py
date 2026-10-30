import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))
from profile_store import ProfileStore
from profile_composer import ProfileCompositionError, compose_profile


class ProfileComposerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProfileStore(Path(self.tmp.name) / "profiles.json")
        self.profile = {
            "name": "Work",
            "base_theme": {"id": "classic-glass", "version": "1.0.0"},
            "mixins": ["accent-pack", "spacing-pack"],
            "mixin_winners": {"colors.accent": "accent-pack"},
            "overrides": {"colors": {"background": "#eeeeee"}, "spacing": {"normal": 12}},
        }
        self.store.save_profile("work", self.profile)
        self.catalog = {
            "classic-glass": {"kind": "theme", "version": "1.0.0",
                              "tokens": {"colors": {"background": "#ffffff", "foreground": "#111111"}}},
            "accent-pack": {"kind": "mixin", "version": "2.0.0",
                            "tokens": {"colors": {"accent": "#ff0000"}}},
            "spacing-pack": {"kind": "mixin", "version": "1.2.0",
                             "tokens": {"spacing": {"normal": 8, "large": 24}}},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_composes_active_profile_and_reports_provenance(self):
        self.store.activate_profile("work")
        result = compose_profile(self.store, self.catalog)
        self.assertEqual(result.profile_id, "work")
        self.assertEqual(result.base_theme_version, "1.0.0")
        self.assertEqual(result.tokens["colors"]["background"], "#eeeeee")
        self.assertEqual(result.tokens["colors"]["accent"], "#ff0000")
        self.assertEqual(result.tokens["spacing"]["normal"], 12)
        self.assertEqual(result.provenance["colors.background"], "profile")
        self.assertEqual(result.provenance["colors.accent"], "mixin:accent-pack")

    def test_named_profile_does_not_require_activation(self):
        result = compose_profile(self.store, self.catalog, profile_id="work")
        self.assertEqual(result.profile_id, "work")

    def test_no_active_profile_is_rejected(self):
        with self.assertRaisesRegex(ProfileCompositionError, "no active profile"):
            compose_profile(self.store, self.catalog)

    def test_unknown_profile_is_rejected(self):
        with self.assertRaisesRegex(ProfileCompositionError, "unknown profile"):
            compose_profile(self.store, self.catalog, profile_id="missing")

    def test_missing_base_pack_is_rejected(self):
        catalog = deepcopy(self.catalog)
        del catalog["classic-glass"]
        with self.assertRaisesRegex(ProfileCompositionError, "not installed"):
            compose_profile(self.store, catalog, profile_id="work")

    def test_wrong_pinned_base_version_is_rejected(self):
        catalog = deepcopy(self.catalog)
        catalog["classic-glass"]["version"] = "1.1.0"
        with self.assertRaisesRegex(ProfileCompositionError, "version mismatch"):
            compose_profile(self.store, catalog, profile_id="work")

    def test_missing_or_wrong_kind_mixin_is_rejected(self):
        catalog = deepcopy(self.catalog)
        del catalog["spacing-pack"]
        with self.assertRaisesRegex(ProfileCompositionError, "not installed"):
            compose_profile(self.store, catalog, profile_id="work")
        catalog["spacing-pack"] = {"kind": "theme", "version": "1.2.0", "tokens": {}}
        with self.assertRaisesRegex(ProfileCompositionError, "kind mixin"):
            compose_profile(self.store, catalog, profile_id="work")

    def test_unresolved_mixin_conflict_is_rejected(self):
        catalog = deepcopy(self.catalog)
        catalog["spacing-pack"]["tokens"] = {"colors": {"accent": "#00ff00"}}
        with self.assertRaisesRegex(ProfileCompositionError, "explicit winner"):
            compose_profile(self.store, catalog, profile_id="work")

    def test_stale_or_misdirected_winner_is_rejected(self):
        profile = deepcopy(self.profile)
        profile["mixin_winners"] = {"colors.background": "accent-pack"}
        self.store.save_profile("work", profile)
        with self.assertRaisesRegex(ProfileCompositionError, "does not define"):
            compose_profile(self.store, self.catalog, profile_id="work")

    def test_user_override_applies_but_enforced_override_wins(self):
        result = compose_profile(
            self.store, self.catalog, profile_id="work",
            user_overrides={"colors": {"foreground": "#222222"}, "spacing": {"normal": 99}},
            enforced_overrides={"spacing": {"normal": 0}},
        )
        self.assertEqual(result.tokens["colors"]["foreground"], "#222222")
        self.assertEqual(result.tokens["spacing"]["normal"], 0)
        self.assertEqual(result.provenance["spacing.normal"], "enforced-policy")

    def test_catalog_and_profile_inputs_are_not_mutated(self):
        catalog_before = deepcopy(self.catalog)
        profile_before = deepcopy(self.profile)
        compose_profile(self.store, self.catalog, profile_id="work",
                        user_overrides={"extra": {"value": [1, 2]}})
        self.assertEqual(self.catalog, catalog_before)
        self.assertEqual(self.store.get_profile("work"), profile_before)

    def test_deterministic_output_for_catalog_insertion_order(self):
        reversed_catalog = dict(reversed(list(self.catalog.items())))
        first = compose_profile(self.store, self.catalog, profile_id="work")
        second = compose_profile(self.store, reversed_catalog, profile_id="work")
        self.assertEqual(first.tokens, second.tokens)
        self.assertEqual(first.provenance, second.provenance)


if __name__ == "__main__":
    unittest.main()
