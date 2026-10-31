"""Tests for immutable Fedora repository snapshot capture and verification."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("verify-repository-snapshot.py")
SPEC = importlib.util.spec_from_file_location("atlas_repository_snapshot", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load repository snapshot verifier from {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

REPOMD_URL = "https://mirror.example/fedora/repodata/repomd.xml"
PRIMARY_URL = "https://mirror.example/fedora/repodata/primary.xml.gz"
PRIMARY = b"immutable primary metadata fixture\n"
REPOMD = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<repomd xmlns="http://linux.duke.edu/metadata/repo">'
    b'<revision>20261031</revision>'
    b'<data type="primary">'
    b'<checksum type="sha256">' + hashlib.sha256(PRIMARY).hexdigest().encode() + b'</checksum>'
    b'<location href="repodata/primary.xml.gz"/>'
    b'</data></repomd>'
)


class LockValidationTests(unittest.TestCase):
    def entry(self):
        repomd_digest = hashlib.sha256(REPOMD).hexdigest()
        return {
            "repository_id": "fedora",
            "repomd_url": REPOMD_URL,
            "repomd_sha256": repomd_digest,
            "revision": "20261031",
            "primary_href": "repodata/primary.xml.gz",
            "primary_sha256": hashlib.sha256(PRIMARY).hexdigest(),
            "snapshot_id": f"fedora44/fedora/20261031/{repomd_digest}",
        }

    def payload(self, entries=None):
        return {
            "schema_version": 1,
            "fedora_release": "44",
            "architecture": "x86_64",
            "repositories": [self.entry()] if entries is None else entries,
        }

    def test_valid_empty_lock_is_schema_valid(self):
        self.assertEqual(MODULE.validate_lock(self.payload([])), {})

    def test_empty_lock_is_rejected_for_production_verification(self):
        with self.assertRaisesRegex(RuntimeError, "has no repositories"):
            MODULE.validate_lock(self.payload([]), require_repositories=True)

    def test_wrong_release_or_architecture_is_rejected(self):
        payload = self.payload()
        payload["architecture"] = "aarch64"
        with self.assertRaisesRegex(RuntimeError, "Fedora 44 x86_64"):
            MODULE.validate_lock(payload)

    def test_duplicate_repository_ids_are_rejected(self):
        entry = self.entry()
        with self.assertRaisesRegex(RuntimeError, "duplicate repository"):
            MODULE.validate_lock(self.payload([entry, dict(entry)]))

    def test_invalid_digest_is_rejected(self):
        entry = self.entry()
        entry["repomd_sha256"] = "not-a-digest"
        with self.assertRaisesRegex(RuntimeError, "SHA-256"):
            MODULE.validate_lock(self.payload([entry]))

    def test_snapshot_id_must_bind_revision_and_repomd_digest(self):
        entry = self.entry()
        entry["snapshot_id"] = "fedora44/fedora/latest"
        with self.assertRaisesRegex(RuntimeError, "snapshot_id"):
            MODULE.validate_lock(self.payload([entry]))

    def test_primary_metadata_url_is_resolved_from_repository_root(self):
        self.assertEqual(MODULE.primary_metadata_url(REPOMD_URL, "repodata/primary.xml.gz"), PRIMARY_URL)

    def test_primary_path_traversal_is_rejected(self):
        malicious = REPOMD.replace(b"repodata/primary.xml.gz", b"../outside.xml")
        with self.assertRaisesRegex(RuntimeError, "unsafe primary metadata path"):
            MODULE.parse_repomd(malicious)

    def test_absolute_primary_metadata_url_is_rejected(self):
        malicious = REPOMD.replace(
            b"repodata/primary.xml.gz",
            b"https://attacker.example/primary.xml.gz",
        )
        with self.assertRaisesRegex(RuntimeError, "unsafe primary metadata path"):
            MODULE.parse_repomd(malicious)

    def test_primary_metadata_must_stay_on_repository_origin(self):
        with self.assertRaisesRegex(RuntimeError, "escaped its HTTPS repository origin"):
            MODULE.primary_metadata_url(REPOMD_URL, "//attacker.example/primary.xml.gz")


class CaptureTests(unittest.TestCase):
    def test_capture_pins_both_repomd_and_primary_payload(self):
        with mock.patch.object(MODULE, "fetch_https", side_effect=[REPOMD, PRIMARY]) as fetch:
            entry = MODULE.capture_repository("fedora", REPOMD_URL)
        self.assertEqual(entry["repomd_sha256"], hashlib.sha256(REPOMD).hexdigest())
        self.assertEqual(entry["primary_sha256"], hashlib.sha256(PRIMARY).hexdigest())
        self.assertEqual(entry["revision"], "20261031")
        self.assertTrue(entry["snapshot_id"].startswith("fedora44/fedora/20261031/"))
        self.assertEqual(fetch.call_args_list[1].args[0], PRIMARY_URL)

    def test_capture_rejects_primary_payload_digest_mismatch(self):
        with mock.patch.object(MODULE, "fetch_https", side_effect=[REPOMD, b"tampered"]):
            with self.assertRaisesRegex(RuntimeError, "does not match repomd.xml"):
                MODULE.capture_repository("fedora", REPOMD_URL)

    def test_capture_rejects_invalid_repository_id(self):
        with self.assertRaisesRegex(RuntimeError, "invalid repository ID"):
            MODULE.capture_repository("../fedora", REPOMD_URL)


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.lock_path = Path(self.temporary.name) / "repository-snapshot.lock.json"
        self.entry = {
            "repository_id": "fedora",
            "repomd_url": REPOMD_URL,
            "repomd_sha256": hashlib.sha256(REPOMD).hexdigest(),
            "revision": "20261031",
            "primary_href": "repodata/primary.xml.gz",
            "primary_sha256": hashlib.sha256(PRIMARY).hexdigest(),
            "snapshot_id": f"fedora44/fedora/20261031/{hashlib.sha256(REPOMD).hexdigest()}",
        }
        self.lock_path.write_text(json.dumps({
            "schema_version": 1,
            "fedora_release": "44",
            "architecture": "x86_64",
            "repositories": [self.entry],
        }), encoding="utf-8")

    def test_verify_checks_repomd_and_primary_payload(self):
        with mock.patch.object(MODULE, "fetch_https", side_effect=[REPOMD, PRIMARY]) as fetch:
            indexed = MODULE.verify_lock(self.lock_path)
        self.assertIn("fedora", indexed)
        self.assertEqual(fetch.call_count, 2)

    def test_verify_rejects_changed_repomd_bytes(self):
        with mock.patch.object(MODULE, "fetch_https", return_value=REPOMD + b"changed"):
            with self.assertRaisesRegex(RuntimeError, "repomd.xml SHA-256 changed"):
                MODULE.verify_lock(self.lock_path)

    def test_verify_rejects_changed_primary_payload(self):
        with mock.patch.object(MODULE, "fetch_https", side_effect=[REPOMD, b"changed primary"]):
            with self.assertRaisesRegex(RuntimeError, "primary metadata SHA-256 changed"):
                MODULE.verify_lock(self.lock_path)


class ManifestSnapshotBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.manifest = Path(self.temporary.name) / "manifest.csv"
        self.snapshot_id = f"fedora44/fedora/20261031/{hashlib.sha256(REPOMD).hexdigest()}"
        self.indexed = {"fedora": {"snapshot_id": self.snapshot_id}}

    def write_manifest(self, repository_id="fedora", snapshot_id=None):
        snapshot_id = self.snapshot_id if snapshot_id is None else snapshot_id
        self.manifest.write_text(
            "layer,package,repository_id,repository_snapshot\n"
            f"base,bash,{repository_id},{snapshot_id}\n",
            encoding="utf-8",
        )

    def test_package_row_must_reference_exact_snapshot(self):
        self.write_manifest()
        self.assertEqual(MODULE.verify_manifest_snapshot_pins(self.manifest, self.indexed), 1)

    def test_package_row_cannot_reference_unknown_repository(self):
        self.write_manifest(repository_id="third-party")
        with self.assertRaisesRegex(RuntimeError, "has no verified snapshot"):
            MODULE.verify_manifest_snapshot_pins(self.manifest, self.indexed)

    def test_package_row_cannot_reference_different_snapshot(self):
        self.write_manifest(snapshot_id="fedora44/fedora/latest")
        with self.assertRaisesRegex(RuntimeError, "does not match verified snapshot"):
            MODULE.verify_manifest_snapshot_pins(self.manifest, self.indexed)

    def test_empty_package_manifest_is_rejected_for_build(self):
        self.manifest.write_text("layer,package,repository_id,repository_snapshot\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "has no rows"):
            MODULE.verify_manifest_snapshot_pins(self.manifest, self.indexed)



if __name__ == "__main__":
    unittest.main()
