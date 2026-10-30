"""Contract schema checks. Run: python -m unittest discover -s system-integration/tests -v"""
import json
import pathlib
import unittest

from jsonschema import Draft202012Validator, FormatChecker

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "contracts"
EXAMPLES = SCHEMAS / "examples"

class ContractSchemaTests(unittest.TestCase):
    def validate_fixture(self, schema_name, fixture_name):
        schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
        fixture = json.loads((EXAMPLES / fixture_name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(fixture)

    def test_tool_invocation_example(self):
        self.validate_fixture("tool-invocation.schema.json", "tool-invocation.valid.json")

    def test_tool_result_example(self):
        self.validate_fixture("tool-result.schema.json", "tool-result.valid.json")

    def test_event_envelope_example(self):
        self.validate_fixture("event-envelope.schema.json", "event-envelope.valid.json")

    def test_health_status_example(self):
        self.validate_fixture("health-status.schema.json", "health-status.valid.json")

    def test_invocation_rejects_unbounded_deadline(self):
        schema = json.loads((SCHEMAS / "tool-invocation.schema.json").read_text(encoding="utf-8"))
        invalid = {"schema_version":"1.0","request_id":"550e8400-e29b-41d4-a716-446655440000",
                   "caller":{"component":"tusker-core","instance_id":"local-1"},
                   "tool":"system.info","arguments":{},"deadline_ms":999999}
        with self.assertRaises(Exception):
            Draft202012Validator(schema, format_checker=FormatChecker()).validate(invalid)

    def test_result_rejects_unknown_status(self):
        schema = json.loads((SCHEMAS / "tool-result.schema.json").read_text(encoding="utf-8"))
        invalid = {"schema_version":"1.0","request_id":"550e8400-e29b-41d4-a716-446655440000",
                   "operation_id":"op-1","status":"success","result":{},
                   "postcondition":{"state":"verified","details":{}},
                   "side_effects":[],"timing":{"duration_ms":1},"error":None}
        with self.assertRaises(Exception):
            Draft202012Validator(schema, format_checker=FormatChecker()).validate(invalid)

if __name__ == "__main__":
    unittest.main()
