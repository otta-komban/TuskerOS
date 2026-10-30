"""Runtime asset-inspection security tests."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from asset_inspector import AssetInspectionError, inspect_asset, inspect_pack_assets

PNG = b"\x89PNG\r\n\x1a\n" + b"test-payload"

class AssetInspectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "assets").mkdir()
        (self.root / "assets" / "wallpaper.png").write_bytes(PNG)
        self.asset = {
            "id": "wallpaper-main", "kind": "wallpaper",
            "path": "assets/wallpaper.png", "media_type": "image/png",
            "sha256": hashlib.sha256(PNG).hexdigest(),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_asset_is_inspected_and_hashed(self):
        result = inspect_asset(self.root, self.asset)
        self.assertEqual(result["size_bytes"], len(PNG))
        self.assertEqual(result["sha256"], self.asset["sha256"])

    def test_traversal_and_absolute_paths_are_rejected(self):
        for path in ("../outside.png", "assets/../../outside.png", "/etc/passwd",
                     "assets//wallpaper.png", r"assets\\wallpaper.png"):
            with self.subTest(path=path):
                bad = {**self.asset, "path": path}
                with self.assertRaises(AssetInspectionError):
                    inspect_asset(self.root, bad)

    def test_symlink_is_rejected(self):
        outside = self.root.parent / (self.root.name + "-outside.png")
        outside.write_bytes(PNG)
        try:
            (self.root / "assets" / "linked.png").symlink_to(outside)
            bad = {**self.asset, "path": "assets/linked.png"}
            with self.assertRaises(AssetInspectionError):
                inspect_asset(self.root, bad)
        finally:
            outside.unlink(missing_ok=True)

    def test_content_type_mismatch_is_rejected(self):
        bad = {**self.asset, "media_type": "image/jpeg"}
        with self.assertRaises(AssetInspectionError):
            inspect_asset(self.root, bad)

    def test_digest_mismatch_is_rejected(self):
        bad = {**self.asset, "sha256": "0" * 64}
        with self.assertRaises(AssetInspectionError):
            inspect_asset(self.root, bad)

    def test_per_file_limit_is_enforced(self):
        with self.assertRaises(AssetInspectionError):
            inspect_pack_assets(self.root, [self.asset], max_pack_bytes=4)

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(AssetInspectionError):
            inspect_pack_assets(self.root, [self.asset, self.asset])

if __name__ == "__main__":
    unittest.main()
