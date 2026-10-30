from __future__ import annotations

import json
import unittest
from pathlib import Path

from desktop.config.settings import DEFAULT_SETTINGS


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "config" / "settings.schema.json"


class SettingsSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_is_draft_2020_12_and_rejects_unknown_keys(self) -> None:
        self.assertEqual(
            self.schema["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertFalse(self.schema["additionalProperties"])
        for section in ("panel", "assistant", "accessibility"):
            self.assertFalse(self.schema["properties"][section]["additionalProperties"])

    def test_schema_defaults_match_runtime_defaults(self) -> None:
        self.assertEqual(self.schema["properties"]["schema_version"]["default"], 1)
        for section, values in DEFAULT_SETTINGS.items():
            if section == "schema_version":
                continue
            schema_properties = self.schema["properties"][section]["properties"]
            for key, value in values.items():
                with self.subTest(section=section, key=key):
                    self.assertEqual(schema_properties[key]["default"], value)

    def test_schema_constraints_match_runtime_enums(self) -> None:
        panel = self.schema["properties"]["panel"]["properties"]
        self.assertEqual(panel["edge"]["enum"], ["bottom", "top", "left", "right"])
        self.assertEqual(panel["icon_size"]["enum"], [24, 32, 40, 48, 56, 64, 72, 80, 88, 96])
        self.assertEqual(self.schema["properties"]["schema_version"]["const"], 1)

    def test_schema_covers_every_runtime_setting(self) -> None:
        for section, values in DEFAULT_SETTINGS.items():
            if section == "schema_version":
                self.assertIn(section, self.schema["properties"])
                continue
            declared = self.schema["properties"][section]["properties"]
            self.assertEqual(set(declared), set(values))


if __name__ == "__main__":
    unittest.main()
