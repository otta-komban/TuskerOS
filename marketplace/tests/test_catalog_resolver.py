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

    def test_release_versions_order_numerically(self):
        self.assertLess(parse_release_version("1.9.0"), parse_release_version("1.10.0"))

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

    def test_missing_candidate_blocks_plan(self):
        with self.assertRaises(CatalogResolutionError):
            resolve_catalog_plan(
                ["org.tuskeros.apps.missing"], [],
                {"org.tuskeros.apps.missing": []}, "0.5.0", "1.2.0"
            )


if __name__ == "__main__":
    unittest.main()
