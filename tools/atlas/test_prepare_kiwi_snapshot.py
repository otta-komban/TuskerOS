"""Tests for preparing a local-only KIWI overlay from pinned Fedora descriptions."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

MODULE_PATH = Path(__file__).with_name("prepare-kiwi-snapshot.py")
SPEC = importlib.util.spec_from_file_location("atlas_kiwi_snapshot", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load KIWI snapshot preparation helper")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PrepareKiwiSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.description = self.root / "kiwi"
        self.repositories = self.description / "repositories"
        self.repositories.mkdir(parents=True)
        self.snapshot = self.root / "snapshot"
        self.lock = self.root / "lock.json"
        self.signing_key = self.root / "fedora-signing-key"
        self.signing_key.write_text("test key fixture", encoding="utf-8")
        self.signing_key_uri = self.signing_key.as_uri()
        (self.description / "Fedora.kiwi").write_text(
            '<image><include from="this://./repositories/core.xml"/></image>', encoding="utf-8"
        )
        core_xml = (
            '<image>'
            '<repository type="rpm-md" alias="fedora"><source path="https://mirror.invalid/fedora" sourcetype="metalink">'
            f'<signing key="{self.signing_key_uri}"/>'
            '</source></repository>'
            '<repository type="rpm-md" alias="updates"><source path="https://mirror.invalid/updates" sourcetype="metalink">'
            f'<signing key="{self.signing_key_uri}"/>'
            '</source></repository>'
            '</image>'
        )
        (self.repositories / "core-nonrawhide.xml").write_text(core_xml, encoding="utf-8")
        (self.repositories / "core.xml").symlink_to("core-nonrawhide.xml")
        for repository_id in ("fedora", "updates"):
            (self.snapshot / repository_id / "repodata").mkdir(parents=True)
            (self.snapshot / repository_id / "repodata" / "repomd.xml").write_text("<repomd/>", encoding="utf-8")
        self.lock.write_text(json.dumps({
            "schema_version": 1,
            "fedora_release": "44",
            "architecture": "x86_64",
            "repositories": [{"repository_id": "fedora"}, {"repository_id": "updates"}],
        }), encoding="utf-8")

    def test_overlay_rewrites_every_source_to_local_file_uri_and_enforces_signatures(self):
        result = MODULE.prepare_overlay(self.description, self.snapshot, self.lock)
        self.assertEqual(set(result), {"fedora", "updates"})
        root = ET.parse(self.repositories / "core-nonrawhide.xml").getroot()
        for repository in root.findall("repository"):
            source = repository.find("source")
            self.assertTrue(source.attrib["path"].startswith("file://"))
            self.assertNotIn("sourcetype", source.attrib)
            self.assertTrue(source.find("signing").attrib["key"].startswith("file://"))
            self.assertEqual(repository.attrib["repository_gpgcheck"], "true")
            self.assertEqual(repository.attrib["package_gpgcheck"], "true")

    def test_lock_ids_must_match_upstream_repository_aliases(self):
        payload = json.loads(self.lock.read_text(encoding="utf-8"))
        payload["repositories"] = [{"repository_id": "fedora"}]
        self.lock.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "do not exactly match"):
            MODULE.prepare_overlay(self.description, self.snapshot, self.lock)

    def test_missing_local_repository_is_rejected(self):
        (self.snapshot / "updates" / "repodata" / "repomd.xml").unlink()
        with self.assertRaisesRegex(RuntimeError, "lacks repodata/repomd.xml"):
            MODULE.prepare_overlay(self.description, self.snapshot, self.lock)

    def test_missing_fedora_signing_key_reference_is_rejected(self):
        path = self.repositories / "core-nonrawhide.xml"
        path.write_text(path.read_text(encoding="utf-8").replace(
            f'<signing key="{self.signing_key_uri}"/>', ""
        ), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "signing-key reference is missing"):
            MODULE.prepare_overlay(self.description, self.snapshot, self.lock)

    def test_uninstalled_fedora_signing_key_is_rejected(self):
        path = self.repositories / "core-nonrawhide.xml"
        path.write_text(path.read_text(encoding="utf-8").replace(
            self.signing_key_uri, (self.root / "missing-key").as_uri()
        ), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "signing key is not installed"):
            MODULE.prepare_overlay(self.description, self.snapshot, self.lock)

    def test_non_fedora_lock_target_is_rejected(self):
        payload = json.loads(self.lock.read_text(encoding="utf-8"))
        payload["architecture"] = "aarch64"
        self.lock.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Fedora 44 x86_64"):
            MODULE.prepare_overlay(self.description, self.snapshot, self.lock)


if __name__ == "__main__":
    unittest.main()
