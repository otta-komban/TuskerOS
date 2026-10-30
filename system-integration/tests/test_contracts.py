"""Contract schema checks. Run: python -m unittest discover -s system-integration/tests -v"""
import copy
import json
import pathlib
import unittest

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "contracts"
EXAMPLES = SCHEMAS / "examples"


class ContractSchemaTests(unittest.TestCase):
    def validate_fixture(self, schema_name, fixture_name):
        schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
        fixture = json.loads((EXAMPLES / fixture_name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(fixture)

    def validate_descriptor_semantics(self, descriptor):
        bounds = descriptor["timeout_ms"]
        if not bounds["minimum"] <= bounds["default"] <= bounds["maximum"]:
            raise ValueError("timeout bounds must satisfy minimum <= default <= maximum")
        idem = descriptor["idempotency"]
        if not idem["supported"] and idem["scope"] != "none":
            raise ValueError("unsupported idempotency must use scope=none")
        if idem["supported"] and idem["scope"] == "none":
            raise ValueError("supported idempotency must declare a non-none scope")

    def test_tool_descriptor_example(self):
        self.validate_fixture("tool-descriptor.schema.json", "tool-descriptor.valid.json")
        descriptor = json.loads((EXAMPLES / "tool-descriptor.valid.json").read_text(encoding="utf-8"))
        self.validate_descriptor_semantics(descriptor)

    def test_tool_descriptor_rejects_inverted_timeout_bounds(self):
        descriptor = json.loads((EXAMPLES / "tool-descriptor.valid.json").read_text(encoding="utf-8"))
        descriptor["timeout_ms"] = {"default": 5000, "minimum": 10000, "maximum": 20000}
        with self.assertRaises(ValueError):
            self.validate_descriptor_semantics(descriptor)

    def test_tool_descriptor_rejects_inconsistent_idempotency(self):
        descriptor = json.loads((EXAMPLES / "tool-descriptor.valid.json").read_text(encoding="utf-8"))
        descriptor["idempotency"] = {"supported": False, "scope": "request"}
        with self.assertRaises(ValueError):
            self.validate_descriptor_semantics(descriptor)

    def test_tool_descriptor_rejects_unknown_idempotency_scope(self):
        schema = json.loads((SCHEMAS / "tool-descriptor.schema.json").read_text(encoding="utf-8"))
        invalid = json.loads((EXAMPLES / "tool-descriptor.valid.json").read_text(encoding="utf-8"))
        invalid["idempotency"]["scope"] = "per_user"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema, format_checker=FormatChecker()).validate(invalid)

    def test_tool_invocation_example(self):
        self.validate_fixture("tool-invocation.schema.json", "tool-invocation.valid.json")

    def test_tool_result_example(self):
        self.validate_fixture("tool-result.schema.json", "tool-result.valid.json")

    def test_tool_result_preserves_all_json_value_types(self):
        schema = json.loads((SCHEMAS / "tool-result.schema.json").read_text(encoding="utf-8"))
        fixture = json.loads((EXAMPLES / "tool-result.valid.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for value in ({"key": "value"}, [1, "two"], "text", 42, 3.5, True, None):
            with self.subTest(result_type=type(value).__name__):
                candidate = copy.deepcopy(fixture)
                candidate["result"] = value
                validator.validate(candidate)

    def test_event_envelope_example(self):
        self.validate_fixture("event-envelope.schema.json", "event-envelope.valid.json")

    def test_health_status_example(self):
        self.validate_fixture("health-status.schema.json", "health-status.valid.json")

    def test_invocation_rejects_unbounded_deadline(self):
        schema = json.loads((SCHEMAS / "tool-invocation.schema.json").read_text(encoding="utf-8"))
        invalid = {"schema_version": "1.0", "request_id": "550e8400-e29b-41d4-a716-446655440000",
                   "caller": {"component": "tusker-core", "instance_id": "local-1"},
                   "tool": "system.info", "arguments": {}, "deadline_ms": 999999,
                   "task_id": "550e8400-e29b-41d4-a716-446655440001",
                   "step_id": "550e8400-e29b-41d4-a716-446655440002", "correlation_id": "corr-1"}
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema, format_checker=FormatChecker()).validate(invalid)

    def test_result_rejects_unknown_status(self):
        schema = json.loads((SCHEMAS / "tool-result.schema.json").read_text(encoding="utf-8"))
        invalid = {"schema_version": "1.0", "request_id": "550e8400-e29b-41d4-a716-446655440000",
                   "operation_id": "op-1", "task_id": "task-1", "step_id": "step-1",
                   "correlation_id": "corr-1", "status": "success", "result": {},
                   "postcondition": {"state": "verified", "details": {}},
                   "side_effects": [], "timing": {"duration_ms": 1},
                   "cancellation": {"request_state": "not_requested", "operation_state": "completed"},
                   "evidence_refs": [], "error": None}
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema, format_checker=FormatChecker()).validate(invalid)


if __name__ == "__main__":
    unittest.main()
