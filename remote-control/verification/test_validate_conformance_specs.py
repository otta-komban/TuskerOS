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

    def test_preserves_escaped_pipe_inside_cell(self):
        markdown = r"| PAIR-C01 | Condition with \| literal pipe | Reject safely |" + "\n"
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [("PAIR-C01", "Condition with | literal pipe", "Reject safely")],
        )

    def test_even_backslash_run_does_not_escape_delimiter(self):
        markdown = r"| PAIR-C01 | Two slashes \\ before delimiter | Reject |" + "\n"
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [( "PAIR-C01", r"Two slashes \ before delimiter", "Reject")],
        )

    def test_odd_backslash_run_escapes_pipe_and_preserves_pairs(self):
        markdown = r"| PAIR-C01 | Three slashes \\\| then text | Reject |" + "\n"
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [("PAIR-C01", r"Two slashes \\| then text", "Reject")],
        )

    def test_pipe_delimiter_parity_for_one_through_six_backslashes(self):
        for slash_count in range(1, 7):
            with self.subTest(slash_count=slash_count):
                slashes = "\\" * slash_count
                row = "| PAIR-C01 | prefix " + slashes + "| suffix | Reject |"
                if slash_count % 2:
                    expected = [
                        "PAIR-C01",
                        "prefix " + ("\\" * (slash_count - 1)) + "| suffix",
                        "Reject",
                    ]
                else:
                    expected = [
                        "PAIR-C01",
                        "prefix " + slashes,
                        "suffix",
                        "Reject",
                    ]
                self.assertEqual(validator.split_table_cells(row), expected)

    def test_rejects_malformed_case_identifier(self):
        markdown = "| PAIR-C1 | Missing zero padding | Reject |" + "\n"
        with self.assertRaisesRegex(validator.SpecError, "malformed case ID"):
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
