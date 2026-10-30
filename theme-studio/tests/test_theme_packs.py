"""Theme-pack schema and safety regression tests.

Install the development dependency with: python -m pip install -r requirements-dev.txt
Run from the repository root: python -m unittest discover -s theme-studio/tests -v
"""
import copy
import json
import re
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "theme-studio/schema/theme-pack.schema.json"
SAMPLE_PATHS = [
    ROOT / "themes/monochrome/theme.json",
    ROOT / "themes/classic-glass/theme.json",
    ROOT / "themes/smooth-ui/theme.json",
]
EXECUTABLE_KEYS = {
    "script", "scripts", "command", "commands", "exec", "executable",
    "hook", "hooks", "plugin", "plugins", "qml", "javascript",
    "python", "shell", "entrypoint", "post_install", "pre_install",
}
SHA = "a" * 64


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).lower()
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def valid_asset(asset_id="wallpaper-main", kind="wallpaper", path="assets/wallpaper.webp", media_type="image/webp"):
    return {
        "id": asset_id,
        "kind": kind,
        "path": path,
        "media_type": media_type,
        "sha256": SHA,
        "license": "CC0-1.0",
    }


def asset_roles_match_kinds(pack):
    expected = {
        "desktop_wallpaper": "wallpaper",
        "lock_screen_wallpaper": "wallpaper",
        "icon_set": "icon",
        "font_regular": "font",
        "font_emphasis": "font",
        "notification_sound": "sound",
        "startup_sound": "sound",
    }
    assets = {item["id"]: item["kind"] for item in pack.get("assets", [])}
    for role, asset_id in pack.get("asset_roles", {}).items():
        if asset_id not in assets or assets[asset_id] != expected[role]:
            return False
    return True


class ThemePackSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_json(SCHEMA_PATH)
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())

    def test_schema_itself_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(self.schema)

    def test_all_starter_packs_validate(self):
        for path in SAMPLE_PATHS:
            with self.subTest(pack=path.parent.name):
                pack = load_json(path)
                self.validator.validate(pack)
                self.assertTrue(asset_roles_match_kinds(pack))

    def test_starter_packs_have_no_executable_extension_keys(self):
        for path in SAMPLE_PATHS:
            with self.subTest(pack=path.parent.name):
                self.assertTrue(EXECUTABLE_KEYS.isdisjoint(set(walk_keys(load_json(path)))))

    def test_unknown_manifest_field_is_rejected(self):
        pack = copy.deepcopy(load_json(SAMPLE_PATHS[0]))
        pack["post_install"] = "echo unsafe"
        self.assertFalse(self.validator.is_valid(pack))

    def test_svg_active_content_format_is_rejected(self):
        pack = copy.deepcopy(load_json(SAMPLE_PATHS[0]))
        pack["assets"] = [valid_asset(media_type="image/svg+xml", path="assets/active.svg")]
        self.assertFalse(self.validator.is_valid(pack))

    def test_path_traversal_is_rejected(self):
        for unsafe_path in ("../outside.webp", "assets/../../outside.webp", "/etc/passwd", r"assets\\evil.webp", "assets//double.webp"):
            with self.subTest(path=unsafe_path):
                pack = copy.deepcopy(load_json(SAMPLE_PATHS[0]))
                pack["assets"] = [valid_asset(path=unsafe_path)]
                self.assertFalse(self.validator.is_valid(pack))

    def test_unknown_surface_override_is_rejected(self):
        pack = copy.deepcopy(load_json(SAMPLE_PATHS[0]))
        pack["surface_overrides"] = {"arbitrary.plugin.surface": {"opacity": 0.8}}
        self.assertFalse(self.validator.is_valid(pack))

    def test_asset_role_must_resolve_to_declared_asset_of_expected_kind(self):
        pack = copy.deepcopy(load_json(SAMPLE_PATHS[0]))
        pack["assets"] = [valid_asset()]
        pack["asset_roles"] = {"desktop_wallpaper": "wallpaper-main"}
        self.validator.validate(pack)
        self.assertTrue(asset_roles_match_kinds(pack))
        pack["asset_roles"]["font_regular"] = "wallpaper-main"
        self.assertFalse(asset_roles_match_kinds(pack))

    def test_duplicate_asset_ids_are_rejected_by_semantic_validator(self):
        pack = copy.deepcopy(load_json(SAMPLE_PATHS[0]))
        pack["assets"] = [valid_asset(), valid_asset(path="assets/other.webp")]
        ids = [asset["id"] for asset in pack["assets"]]
        self.assertNotEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
