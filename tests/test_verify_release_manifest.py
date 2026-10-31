import hashlib
import json
import tempfile

import unittest
from pathlib import Path

from scripts.verify_release_manifest import SCHEMA_PATH, verify_release_manifest


class ReleaseManifestVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.schema = self.root / "schema.json"
        self.schema.write_text(json.dumps({
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["schema_version", "platform", "sbom", "provenance", "artifacts"],
            "properties": {
                "schema_version": {"const": "1.0.0"},
                "platform": {"type": "object", "required": ["architecture"], "properties": {"architecture": {"enum": ["x86_64", "aarch64"]}}},
                "sbom": {"$ref": "#/$defs/evidence"},
                "provenance": {"$ref": "#/$defs/evidence"},
                "artifacts": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/artifact"}},
            },
            "$defs": {
                "evidence": {"type": "object", "required": ["format", "uri", "sha256"], "properties": {"format": {"type": "string"}, "uri": {"type": "string"}, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}},
                "artifact": {"type": "object", "required": ["id", "filename", "architecture", "size_bytes", "sha256", "tests"], "properties": {"id": {"type": "string"}, "filename": {"type": "string"}, "architecture": {"type": "string"}, "size_bytes": {"type": "integer"}, "sha256": {"type": "string"}, "signature": {"$ref": "#/$defs/evidence"}, "tests": {"type": "object"}}},
            },
        }), encoding="utf-8")
        self._write("sbom.spdx.json", b'{"spdxVersion":"SPDX-2.3"}')
        self._write("provenance.json", b'{"_type":"https://in-toto.io/Statement/v1"}')
        self._write("tusker.iso", b"synthetic installer bytes")
        self.manifest = self.root / "release.json"
        self.payload = {
            "schema_version": "1.0.0",
            "platform": {"architecture": "x86_64"},
            "sbom": self._evidence("sbom.spdx.json", "SPDX-2.3"),
            "provenance": self._evidence("provenance.json", "in-toto"),
            "artifacts": [{
                "id": "tusker-x86_64-iso",
                "filename": "tusker.iso",
                "architecture": "x86_64",
                "size_bytes": (self.root / "tusker.iso").stat().st_size,
                "sha256": self._digest("tusker.iso"),
                "tests": {name: {"status": "passed", "report": f"reports/{name}.json"} for name in ("uefi_boot", "secure_boot", "desktop_smoke", "install", "recovery")},
            }],
        }
        self._save()

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, name, content):
        (self.root / name).write_bytes(content)

    def _digest(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def _evidence(self, name, fmt):
        return {"format": fmt, "uri": name, "sha256": self._digest(name)}

    def _save(self):
        self.manifest.write_text(json.dumps(self.payload), encoding="utf-8")

    def _verify(self):
        return verify_release_manifest(self.manifest, self.schema)

    def _real_contract_manifest(self):
        return {
            "schema_version": "1.0.0",
            "release_id": "phoenix-fixture-001",
            "channel": "development",
            "created_at_utc": "2026-10-31T00:00:00Z",
            "source": {"repository": "https://github.com/otta-komban/TuskerOS", "commit": "a" * 40},
            "recipe": {"path": "image/kiwi/config.xml", "commit": "b" * 40},
            "platform": {
                "distribution": "Fedora", "release": "44", "architecture": "x86_64",
                "builder": {"name": "kiwi-ng", "version": "11.1.6"},
                "environment_digest": "sha256:" + "c" * 64,
            },
            "repositories": [{"id": "fedora-44", "url": "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/", "snapshot_id": "fixture-snapshot"}],
            "packages": [{"nevra": "bash-0:5.2.32-1.fc44.x86_64"}],
            "sbom": self._evidence("sbom.spdx.json", "SPDX-2.3"),
            "provenance": self._evidence("provenance.json", "in-toto"),
            "artifacts": [{
                "id": "tusker-x86_64-iso", "filename": "tusker.iso",
                "media_type": "application/x-iso9660-image", "architecture": "x86_64",
                "firmware_targets": ["uefi"],
                "size_bytes": (self.root / "tusker.iso").stat().st_size,
                "sha256": self._digest("tusker.iso"),
                "tests": {name: {"status": "passed", "report": f"reports/{name}.json"} for name in ("uefi_boot", "secure_boot", "desktop_smoke", "install", "recovery")},
            }],
        }

    def test_valid_local_manifest_and_bytes_pass_but_promotion_stays_blocked(self):
        result = self._verify()
        self.assertTrue(result["valid"], result["errors"])
        self.assertFalse(result["promotion_ready"])
        self.assertTrue(any("cryptographic signature verification is NOT performed" in item for item in result["warnings"]))

    @unittest.skipUnless(SCHEMA_PATH.is_file(), "requires repository release-manifest schema")
    def test_complete_manifest_matches_repository_draft_2020_12_schema(self):
        self.payload = self._real_contract_manifest()
        self._save()
        result = verify_release_manifest(self.manifest, SCHEMA_PATH)
        self.assertTrue(result["valid"], result["errors"])
        self.assertFalse(result["promotion_ready"])

    @unittest.skipUnless(SCHEMA_PATH.is_file(), "requires repository release-manifest schema")
    def test_repository_schema_rejects_unknown_top_level_property(self):
        self.payload = self._real_contract_manifest()
        self.payload["unreviewed_extension"] = True
        self._save()
        result = verify_release_manifest(self.manifest, SCHEMA_PATH)
        self.assertFalse(result["valid"])
        self.assertTrue(any("Additional properties are not allowed" in item for item in result["errors"]))

    def test_artifact_digest_mismatch_fails(self):
        self._write("tusker.iso", b"tampered bytes")
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("sha256" in item for item in result["errors"]))

    def test_artifact_size_mismatch_fails(self):
        self.payload["artifacts"][0]["size_bytes"] += 1
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("size_bytes" in item for item in result["errors"]))

    def test_sbom_digest_mismatch_fails(self):
        self.payload["sbom"]["sha256"] = "0" * 64
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("sbom: SHA-256" in item for item in result["errors"]))

    def test_parent_traversal_is_rejected(self):
        self.payload["artifacts"][0]["filename"] = "../tusker.iso"
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("parent traversal" in item for item in result["errors"]))

    def test_remote_evidence_uri_is_rejected_without_network_fetch(self):
        self.payload["provenance"]["uri"] = "https://example.invalid/provenance.json"
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("only local relative paths" in item for item in result["errors"]))

    def test_symlink_escape_is_rejected(self):
        outside = self.root.parent / (self.root.name + "-outside")
        outside.write_bytes(b"outside")
        link = self.root / "escape.bin"
        link.symlink_to(outside)
        self.payload["artifacts"][0]["filename"] = "escape.bin"
        self._save()
        try:
            result = self._verify()
            self.assertFalse(result["valid"])
            self.assertTrue(any("outside the manifest directory" in item for item in result["errors"]))
        finally:
            link.unlink(missing_ok=True)
            outside.unlink(missing_ok=True)


    def test_symlink_to_file_inside_manifest_directory_is_rejected(self):
        target = self.root / "real.iso"
        target.write_bytes(b"synthetic installer bytes")
        link = self.root / "linked.iso"
        link.symlink_to(target)
        self.payload["artifacts"][0]["filename"] = "linked.iso"
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("symlinked" in item for item in result["errors"]))

    def test_symlinked_parent_directory_is_rejected(self):
        target_dir = self.root / "real-dir"
        target_dir.mkdir()
        (target_dir / "installer.iso").write_bytes(b"synthetic installer bytes")
        (self.root / "linked-dir").symlink_to(target_dir, target_is_directory=True)
        self.payload["artifacts"][0]["filename"] = "linked-dir/installer.iso"
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("symlinked" in item for item in result["errors"]))

    def test_non_regular_artifact_is_rejected(self):
        directory = self.root / "artifact-directory"
        directory.mkdir()
        self.payload["artifacts"][0]["filename"] = "artifact-directory"
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("regular file" in item for item in result["errors"]))

    def test_empty_path_component_is_rejected(self):
        self.payload["artifacts"][0]["filename"] = "nested//installer.iso"
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("empty components" in item for item in result["errors"]))

    def test_nested_regular_artifact_is_supported(self):
        nested = self.root / "artifacts"
        nested.mkdir()
        (nested / "tusker.iso").write_bytes(b"synthetic installer bytes")
        self.payload["artifacts"][0]["filename"] = "artifacts/tusker.iso"
        self._save()
        result = self._verify()
        self.assertTrue(result["valid"], result["errors"])
        self.assertFalse(result["promotion_ready"])

    def test_architecture_mismatch_fails(self):
        self.payload["artifacts"][0]["architecture"] = "aarch64"
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("does not match platform architecture" in item for item in result["errors"]))

    def test_duplicate_artifact_id_and_filename_fail(self):
        self.payload["artifacts"].append(dict(self.payload["artifacts"][0]))
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("duplicate artifact id" in item for item in result["errors"]))
        self.assertTrue(any("duplicate artifact filename" in item for item in result["errors"]))

    def test_signature_file_digest_is_checked_but_not_trusted(self):
        self._write("tusker.iso.sig", b"detached signature bytes")
        self.payload["artifacts"][0]["signature"] = self._evidence("tusker.iso.sig", "openpgp-detached")
        self._save()
        result = self._verify()
        self.assertTrue(result["valid"], result["errors"])
        self.assertFalse(result["promotion_ready"])
        self.assertTrue(any(item["id"].endswith("signature_file_bytes") for item in result["checks"]))

    def test_failed_test_gate_is_reported_as_blocked(self):
        self.payload["artifacts"][0]["tests"]["install"] = {"status": "blocked"}
        self._save()
        result = self._verify()
        self.assertTrue(result["valid"], result["errors"])
        self.assertFalse(result["promotion_ready"])
        self.assertTrue(any("tests.install" in item for item in result["warnings"]))

    def test_duplicate_json_keys_are_rejected(self):
        self.manifest.write_text('{"schema_version":"1.0.0","schema_version":"1.0.0"}', encoding="utf-8")
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("duplicate JSON object key" in item for item in result["errors"]))

    def test_schema_rejection_is_reported(self):
        self.payload["schema_version"] = "2.0.0"
        self._save()
        result = self._verify()
        self.assertFalse(result["valid"])
        self.assertTrue(any("schema" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
