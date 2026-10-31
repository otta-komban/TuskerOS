"""Structural checks for the immutable Fedora KIWI source lock."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads((ROOT / "os" / "image-source.lock.json").read_text(encoding="utf-8"))


class ImageSourceLockTests(unittest.TestCase):
    def test_upstream_source_is_immutable_and_fedora_hosted(self):
        source = LOCK["source"]
        self.assertEqual(source["repository"], "https://forge.fedoraproject.org/releng/kiwi-descriptions.git")
        self.assertEqual(source["ref"], "f44")
        self.assertRegex(source["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(source["license"], "GPL-3.0-or-later")
        self.assertFalse(source["commit_signature_verified"])

    def test_upstream_files_have_git_blob_identities(self):
        source = LOCK["source"]
        for key in ("description_blob", "wrapper_blob", "kde_profile_blob"):
            self.assertRegex(source[key], r"^[0-9a-f]{40}$")

    def test_iso_and_disk_profiles_are_paired(self):
        self.assertEqual(
            [(item["image_type"], item["image_profile"]) for item in LOCK["artifacts"]],
            [("iso", "KDE-Desktop-Live"), ("oem", "KDE-Desktop-Disk")],
        )

    def test_platform_is_the_reviewed_poc_target(self):
        self.assertEqual(
            LOCK["platform"],
            {"fedora_release": "44", "architecture": "x86_64", "firmware": "uefi"},
        )


if __name__ == "__main__":
    unittest.main()
