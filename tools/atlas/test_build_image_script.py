"""Regression checks for the Fedora KIWI wrapper's output contract.

These are static source-contract checks; they do not execute KIWI or build an image.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (ROOT / "tools" / "atlas" / "build-image.sh").read_text(encoding="utf-8")


class KiwiBundleContractTests(unittest.TestCase):
    def test_both_profiles_request_result_bundle_export(self):
        self.assertIn('--image-type=iso --image-profile="$ISO_PROFILE" --image-release=0', SCRIPT)
        self.assertIn('--image-type=oem --image-profile="$DISK_PROFILE" --image-release=0', SCRIPT)

    def test_intermediate_build_trees_are_excluded_from_artifact_hashes(self):
        self.assertIn('rm -rf -- "$destination/iso-build" "$destination/disk-build"', SCRIPT)
        self.assertIn('find iso disk -type f -print0 | sort -z', SCRIPT)
        self.assertNotIn('find . -type f ! -name SHA256SUMS', SCRIPT)

    def test_required_artifact_types_are_checked(self):
        self.assertIn("-name '*.iso'", SCRIPT)
        self.assertIn("-name '*.qcow2'", SCRIPT)
        self.assertIn("did not export a live ISO bundle", SCRIPT)
        self.assertIn("did not export a QCOW2 disk bundle", SCRIPT)

    def test_repeat_build_compares_normalized_bundle_checksums(self):
        self.assertIn('diff -u "$RUN_DIR/first/SHA256SUMS" "$RUN_DIR/repeat/SHA256SUMS"', SCRIPT)

    def test_image_build_requires_immutable_repository_metadata_and_package_pins(self):
        self.assertIn('SNAPSHOT_LOCK="${ROOT}/os/repository-snapshot.lock.json"', SCRIPT)
        self.assertIn('"$SNAPSHOT_VERIFIER" --lock "$SNAPSHOT_LOCK" --manifest "$MANIFEST"', SCRIPT)
        self.assertIn('"repository_snapshot_preflight_verified": True', SCRIPT)
        self.assertIn('"repository_snapshot_consumed_by_dnf5": True', SCRIPT)
        self.assertIn('"repository_snapshot_consumed_by_kiwi": True', SCRIPT)
        self.assertIn('--setopt="$repo_id.gpgcheck=1" reposync', SCRIPT)
        self.assertIn('git -C "$UPSTREAM_DIR" archive --format=tar "$UPSTREAM_COMMIT" | tar -xf - -C "$KIWI_BUILD_DIR"', SCRIPT)
        self.assertIn('"$KIWI_OVERLAY_PREPARER" --description-root "$KIWI_BUILD_DIR" --snapshot-root "$SNAPSHOT_ROOT"', SCRIPT)
        self.assertIn('cd "$KIWI_BUILD_DIR"', SCRIPT)
        self.assertIn('--download-metadata --destdir="$SNAPSHOT_ROOT" --arch=x86_64 --arch=noarch --gpgcheck', SCRIPT)
        self.assertIn('--snapshot-root "$SNAPSHOT_ROOT"', SCRIPT)

    def test_metadata_does_not_overclaim_reproducibility(self):
        self.assertIn('"repeat_build_checksum_comparison": "passed" if repro == "1" else "not_run"', SCRIPT)
        self.assertIn('"reproducible_build_claim": False', SCRIPT)
        self.assertIn('"repository_metadata_signature_verified": False', SCRIPT)
        self.assertIn("Fedora 44 fedora/updates endpoints do not publish repomd.xml.asc at the inspected official URLs", SCRIPT)
        self.assertIn("DNF5 and KIWI enforce RPM package signatures using the Fedora 44 primary key", SCRIPT)
        self.assertIn("RPM payload SHA-256 is checked against the package manifest", SCRIPT)
        self.assertIn("Fedora dist-git source repository URLs are syntax-checked but not independently fetched or verified", SCRIPT)


if __name__ == "__main__":
    unittest.main()
