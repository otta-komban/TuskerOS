import json
import sys
import unittest
from pathlib import Path

try:
    import jsonschema
except ImportError:  # CI installs theme-studio/requirements-dev.txt
    jsonschema = None


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"


@unittest.skipIf(jsonschema is None, "jsonschema dependency is required")
class PreviewContractSchemaTests(unittest.TestCase):
    def load_schema(self, name):
        return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))

    def test_valid_preview_request_is_declarative_and_preview_only(self):
        schema = self.load_schema("preview-render-request.schema.json")
        payload = {
            "protocol_version": "1.0",
            "request_id": "request_0123456789abcdef",
            "session_id": "session_0123456789abcdef",
            "revision": 7,
            "preview_only": True,
            "expires_in_ms": 120000,
            "surfaces": ["desktop", "panel"],
            "snapshot": {
                "schema_version": "1.0",
                "theme_id": "classic-glass",
                "theme_version": "1.0.0",
                "tokens": {
                    "color": {"background": "#101010", "foreground": "#fefefe"},
                    "motion": {"enabled": False}
                },
                "assets": [{"asset_id": "wallpaper-main", "kind": "wallpaper"}],
                "accessibility": {
                    "focus_indicator": True,
                    "reduced_motion": True,
                    "minimum_text_scale": 1.0,
                    "high_contrast": False
                }
            }
        }
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(payload, schema)

    def test_apply_fields_and_unknown_fields_are_rejected(self):
        schema = self.load_schema("preview-render-request.schema.json")
        payload = {
            "protocol_version": "1.0",
            "request_id": "request_0123456789abcdef",
            "session_id": "session_0123456789abcdef",
            "revision": 1,
            "preview_only": True,
            "expires_in_ms": 1000,
            "surfaces": ["desktop"],
            "snapshot": {
                "schema_version": "1.0",
                "theme_id": "classic-glass",
                "theme_version": "1.0.0",
                "tokens": {"color": {"background": "#000000"}},
                "assets": [],
                "accessibility": {"focus_indicator": True, "reduced_motion": False, "minimum_text_scale": 1.0}
            },
            "apply": True
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(payload, schema)

    def test_preview_only_must_be_true_and_ttl_is_bounded(self):
        schema = self.load_schema("preview-render-request.schema.json")
        for field, value in (("preview_only", False), ("expires_in_ms", 300001), ("expires_in_ms", 0)):
            payload = {
                "protocol_version": "1.0", "request_id": "request_0123456789abcdef",
                "session_id": "session_0123456789abcdef", "revision": 0,
                "preview_only": True, "expires_in_ms": 1000, "surfaces": ["desktop"],
                "snapshot": {"schema_version": "1.0", "theme_id": "classic-glass", "theme_version": "1.0.0",
                             "tokens": {"color": {"background": "#000000"}}, "assets": [],
                             "accessibility": {"focus_indicator": True, "reduced_motion": False, "minimum_text_scale": 1.0}}
            }
            payload[field] = value
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(payload, schema)

    def test_unknown_surfaces_and_token_namespaces_are_rejected(self):
        request_schema = self.load_schema("preview-render-request.schema.json")
        payload = {
            "protocol_version": "1.0", "request_id": "request_0123456789abcdef",
            "session_id": "session_0123456789abcdef", "revision": 0, "preview_only": True,
            "expires_in_ms": 1000, "surfaces": ["arbitrary_shell"],
            "snapshot": {"schema_version": "1.0", "theme_id": "classic-glass", "theme_version": "1.0.0",
                         "tokens": {"color": {"background": "#000000"}}, "assets": [],
                         "accessibility": {"focus_indicator": True, "reduced_motion": False, "minimum_text_scale": 1.0}}
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(payload, request_schema)
        payload["surfaces"] = ["desktop"]
        payload["snapshot"]["tokens"] = {"execute": {"command": "sh"}}
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(payload, request_schema)

    def test_adapter_capabilities_are_allowlisted(self):
        schema = self.load_schema("preview-adapter-capabilities.schema.json")
        payload = {
            "adapter_id": "plasma-preview",
            "protocol_versions": ["1.0"],
            "surfaces": ["desktop", "panel"],
            "token_namespaces": ["color", "typography", "motion"],
            "capabilities": {"blur": True, "transparency": True, "animation": False,
                             "dynamic_wallpaper": False, "lock_screen_theming": False}
        }
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(payload, schema)
        payload["capabilities"]["arbitrary_code"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(payload, schema)

    def test_rendered_response_requires_at_least_one_surface(self):
        schema = self.load_schema("preview-render-response.schema.json")
        payload = {"protocol_version": "1.0", "request_id": "request_0123456789abcdef",
                   "session_id": "session_0123456789abcdef", "revision": 2,
                   "status": "rendered", "rendered_surfaces": ["desktop"]}
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(payload, schema)
        payload["rendered_surfaces"] = []
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(payload, schema)

    def test_partial_response_requires_rendered_and_omitted_surfaces(self):
        schema = self.load_schema("preview-render-response.schema.json")
        payload = {"protocol_version": "1.0", "request_id": "request_0123456789abcdef",
                   "session_id": "session_0123456789abcdef", "revision": 2,
                   "status": "partial", "rendered_surfaces": ["desktop"],
                   "omitted_surfaces": [{"surface": "panel", "reason": "unsupported_effect"}]}
        jsonschema.validate(payload, schema)
        payload["omitted_surfaces"] = []
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(payload, schema)

    def test_rejected_response_requires_stable_failure_code(self):
        schema = self.load_schema("preview-render-response.schema.json")
        payload = {"protocol_version": "1.0", "request_id": "request_0123456789abcdef",
                   "session_id": "session_0123456789abcdef", "revision": 2,
                   "status": "rejected", "failure_code": "expired_session"}
        jsonschema.validate(payload, schema)
        payload["failure_code"] = "arbitrary_error"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(payload, schema)

    def test_response_rejects_unknown_fields_and_apply_claims(self):
        schema = self.load_schema("preview-render-response.schema.json")
        payload = {"protocol_version": "1.0", "request_id": "request_0123456789abcdef",
                   "session_id": "session_0123456789abcdef", "revision": 2,
                   "status": "rejected", "failure_code": "adapter_unavailable", "apply": True}
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(payload, schema)


if __name__ == "__main__":
    unittest.main()
