import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from token_resolver import TokenResolutionError, resolve_tokens


class TokenResolverTests(unittest.TestCase):
    def test_precedence_and_provenance(self):
        tokens, source = resolve_tokens(
            system_defaults={"color": {"surface": "#fff", "text": "#111"}},
            base_theme={"color": {"surface": "#eee"}},
            mixins={"pack.spacing": {"space": {"small": 4}}},
            profile_overrides={"color": {"surface": "#ddd"}},
            user_overrides={"color": {"text": "#222"}},
            enforced_overrides={"color": {"text": "#000"}},
        )
        self.assertEqual(tokens["color"], {"surface": "#ddd", "text": "#000"})
        self.assertEqual(tokens["space"]["small"], 4)
        self.assertEqual(source["color.surface"], "profile")
        self.assertEqual(source["color.text"], "enforced-policy")
        self.assertEqual(source["space.small"], "mixin:pack.spacing")

    def test_disjoint_mixins_are_order_independent(self):
        args = dict(system_defaults={}, base_theme={})
        a, _ = resolve_tokens(**args, mixins={"z": {"b": 2}, "a": {"a": 1}})
        b, _ = resolve_tokens(**args, mixins={"a": {"a": 1}, "z": {"b": 2}})
        self.assertEqual(a, b)

    def test_conflicting_mixins_require_explicit_winner(self):
        with self.assertRaisesRegex(TokenResolutionError, "explicit winner"):
            resolve_tokens(system_defaults={}, base_theme={},
                           mixins={"one": {"color": {"accent": "red"}},
                                   "two": {"color": {"accent": "blue"}}})

    def test_explicit_mixin_winner_is_stable(self):
        tokens, source = resolve_tokens(
            system_defaults={}, base_theme={},
            mixins={"one": {"color": {"accent": "red"}},
                    "two": {"color": {"accent": "blue"}}},
            mixin_winners={"color.accent": "two"})
        self.assertEqual(tokens["color"]["accent"], "blue")
        self.assertEqual(source["color.accent"], "mixin:two")

    def test_unknown_winner_does_not_silently_choose(self):
        with self.assertRaises(TokenResolutionError):
            resolve_tokens(system_defaults={}, base_theme={},
                           mixins={"one": {"x": 1}, "two": {"x": 2}},
                           mixin_winners={"x": "missing"})

    def test_inputs_are_not_mutated(self):
        base = {"nested": {"value": [1, 2]}}
        before = {"nested": {"value": [1, 2]}}
        resolve_tokens(system_defaults={}, base_theme=base)
        self.assertEqual(base, before)

    def test_enforced_policy_is_last_and_cannot_be_weakened_by_user(self):
        tokens, source = resolve_tokens(
            system_defaults={"motion": {"duration_ms": 200}},
            base_theme={}, user_overrides={"motion": {"duration_ms": 900}},
            enforced_overrides={"motion": {"duration_ms": 0}})
        self.assertEqual(tokens["motion"]["duration_ms"], 0)
        self.assertEqual(source["motion.duration_ms"], "enforced-policy")

    def test_invalid_mapping_is_rejected(self):
        with self.assertRaises(TokenResolutionError):
            resolve_tokens(system_defaults=[], base_theme={})


if __name__ == "__main__":
    unittest.main()
