"""Validation for provisional Tusker Core JSON Schemas."""
import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
EXAMPLES_DIR = SCHEMA_DIR / "examples"
CONTRACTS = {
    "task": ("task.schema.json", "task.valid.json"),
    "plan": ("plan.schema.json", "plan.valid.json"),
    "task-event": ("task-event.schema.json", "task-event.valid.json"),
    "task-result": ("task-result.schema.json", "task-result.valid.json"),
    "cancellation": ("cancellation.schema.json", "cancellation.valid.json"),
}


def load_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


class ContractSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples = {}
        cls.validators = {}
        for name, (schema_file, example_file) in CONTRACTS.items():
            schema = load_json(SCHEMA_DIR / schema_file)
            Draft202012Validator.check_schema(schema)
            cls.examples[name] = load_json(EXAMPLES_DIR / example_file)
            cls.validators[name] = Draft202012Validator(
                schema, format_checker=FormatChecker()
            )

    def test_representative_examples_validate(self):
        for name, validator in self.validators.items():
            with self.subTest(contract=name):
                errors = list(validator.iter_errors(self.examples[name]))
                self.assertEqual(errors, [], "; ".join(e.message for e in errors))

    def test_unknown_top_level_fields_are_rejected(self):
        for name, validator in self.validators.items():
            with self.subTest(contract=name):
                candidate = copy.deepcopy(self.examples[name])
                candidate["unexpected_untrusted_field"] = True
                self.assertTrue(list(validator.iter_errors(candidate)))

    def test_unknown_schema_versions_are_rejected(self):
        for name, validator in self.validators.items():
            with self.subTest(contract=name):
                candidate = copy.deepcopy(self.examples[name])
                candidate["schema_version"] = "99.0.0"
                self.assertTrue(list(validator.iter_errors(candidate)))

    def test_task_event_requires_origin(self):
        candidate = copy.deepcopy(self.examples["task-event"])
        candidate.pop("origin", None)
        self.assertTrue(list(self.validators["task-event"].iter_errors(candidate)))


    def test_idempotency_key_matches_nexus_length_bounds(self):
        validator = self.validators["plan"]
        for length in (16, 128):
            with self.subTest(valid_length=length):
                candidate = copy.deepcopy(self.examples["plan"])
                candidate["steps"][0]["idempotency_key"] = "k" * length
                self.assertEqual(list(validator.iter_errors(candidate)), [])
        for length in (15, 129):
            with self.subTest(invalid_length=length):
                candidate = copy.deepcopy(self.examples["plan"])
                candidate["steps"][0]["idempotency_key"] = "k" * length
                self.assertTrue(list(validator.iter_errors(candidate)))

    def test_terminal_cancelled_event_is_valid(self):
        candidate = copy.deepcopy(self.examples["task-event"])
        candidate["type"] = "task.cancelled"
        candidate["state"] = "cancelled"
        self.assertEqual(
            list(self.validators["task-event"].iter_errors(candidate)), []
        )


if __name__ == "__main__":
    unittest.main()
