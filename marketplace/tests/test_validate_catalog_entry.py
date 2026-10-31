import copy
import json
import re
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


    def test_malformed_and_whitespace_urls_fail_closed_without_exception(self):
        for value in ("https://[broken/path", "https://example.invalid:bad/file", "https://example.invalid/a b", "https://example.invalid/a\x7fb", "https://example.invalid/a\u0085b"):
            with self.subTest(value=value):
                entry = copy.deepcopy(self.fixture)
                entry["release"]["artifact_uri"] = value
                errors = validate_catalog_entry(entry)
                self.assertTrue(any("$.release.artifact_uri" in e for e in errors))

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


    def test_package_and_publisher_identifiers_use_ascii_slug_grammar(self):
        for section, field, invalid in (
            ("package", "id", "Org.Tuskeros.Package"),
            ("publisher", "id", "publisher name"),
            ("package", "id", "x"),
            ("publisher", "id", "x"),
            ("package", "id", "ümlaut.package"),
        ):
            with self.subTest(section=section, invalid=invalid):
                entry = copy.deepcopy(self.fixture)
                entry[section][field] = invalid
                self.assertTrue(any(f"$.{section}.{field}" in e for e in validate_catalog_entry(entry)))

    def test_schema_https_patterns_reject_whitespace_anywhere_in_url(self):
        schema = json.loads((ROOT / "schemas/catalog-entry.schema.json").read_text())
        url_locations = (
            schema["properties"]["package"]["properties"]["description_uri"],
            schema["properties"]["publisher"]["properties"]["homepage"],
            schema["properties"]["release"]["properties"]["manifest_uri"],
            schema["properties"]["release"]["properties"]["artifact_uri"],
            schema["properties"]["release"]["properties"]["signature_uri"],
            schema["properties"]["release"]["properties"]["changelog_uri"],
        )
        for definition in url_locations:
            pattern = re.compile(definition["pattern"])
            for value in ("https://example.invalid/a b", "https://example.invalid/\tpath", "https://example.invalid/a\x7fb", "https://example.invalid/a\u0085b"):
                with self.subTest(value=value, pattern=definition["pattern"]):
                    self.assertIsNone(pattern.fullmatch(value))
            self.assertIsNotNone(pattern.fullmatch("https://example.invalid/a%20b"))

    def test_optional_metadata_urls_require_https(self):
        for section, field in (
            ("package", "description_uri"),
            ("publisher", "homepage"),
            ("release", "signature_uri"),
            ("release", "changelog_uri"),
        ):
            with self.subTest(section=section, field=field):
                entry = copy.deepcopy(self.fixture)
                entry[section][field] = "http://example.invalid/resource"
                self.assertTrue(any(f"$.{section}.{field}" in e for e in validate_catalog_entry(entry)))


    def test_whitespace_only_text_and_oversized_compatibility_ranges_rejected(self):
        entry = copy.deepcopy(self.fixture)
        entry["package"]["name"] = "   "
        self.assertTrue(any("$.package.name" in e for e in validate_catalog_entry(entry)))
        entry = copy.deepcopy(self.fixture)
        entry["compatibility"]["api"]["min"] = "x" * 65
        self.assertTrue(any("$.compatibility.api.min" in e for e in validate_catalog_entry(entry)))

    def test_compatibility_ranges_reject_unknown_fields(self):
        entry = copy.deepcopy(self.fixture)
        entry["compatibility"]["api"]["unexpected"] = "1.0"
        self.assertTrue(any("$.compatibility.api.unexpected" in e for e in validate_catalog_entry(entry)))


    def test_timestamps_require_rfc3339_timezone_and_calendar_validity(self):
        for value in ("2026-10-31 00:00:00Z", "2026-10-31T00:00:00", "2026-02-30T00:00:00Z", "2026-10-31T00:00:00+0530"):
            with self.subTest(value=value):
                entry = copy.deepcopy(self.fixture)
                entry["release"]["published_at"] = value
                self.assertTrue(any("$.release.published_at" in e for e in validate_catalog_entry(entry)))
        for value in ("2026-10-31T00:00:00Z", "2026-10-31t05:30:00+05:30", "2026-10-31T00:00:00.123456-04:00"):
            with self.subTest(value=value):
                entry = copy.deepcopy(self.fixture)
                entry["release"]["published_at"] = value
                self.assertEqual(validate_catalog_entry(entry), [])

    def test_review_timestamp_uses_same_rfc3339_rules(self):
        entry = copy.deepcopy(self.fixture)
        entry["trust"]["reviewed_at"] = "2026-10-31 00:00:00+00:00"
        self.assertTrue(any("$.trust.reviewed_at" in e for e in validate_catalog_entry(entry)))


    def test_semver_length_matches_validator_bound(self):
        entry = copy.deepcopy(self.fixture)
        entry["release"]["version"] = "1.2.3+" + ("a" * 123)
        self.assertTrue(any("$.release.version" in e for e in validate_catalog_entry(entry)))

    def test_categories_and_tags_reject_whitespace_only_values(self):
        for field in ("categories", "tags"):
            with self.subTest(field=field):
                entry = copy.deepcopy(self.fixture)
                entry["package"][field] = ["   "]
                self.assertTrue(any(f"$.package.{field}" in e for e in validate_catalog_entry(entry)))

    def test_duplicate_tags_rejected(self):
        entry = copy.deepcopy(self.fixture)
        entry["package"]["tags"] = ["same", "same"]
        self.assertTrue(any("$.package.tags" in e for e in validate_catalog_entry(entry)))


    def test_schema_anchored_patterns_reject_trailing_line_terminators(self):
        schema = json.loads((ROOT / "schemas/catalog-entry.schema.json").read_text())
        samples = (
            ("^[a-z0-9]", "valid-id"),
            ("^(0|[1-9]", "1.2.3"),
            ("^[a-fA-F0-9]", "a" * 64),
            ("^[0-9]{4}-", "2026-10-31T00:00:00Z"),
            ("^https://", "https://example.invalid/path"),
        )

        def patterns(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "pattern" and isinstance(item, str):
                        yield item
                    else:
                        yield from patterns(item)
            elif isinstance(value, list):
                for item in value:
                    yield from patterns(item)

        for pattern in patterns(schema):
            if pattern.startswith("^"):
                sample = next((sample for prefix, sample in samples if pattern.startswith(prefix)), None)
                if sample is not None:
                    with self.subTest(pattern=pattern):
                        self.assertIsNotNone(re.search(pattern, sample))
                        self.assertIsNone(re.search(pattern, sample + "\n"))


if __name__ == "__main__":
    unittest.main()
