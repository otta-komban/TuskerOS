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
