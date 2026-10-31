import copy
import json
import unittest
from pathlib import Path

from marketplace.tools.catalog_resolver import (
    CatalogResolutionError,
    is_compatible,
    parse_release_version,
    resolve_catalog_plan,
    select_catalog_release,
)

ROOT = Path(__file__).resolve().parents[1]


class CatalogResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / "examples/hello-catalog-entry.json").read_text())

    def candidate(self, version, *, os_min="0.1.0", os_max="0.x", api_min="1.0", api_max="1.x"):
        item = copy.deepcopy(self.fixture)
        item["release"]["version"] = version
        item["compatibility"]["tuskeros"] = {"min": os_min, "max": os_max}
        item["compatibility"]["api"] = {"min": api_min, "max": api_max}
        return item

    def test_direct_release_parser_enforces_strict_ascii_semver(self):
        for value in (
            "1.2.3-alpha..1", "1.2.3-alpha.", "1.2.3-01",
            "1.2.3+build..2", "1.2.3+build.", "1.٢.3",
        ):
            with self.subTest(value=value):
                with self.assertRaises(CatalogResolutionError):
                    parse_release_version(value)
        self.assertEqual(parse_release_version("1.2.3-0.alpha+build.01"), parse_release_version("1.2.3-0.alpha+build.02"))

    def test_compatibility_parser_rejects_unicode_digits(self):
        from marketplace.tools.catalog_resolver import parse_compat_version
        with self.assertRaises(CatalogResolutionError):
            parse_compat_version("1.٢.3")

    def test_compatibility_parser_enforces_schema_length_bound(self):
        from marketplace.tools.catalog_resolver import parse_compat_version
        self.assertEqual(parse_compat_version("1" * 64).major, int("1" * 64))
        for value in ("", "1" * 65):
            with self.subTest(value_length=len(value)):
                with self.assertRaisesRegex(CatalogResolutionError, "max 64"):
                    parse_compat_version(value)

    def test_direct_release_parser_enforces_schema_length_bound(self):
        from marketplace.tools.catalog_resolver import parse_release_version
        maximum = "1" * 124 + ".0.0"
        self.assertEqual(len(maximum), 128)
        self.assertEqual(parse_release_version(maximum).major, int("1" * 124))
        with self.assertRaisesRegex(CatalogResolutionError, "max 128"):
            parse_release_version("1" * 125 + ".0.0")

    def test_release_versions_order_numerically(self):
        self.assertLess(parse_release_version("1.9.0"), parse_release_version("1.10.0"))

    def test_semver_prerelease_precedence_follows_specification(self):
        versions = (
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.beta",
            "1.0.0-beta",
            "1.0.0-beta.2",
            "1.0.0-beta.11",
            "1.0.0-rc.1",
            "1.0.0",
        )
        parsed = [parse_release_version(value) for value in versions]
        self.assertEqual(parsed, sorted(parsed))

    def test_dependency_constraint_parser_enforces_512_character_bound(self):
        from marketplace.tools.catalog_resolver import parse_dependency_constraint
        long_clause = ">=" + "1" * 124 + ".0.0"
        boundary = ",".join((long_clause, long_clause, long_clause, ">=" + "1" * 113 + ".0.0"))
        self.assertEqual(len(boundary), 512)
        self.assertEqual(len(parse_dependency_constraint(boundary)), 4)
        with self.assertRaisesRegex(CatalogResolutionError, "max 512"):
            parse_dependency_constraint(boundary + " ")

    def test_dependency_constraint_operators_are_inclusive_or_exclusive_as_named(self):
        from marketplace.tools.catalog_resolver import satisfies_dependency_constraints
        self.assertTrue(satisfies_dependency_constraints("1.2.0", [">=1.2.0", "<=1.2.0"]))
        self.assertFalse(satisfies_dependency_constraints("1.2.0", [">1.2.0"]))
        self.assertFalse(satisfies_dependency_constraints("1.2.0", ["<1.2.0"]))
        self.assertTrue(satisfies_dependency_constraints("1.2.1", [">1.2.0", "<2.0.0"]))
        self.assertTrue(satisfies_dependency_constraints("1.1.9", ["<=1.2.0", ">=1.0.0"]))

    def test_dependency_constraint_rejects_empty_or_malformed_clauses(self):
        from marketplace.tools.catalog_resolver import parse_dependency_constraint
        for constraint in ("", ",>=1.0.0", ">=1.0.0,", ">=1.0.0,,<2.0.0", "=>1.0.0"):
            with self.subTest(constraint=constraint):
                with self.assertRaises(CatalogResolutionError):
                    parse_dependency_constraint(constraint)

    def test_constraint_satisfaction_normalizes_malformed_public_inputs(self):
        from marketplace.tools.catalog_resolver import Version, satisfies_dependency_constraints
        for version, constraints in (
            (None, []),
            ("1.0.0", None),
            ("1.0.0", ">=1.0.0"),
            ("1.0.0", 7),
            (Version(-1, 0, 0), []),
            (Version(True, 0, 0), []),
            (Version(1, 0, 0, ("01",)), []),
            (Version(1, 0, 0, ["alpha"]), []),
        ):
            with self.subTest(version=version, constraints=constraints):
                with self.assertRaises(CatalogResolutionError):
                    satisfies_dependency_constraints(version, constraints)

    def test_constraint_satisfaction_accepts_valid_version_objects_and_generators(self):
        from marketplace.tools.catalog_resolver import Version, satisfies_dependency_constraints
        self.assertTrue(satisfies_dependency_constraints(
            Version(1, 2, 3, ("alpha",)), (item for item in (">=1.2.3-alpha", "<2.0.0"))
        ))

    def test_prerelease_sorts_before_stable(self):
        self.assertLess(parse_release_version("2.0.0-rc.1"), parse_release_version("2.0.0"))

    def test_selects_highest_compatible_stable(self):
        older = self.candidate("0.8.0")
        newer = self.candidate("0.10.0")
        prerelease = self.candidate("0.11.0-beta.1")
        chosen = select_catalog_release(
            [older, newer, prerelease], "org.tuskeros.examples.hello", "0.5.0", "1.2.0"
        )
        self.assertEqual(chosen["release"]["version"], "0.10.0")

    def test_selector_reuses_generator_constraints_for_every_candidate(self):
        older = self.candidate("1.5.0")
        newer = self.candidate("2.5.0")
        chosen = select_catalog_release(
            [older, newer], "org.tuskeros.examples.hello", "0.5.0", "1.2.0",
            version_constraints=(item for item in ("<2.0.0",)),
        )
        self.assertEqual(chosen["release"]["version"], "1.5.0")

    def test_selector_rejects_malformed_public_collections_and_flags(self):
        valid = self.candidate("1.0.0")
        for candidates, package_id, constraints, prerelease in (
            ("not-a-list", "org.tuskeros.examples.hello", (), False),
            ({"entry": valid}, "org.tuskeros.examples.hello", (), False),
            ([valid], "", (), False),
            ([valid], "org.tuskeros.examples.hello", ">=1.0.0", False),
            ([valid], "org.tuskeros.examples.hello", {}, False),
            ([valid], "org.tuskeros.examples.hello", (), "yes"),
            ([None], "org.tuskeros.examples.hello", (), False),
        ):
            with self.subTest(candidates=candidates, package_id=package_id):
                with self.assertRaises(CatalogResolutionError):
                    select_catalog_release(
                        candidates, package_id, "0.5.0", "1.2.0",
                        version_constraints=constraints, include_prerelease=prerelease,
                    )

    def test_selector_rejects_invalid_target_versions_even_without_candidates(self):
        with self.assertRaises(CatalogResolutionError):
            select_catalog_release(
                [], "org.tuskeros.examples.hello", "not-a-version", "1.2.0"
            )

    def test_excludes_incompatible_release(self):
        candidate = self.candidate("1.0.0", os_min="1.0.0", os_max="1.x")
        with self.assertRaisesRegex(CatalogResolutionError, "no compatible"):
            select_catalog_release(
                [candidate], "org.tuskeros.examples.hello", "0.9.0", "1.2.0"
            )

    def test_wildcard_maximum_matches_major_only(self):
        candidate = self.candidate("1.0.0", os_min="1.0.0", os_max="1.x")
        self.assertTrue(is_compatible(candidate, "1.99.99", "1.2.0"))
        self.assertFalse(is_compatible(candidate, "2.0.0", "1.2.0"))

    def test_wildcard_maximum_obeys_compatibility_length_bound(self):
        oversized = "9" * 63 + ".x"
        candidate = self.candidate("1.0.0", os_min="1.0.0", os_max=oversized)
        with self.assertRaisesRegex(CatalogResolutionError, "max 64"):
            is_compatible(candidate, "1.0.0", "1.2.0")

    def test_prerelease_opt_in(self):
        candidate = self.candidate("0.12.0-rc.1")
        with self.assertRaises(CatalogResolutionError):
            select_catalog_release(
                [candidate], "org.tuskeros.examples.hello", "0.5.0", "1.2.0"
            )
        chosen = select_catalog_release(
            [candidate], "org.tuskeros.examples.hello", "0.5.0", "1.2.0",
            include_prerelease=True,
        )
        self.assertEqual(chosen["release"]["version"], "0.12.0-rc.1")

    def test_equal_precedence_builds_are_ambiguous(self):
        a = self.candidate("1.0.0+build.1")
        b = self.candidate("1.0.0+build.2")
        with self.assertRaisesRegex(CatalogResolutionError, "ambiguous"):
            select_catalog_release(
                [a, b], "org.tuskeros.examples.hello", "0.5.0", "1.2.0"
            )

    def test_revoked_release_is_never_selected(self):
        candidate = self.candidate("1.0.0")
        candidate["trust"]["review_status"] = "revoked"
        with self.assertRaisesRegex(CatalogResolutionError, "no compatible release"):
            select_catalog_release(
                [candidate], "org.tuskeros.examples.hello", "0.5.0", "1.2.0"
            )

    def test_revoked_signature_is_never_selected(self):
        candidate = self.candidate("1.0.0")
        candidate["trust"]["signature_status"] = "revoked"
        with self.assertRaisesRegex(CatalogResolutionError, "no compatible release"):
            select_catalog_release(
                [candidate], "org.tuskeros.examples.hello", "0.5.0", "1.2.0"
            )

    def test_rejected_and_quarantined_releases_are_excluded(self):
        for status in ("rejected", "quarantined"):
            with self.subTest(status=status):
                candidate = self.candidate("1.0.0")
                candidate["trust"]["review_status"] = status
                with self.assertRaisesRegex(CatalogResolutionError, "no compatible release"):
                    select_catalog_release(
                        [candidate], "org.tuskeros.examples.hello", "0.5.0", "1.2.0"
                    )

    def test_invalid_matching_metadata_fails_closed(self):
        candidate = self.candidate("1.0.0")
        candidate["release"]["artifact_uri"] = "http://bad.invalid/file"
        with self.assertRaisesRegex(CatalogResolutionError, "invalid catalog entry"):
            select_catalog_release(
                [candidate], "org.tuskeros.examples.hello", "0.5.0", "1.2.0"
            )

    def test_dependency_plan_selects_each_package_and_orders(self):
        app = self.candidate("1.0.0")
        app["package"]["id"] = "org.tuskeros.apps.demo"
        lib = self.candidate("2.0.0")
        lib["package"]["id"] = "org.tuskeros.libs.core"
        plan = resolve_catalog_plan(
            ["org.tuskeros.apps.demo"],
            [app, lib],
            {"org.tuskeros.apps.demo": ["org.tuskeros.libs.core"],
             "org.tuskeros.libs.core": []},
            "0.5.0",
            "1.2.0",
        )
        self.assertEqual(
            plan["order"],
            ["org.tuskeros.libs.core", "org.tuskeros.apps.demo"],
        )
        self.assertEqual(plan["releases"]["org.tuskeros.libs.core"]["release"]["version"], "2.0.0")

    def test_catalog_plan_rejects_malformed_root_inputs(self):
        for roots in ("org.tuskeros.apps.demo", [["bad"]], None):
            with self.subTest(roots=roots):
                with self.assertRaises(CatalogResolutionError):
                    resolve_catalog_plan(roots, [], {}, "0.5.0", "1.2.0")

    def test_catalog_plan_rejects_malformed_candidate_collection(self):
        for candidates in ("not-a-candidate-list", {"entry": {}}, None):
            with self.subTest(candidates=candidates):
                with self.assertRaises(CatalogResolutionError):
                    resolve_catalog_plan(
                        ["org.tuskeros.apps.demo"], candidates,
                        {"org.tuskeros.apps.demo": []}, "0.5.0", "1.2.0"
                    )

    def test_catalog_plan_rejects_non_mapping_dependency_constraints(self):
        for constraints in ([], "not-a-mapping", None):
            if constraints is None:
                continue  # None explicitly means constraints are omitted.
            with self.subTest(constraints=constraints):
                with self.assertRaisesRegex(CatalogResolutionError, "dependency_constraints must be a mapping"):
                    resolve_catalog_plan(
                        ["org.tuskeros.apps.demo"], [],
                        {"org.tuskeros.apps.demo": []}, "0.5.0", "1.2.0",
                        dependency_constraints=constraints,
                    )

    def test_catalog_plan_rejects_invalid_constraint_parent_id(self):
        with self.assertRaisesRegex(CatalogResolutionError, "parent IDs"):
            resolve_catalog_plan(
                ["org.tuskeros.apps.demo"], [],
                {"org.tuskeros.apps.demo": []}, "0.5.0", "1.2.0",
                dependency_constraints={"": {}},
            )

    def test_catalog_plan_rejects_malformed_dependency_graph(self):
        invalid_graphs = (
            [],
            {"org.tuskeros.apps.demo": "org.tuskeros.libs.core"},
            {"org.tuskeros.apps.demo": [None]},
            {"": []},
            {"org.tuskeros.apps.demo": None},
        )
        for graph in invalid_graphs:
            with self.subTest(graph=graph):
                with self.assertRaises(CatalogResolutionError):
                    resolve_catalog_plan(
                        ["org.tuskeros.apps.demo"], [], graph, "0.5.0", "1.2.0"
                    )

    def test_missing_candidate_blocks_plan(self):
        with self.assertRaises(CatalogResolutionError):
            resolve_catalog_plan(
                ["org.tuskeros.apps.missing"], [],
                {"org.tuskeros.apps.missing": []}, "0.5.0", "1.2.0"
            )

    def test_dependency_constraint_selects_matching_release(self):
        app = self.candidate("1.0.0")
        app["package"]["id"] = "org.tuskeros.apps.demo"
        old = self.candidate("1.5.0")
        old["package"]["id"] = "org.tuskeros.libs.core"
        new = self.candidate("2.4.0")
        new["package"]["id"] = "org.tuskeros.libs.core"
        plan = resolve_catalog_plan(
            ["org.tuskeros.apps.demo"], [app, old, new],
            {"org.tuskeros.apps.demo": ["org.tuskeros.libs.core"],
             "org.tuskeros.libs.core": []},
            "0.5.0", "1.2.0",
            dependency_constraints={"org.tuskeros.apps.demo": {
                "org.tuskeros.libs.core": ">=1.0.0,<2.0.0"
            }},
        )
        self.assertEqual(plan["releases"]["org.tuskeros.libs.core"]["release"]["version"], "1.5.0")

    def test_conflicting_dependency_constraints_fail_closed(self):
        app = self.candidate("1.0.0")
        app["package"]["id"] = "org.tuskeros.apps.demo"
        lib = self.candidate("1.8.0")
        lib["package"]["id"] = "org.tuskeros.libs.core"
        with self.assertRaisesRegex(CatalogResolutionError, "no compatible release"):
            resolve_catalog_plan(
                ["org.tuskeros.apps.demo"], [app, lib],
                {"org.tuskeros.apps.demo": ["org.tuskeros.libs.core"],
                 "org.tuskeros.libs.core": []},
                "0.5.0", "1.2.0",
                dependency_constraints={"org.tuskeros.apps.demo": {
                    "org.tuskeros.libs.core": ">=2.0.0,<2.0.0"
                }},
            )

    def test_missing_dependency_constraint_fails_closed(self):
        with self.assertRaisesRegex(CatalogResolutionError, "match declared dependency edges"):
            resolve_catalog_plan(
                ["org.tuskeros.apps.demo"], [],
                {"org.tuskeros.apps.demo": ["org.tuskeros.libs.core"],
                 "org.tuskeros.libs.core": []},
                "0.5.0", "1.2.0",
                dependency_constraints={"org.tuskeros.apps.demo": {}},
            )

    def test_constraints_from_multiple_parents_are_intersected(self):
        root = self.candidate("1.0.0")
        root["package"]["id"] = "org.tuskeros.apps.root"
        left = self.candidate("1.0.0")
        left["package"]["id"] = "org.tuskeros.apps.left"
        right = self.candidate("1.0.0")
        right["package"]["id"] = "org.tuskeros.apps.right"
        lib = self.candidate("1.8.0")
        lib["package"]["id"] = "org.tuskeros.libs.shared"
        lib_new = self.candidate("2.2.0")
        lib_new["package"]["id"] = "org.tuskeros.libs.shared"
        graph = {
            "org.tuskeros.apps.root": ["org.tuskeros.apps.left", "org.tuskeros.apps.right"],
            "org.tuskeros.apps.left": ["org.tuskeros.libs.shared"],
            "org.tuskeros.apps.right": ["org.tuskeros.libs.shared"],
            "org.tuskeros.libs.shared": [],
        }
        constraints = {
            "org.tuskeros.apps.root": {
                "org.tuskeros.apps.left": ">=1.0.0",
                "org.tuskeros.apps.right": ">=1.0.0",
            },
            "org.tuskeros.apps.left": {"org.tuskeros.libs.shared": ">=1.5.0"},
            "org.tuskeros.apps.right": {"org.tuskeros.libs.shared": "<2.0.0"},
        }
        plan = resolve_catalog_plan(
            ["org.tuskeros.apps.root"], [root, left, right, lib, lib_new],
            graph, "0.5.0", "1.2.0", dependency_constraints=constraints,
        )
        self.assertEqual(plan["releases"]["org.tuskeros.libs.shared"]["release"]["version"], "1.8.0")

    def test_declared_package_conflict_blocks_resolved_plan(self):
        app = self.candidate("1.0.0")
        app["package"]["id"] = "org.tuskeros.apps.demo"
        app["package"]["conflicts"] = ["org.tuskeros.libs.core"]
        lib = self.candidate("1.0.0")
        lib["package"]["id"] = "org.tuskeros.libs.core"
        with self.assertRaisesRegex(CatalogResolutionError, "package conflict"):
            resolve_catalog_plan(
                ["org.tuskeros.apps.demo"], [app, lib],
                {"org.tuskeros.apps.demo": ["org.tuskeros.libs.core"],
                 "org.tuskeros.libs.core": []},
                "0.5.0", "1.2.0",
            )

    def test_conflict_declared_by_either_package_is_enforced(self):
        root = self.candidate("1.0.0")
        root["package"]["id"] = "org.tuskeros.apps.root"
        dependency = self.candidate("1.0.0")
        dependency["package"]["id"] = "org.tuskeros.libs.core"
        dependency["package"]["conflicts"] = ["org.tuskeros.apps.root"]
        with self.assertRaisesRegex(CatalogResolutionError, "package conflict"):
            resolve_catalog_plan(
                ["org.tuskeros.apps.root"], [root, dependency],
                {"org.tuskeros.apps.root": ["org.tuskeros.libs.core"],
                 "org.tuskeros.libs.core": []},
                "0.5.0", "1.2.0",
            )

    def test_malformed_dependency_constraint_is_rejected(self):
        with self.assertRaisesRegex(CatalogResolutionError, "invalid dependency version constraint"):
            resolve_catalog_plan(
                ["org.tuskeros.apps.demo"], [],
                {"org.tuskeros.apps.demo": ["org.tuskeros.libs.core"],
                 "org.tuskeros.libs.core": []}, "0.5.0", "1.2.0",
                dependency_constraints={"org.tuskeros.apps.demo": {
                    "org.tuskeros.libs.core": "latest"
                }},
            )


if __name__ == "__main__":
    unittest.main()
