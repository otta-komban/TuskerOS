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

    def test_rejects_case_identifier_from_another_specification(self):
        markdown = "| SESS-C01 | Wrong specification | Reject |" + "\n"
        with self.assertRaisesRegex(validator.SpecError, "belongs to another specification"):
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

    def test_json_success_output_is_machine_readable_and_scoped(self):
        from contextlib import redirect_stdout
        import io
        import json
        from unittest.mock import patch

        output = io.StringIO()
        with patch.object(validator, "validate_repository", return_value=["validated"]):
            with redirect_stdout(output):
                result = validator.main(["--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["runtime_security_tested"])
        self.assertEqual([item["prefix"] for item in payload["specifications"]],
                         ["PAIR", "SESS", "NET"])

    def test_json_failure_output_is_machine_readable_and_scoped(self):
        from contextlib import redirect_stdout
        import io
        import json
        from unittest.mock import patch

        output = io.StringIO()
        with patch.object(validator, "validate_repository",
                          side_effect=validator.SpecError("bad specification")):
            with redirect_stdout(output):
                result = validator.main(["--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(result, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "bad specification")
        self.assertFalse(payload["runtime_security_tested"])

class RepositoryValidationTests(unittest.TestCase):
    def test_validates_all_specs_from_supplied_root(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            for prefix, (relative_path, case_count) in validator.SPECS.items():
                spec_path = root / relative_path
                spec_path.parent.mkdir(parents=True, exist_ok=True)
                spec_path.write_text(
                    "".join(
                        f"| {prefix}-C{number:02d} | Condition {number} | Assertion {number} |\n"
                        for number in range(1, case_count + 1)
                    ),
                    encoding="utf-8",
                )

            results = validator.validate_repository(root)

        self.assertEqual(len(results), 3)
        self.assertIn("PAIR: 22 unique, contiguous cases validated", results[0])
        self.assertIn("SESS: 40 unique, contiguous cases validated", results[1])
        self.assertIn("NET: 42 unique, contiguous cases validated", results[2])

    def test_json_cli_uses_supplied_root_for_success(self):
        from contextlib import redirect_stdout
        import io
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            for prefix, (relative_path, case_count) in validator.SPECS.items():
                spec_path = root / relative_path
                spec_path.parent.mkdir(parents=True, exist_ok=True)
                spec_path.write_text(
                    "".join(
                        f"| {prefix}-C{number:02d} | Condition {number} | Assertion {number} |\n"
                        for number in range(1, case_count + 1)
                    ),
                    encoding="utf-8",
                )
            output = io.StringIO()
            with redirect_stdout(output):
                result = validator.main(["--root", temporary_root, "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual([item["case_count"] for item in payload["specifications"]],
                         [22, 40, 42])
        self.assertFalse(payload["runtime_security_tested"])

    def test_json_cli_reports_missing_spec_from_supplied_root(self):
        from contextlib import redirect_stdout
        import io
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            output = io.StringIO()
            with redirect_stdout(output):
                result = validator.main(["--root", temporary_root, "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 1)
        self.assertFalse(payload["ok"])
        self.assertIn("PAIR: specification not found", payload["error"])
        self.assertFalse(payload["runtime_security_tested"])

    def test_missing_specification_fails_repository_validation(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            with self.assertRaisesRegex(validator.SpecError, "PAIR: specification not found"):
                validator.validate_repository(Path(temporary_root))


if __name__ == "__main__":
    unittest.main()
