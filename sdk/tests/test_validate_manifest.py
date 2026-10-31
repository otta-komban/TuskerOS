"""Unit tests for the TuskerOS extension manifest validator."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_manifest", ROOT / "tools" / "validate_manifest.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
EXAMPLE = json.loads((ROOT / "examples" / "hello-extension" / "manifest.json").read_text())


class ManifestValidatorTests(unittest.TestCase):
    def test_example_manifest_is_valid(self):
        self.assertEqual(validator.validate(EXAMPLE), [])

    def test_rejects_non_object_root(self):
        self.assertTrue(validator.validate([]))

    def test_rejects_unknown_fields(self):
        data = dict(EXAMPLE, execute="do-not-run")
        self.assertTrue(any("unknown fields" in e for e in validator.validate(data)))

    def test_rejects_invalid_reverse_dns_id(self):
        data = dict(EXAMPLE, id="../escape")
        self.assertTrue(any("id must" in e for e in validator.validate(data)))

    def test_rejects_duplicate_permissions(self):
        data = dict(EXAMPLE, permissions=["files.read", "files.read"])
        self.assertTrue(any("duplicates" in e for e in validator.validate(data)))

    def test_accepts_valid_semver_prerelease_and_build_metadata(self):
        for version in ("1.2.3-alpha.1", "1.2.3-0", "1.2.3-alpha+build.7"):
            with self.subTest(version=version):
                self.assertEqual(validator.validate(dict(EXAMPLE, version=version)), [])

    def test_rejects_malformed_semver_identifiers(self):
        for version in ("1.2.3-alpha..1", "1.2.3-alpha.", "1.2.3-01", "1.2.3+build..7", "1.2.3+"):
            with self.subTest(version=version):
                self.assertTrue(any("semantic version" in e for e in validator.validate(dict(EXAMPLE, version=version))))

    def test_dependency_constraint_obeys_512_character_bound(self):
        valid = dict(EXAMPLE, dependencies=[{"id": "org.tuskeros.example.dep", "version": "x" * 512}])
        self.assertEqual(validator.validate(valid), [])
        oversized = dict(EXAMPLE, dependencies=[{"id": "org.tuskeros.example.dep", "version": "x" * 513}])
        self.assertTrue(any("at most 512" in e for e in validator.validate(oversized)))

    def test_rejects_malformed_dependency(self):
        data = dict(EXAMPLE, dependencies=[{"id": "bad", "version": "*"}])
        self.assertTrue(validator.validate(data))

    def test_rejects_non_https_artifact(self):
        data = dict(EXAMPLE, artifacts=[{"uri": "http://example.invalid/pkg", "sha256": "a" * 64}])
        self.assertTrue(any("HTTPS" in e for e in validator.validate(data)))

    def test_rejects_bad_digest(self):
        data = dict(EXAMPLE, artifacts=[{"uri": "https://example.invalid/pkg", "sha256": "not-a-digest"}])
        self.assertTrue(any("64 hexadecimal" in e for e in validator.validate(data)))


if __name__ == "__main__":
    unittest.main()
