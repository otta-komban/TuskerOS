import copy
import json
import unittest
from pathlib import Path

from marketplace.tools.validate_catalog_entry import validate_catalog_entry


ROOT = Path(__file__).resolve().parents[1]


class CatalogEntryValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / "examples/hello-catalog-entry.json").read_text())

    def test_example_is_structurally_valid_but_untrusted(self):
        entry = copy.deepcopy(self.fixture)
        self.assertEqual(validate_catalog_entry(entry), [])
        self.assertEqual(entry["trust"]["review_status"], "pending")
        self.assertEqual(entry["trust"]["signature_status"], "unverified")

    def test_conflict_metadata_accepts_unique_package_ids(self):
        entry = copy.deepcopy(self.fixture)
        entry["package"]["conflicts"] = ["org.tuskeros.other.package"]
        self.assertEqual(validate_catalog_entry(entry), [])

    def test_conflict_metadata_rejects_duplicates_and_self_conflicts(self):
        entry = copy.deepcopy(self.fixture)
        entry["package"]["conflicts"] = [
            "org.tuskeros.other.package", "org.tuskeros.other.package"
        ]
        self.assertTrue(any("$.package.conflicts" in e for e in validate_catalog_entry(entry)))
        entry["package"]["conflicts"] = [entry["package"]["id"]]
        self.assertTrue(any("cannot conflict with itself" in e for e in validate_catalog_entry(entry)))

    def test_unknown_field_fails_closed(self):
        entry = copy.deepcopy(self.fixture)
        entry["package"]["install_script"] = "do-not-run"
        self.assertTrue(any("unsupported field" in e for e in validate_catalog_entry(entry)))

    def test_http_artifact_rejected(self):
        entry = copy.deepcopy(self.fixture)
        entry["release"]["artifact_uri"] = "http://example.invalid/a.tar"
        self.assertTrue(any("HTTPS URL" in e for e in validate_catalog_entry(entry)))

    def test_bad_digest_rejected(self):
        entry = copy.deepcopy(self.fixture)
        entry["release"]["sha256"] = "abc"
        self.assertTrue(any("64 hexadecimal" in e for e in validate_catalog_entry(entry)))

    def test_bad_version_rejected(self):
        entry = copy.deepcopy(self.fixture)
        entry["release"]["version"] = "latest"
        self.assertTrue(any("semantic version" in e for e in validate_catalog_entry(entry)))

    def test_semver_rejects_empty_and_leading_zero_prerelease_identifiers(self):
        for version in ("1.2.3-alpha..1", "1.2.3-alpha.", "1.2.3-01", "1.2.3-0.01", "1.٢.3"):
            with self.subTest(version=version):
                entry = copy.deepcopy(self.fixture)
                entry["release"]["version"] = version
                self.assertTrue(any("semantic version" in e for e in validate_catalog_entry(entry)))

    def test_semver_rejects_empty_build_identifiers_but_allows_numeric_leading_zeroes(self):
        for version in ("1.2.3+build..2", "1.2.3+build."):
            with self.subTest(version=version):
                entry = copy.deepcopy(self.fixture)
                entry["release"]["version"] = version
                self.assertTrue(any("semantic version" in e for e in validate_catalog_entry(entry)))
        entry = copy.deepcopy(self.fixture)
        entry["release"]["version"] = "1.2.3-0.alpha-1+build.01"
        self.assertEqual(validate_catalog_entry(entry), [])

    def test_revoked_state_is_valid_metadata_not_authorized(self):
        entry = copy.deepcopy(self.fixture)
        entry["trust"]["review_status"] = "revoked"
        entry["trust"]["signature_status"] = "revoked"
        self.assertEqual(validate_catalog_entry(entry), [])

    def test_invalid_trust_vocabulary_rejected(self):
        entry = copy.deepcopy(self.fixture)
        entry["trust"]["signature_status"] = "trusted"
        self.assertTrue(any("unsupported state" in e for e in validate_catalog_entry(entry)))

    def test_duplicate_tags_rejected(self):
        entry = copy.deepcopy(self.fixture)
        entry["package"]["tags"] = ["same", "same"]
        self.assertTrue(any("$.package.tags" in e for e in validate_catalog_entry(entry)))


if __name__ == "__main__":
    unittest.main()
