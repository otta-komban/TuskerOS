"""Structural safety tests for the TuskerOS theme-pack examples.

These tests use only Python's standard library. Full JSON Schema validation is
intentionally a separate CI dependency and is not claimed by this test module.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "theme-studio/schema/theme-pack.schema.json"
SAMPLES = [
    ROOT / "themes/monochrome/theme.json",
    ROOT / "themes/classic-glass/theme.json",
    ROOT / "themes/smooth-ui/theme.json",
]
TOP_LEVEL = {
    "schema_version", "id", "version", "metadata", "compatibility",
    "tokens", "accessibility", "assets", "surface_overrides", "mixins",
}
EXECUTABLE_KEYS = {
    "script", "scripts", "command", "commands", "exec", "executable",
    "hook", "hooks", "plugin", "plugins", "qml", "javascript",
    "python", "shell", "entrypoint", "post_install", "pre_install",
}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?$")


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).lower()
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


class ThemePackStructuralTests(unittest.TestCase):
    def test_schema_is_valid_json_and_closed_at_root(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0.0")

    def test_all_starter_packs_have_required_structure(self):
        for path in SAMPLES:
            with self.subTest(pack=path.parent.name):
                pack = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(pack["schema_version"], "1.0.0")
                self.assertTrue(ID_RE.fullmatch(pack["id"]))
                self.assertTrue(VERSION_RE.fullmatch(pack["version"]))
                self.assertTrue(set(pack).issubset(TOP_LEVEL))
                for field in ("metadata", "compatibility", "tokens", "accessibility", "assets"):
                    self.assertIn(field, pack)
                self.assertEqual(pack["tokens"]["motion"]["reduced_motion_compatible"], True)
                self.assertEqual(pack["accessibility"]["focus_indicator"], True)
                self.assertEqual(pack["accessibility"]["reduced_motion"], True)

    def test_starter_packs_contain_no_executable_extension_keys(self):
        for path in SAMPLES:
            with self.subTest(pack=path.parent.name):
                pack = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(EXECUTABLE_KEYS.isdisjoint(set(walk_keys(pack))))

    def test_assets_are_empty_until_provenance_is_registered(self):
        for path in SAMPLES:
            with self.subTest(pack=path.parent.name):
                pack = json.loads(path.read_text(encoding="utf-8"))
                # Avoid shipping unreviewed or unlicensed binary assets.
                self.assertEqual(pack["assets"], [])


if __name__ == "__main__":
    unittest.main()
