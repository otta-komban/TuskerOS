"""Unit tests for the PILOT-08 conformance-specification validator."""
import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("validate_conformance_specs.py")
MODULE_SPEC = importlib.util.spec_from_file_location("pilot08_spec_validator", MODULE_PATH)
validator = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = validator
MODULE_SPEC.loader.exec_module(validator)


class ParseCaseRowsTests(unittest.TestCase):
    def test_parses_case_row_and_ignores_header(self):
        markdown = (
            "| Test ID | Condition | Required result |\n"
            "| --- | --- | --- |\n"
            "| PAIR-C01 | Replayed challenge | Reject without enrollment |\n"
        )
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [("PAIR-C01", "Replayed challenge", "Reject without enrollment")],
        )

    def test_rejects_empty_assertion(self):
        markdown = "| PAIR-C01 | Replayed challenge | |\n"
        with self.assertRaises(validator.SpecError):
            validator.parse_case_rows(markdown, "PAIR")

    def test_rejects_wrong_column_count(self):
        markdown = "| PAIR-C01 | Replayed challenge | Reject | Extra |\n"
        with self.assertRaises(validator.SpecError):
            validator.parse_case_rows(markdown, "PAIR")


class ValidateSpecTests(unittest.TestCase):
    def test_accepts_contiguous_case_ids(self):
        markdown = "".join(
            f"| PAIR-C{number:02d} | Condition {number} | Reject or safely handle |\n"
            for number in range(1, 3)
        )
        self.assertEqual(
            validator.validate_spec(markdown, "PAIR", 2),
            ["PAIR-C01", "PAIR-C02"],
        )

    def test_rejects_missing_case_id(self):
        markdown = "| PAIR-C01 | Condition | Assertion |\n"
        with self.assertRaisesRegex(validator.SpecError, "missing PAIR-C02"):
            validator.validate_spec(markdown, "PAIR", 2)

    def test_rejects_duplicate_case_id(self):
        markdown = (
            "| PAIR-C01 | First condition | First assertion |\n"
            "| PAIR-C01 | Second condition | Second assertion |\n"
        )
        with self.assertRaisesRegex(validator.SpecError, "duplicate case IDs"):
            validator.validate_spec(markdown, "PAIR", 1)


if __name__ == "__main__":
    unittest.main()
