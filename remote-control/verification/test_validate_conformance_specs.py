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

    def test_preserves_escaped_pipe_at_end_of_row_without_closing_delimiter(self):
        markdown = "| PAIR-C01 | Condition | Reject with literal pipe " + "\\" + "|"
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [("PAIR-C01", "Condition", "Reject with literal pipe |")],
        )

    def test_strips_unescaped_optional_trailing_delimiter_after_backslashes(self):
        slashes = "\\" * 4
        markdown = "| PAIR-C01 | Condition | Reject with literal backslash " + slashes + "|"
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [("PAIR-C01", "Condition", "Reject with literal backslash " + slashes)],
        )

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
            [( "PAIR-C01", r"Two slashes \\ before delimiter", "Reject")],
        )

    def test_odd_backslash_run_escapes_pipe_and_preserves_pairs(self):
        markdown = r"| PAIR-C01 | Three slashes \\\| then text | Reject |" + "\n"
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [("PAIR-C01", r"Three slashes \\| then text", "Reject")],
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

    def test_rejects_non_ascii_digits_in_case_identifier(self):
        markdown = "| PAIR-C٠١ | Non-ASCII digits | Reject |" + "\n"
        with self.assertRaisesRegex(validator.SpecError, "malformed case ID"):
            validator.parse_case_rows(markdown, "PAIR")

    def test_rejects_case_identifier_from_another_specification(self):
        markdown = "| SESS-C01 | Wrong specification | Reject |" + "\n"
        with self.assertRaisesRegex(validator.SpecError, "belongs to another specification"):
            validator.parse_case_rows(markdown, "PAIR")


    def test_ignores_fenced_and_indented_code_example_rows(self):
        markdown = (
            "| PAIR-C01 | Actual specification case | Reject safely |\n"
            "```markdown\n"
            "| PAIR-C01 | Fenced example duplicate | Ignored |\n"
            "```\n"
            "~~~text\n"
            "| PAIR-C01 | Tilde-fenced example duplicate | Ignored |\n"
            "~~~\n"
            "    | PAIR-C01 | Indented example duplicate | Ignored |\n"
            "\t| PAIR-C01 | Tab-indented example duplicate | Ignored |\n"
        )
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [("PAIR-C01", "Actual specification case", "Reject safely")],
        )
        self.assertEqual(
            validator.validate_spec(markdown, "PAIR", 1),
            ["PAIR-C01"],
        )


    def test_fence_closing_length_and_unclosed_fence(self):
        markdown = (
            "| PAIR-C01 | Outside first | Reject |\\n"
            "````markdown\\n"
            "| PAIR-C01 | Inside long fence | Ignored |\\n"
            "```\\n"
            "| PAIR-C01 | Still inside after short fence | Ignored |\\n"
            "````\\n"
            "| PAIR-C01 | Outside after matching close | Reject |\\n"
            "~~~text\\n"
            "| PAIR-C01 | Inside tilde fence | Ignored |\\n"
            "~~~~\\n"
            "| PAIR-C01 | Outside after longer tilde close | Reject |\\n"
            "```python\\n"
            "| PAIR-C01 | Inside unclosed fence | Ignored |\\n"
        )
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [
                ("PAIR-C01", "Outside first", "Reject"),
                ("PAIR-C01", "Outside after matching close", "Reject"),
                ("PAIR-C01", "Outside after longer tilde close", "Reject"),
            ],
        )


    def test_fences_allow_three_space_indent_and_trailing_close_whitespace(self):
        markdown = (
            "| PAIR-C01 | Before fence | Reject |\\n"
            "   ```markdown   \\n"
            "| PAIR-C01 | Fenced example | Ignored |\\n"
            "   ```   \\n"
            "| PAIR-C01 | After fence | Reject |\\n"
            "    ```markdown\\n"
            "| PAIR-C01 | Indented code, not a fence | Ignored |\\n"
        )
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [
                ("PAIR-C01", "Before fence", "Reject"),
                ("PAIR-C01", "After fence", "Reject"),
            ],
        )


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

    def test_duplicate_case_diagnostic_includes_all_source_lines(self):
        markdown = (
            "| PAIR-C01 | First condition | First assertion |\n"
            "| PAIR-C01 | Second condition | Second assertion |\n"
        )
        with self.assertRaisesRegex(
            validator.SpecError, r"PAIR-C01 \(lines 1, 2\)"
        ):
            validator.validate_spec(markdown, "PAIR", 1)

    def test_multiple_duplicate_ids_report_all_lines_in_stable_id_order(self):
        markdown = (
            "| PAIR-C02 | First C02 condition | First C02 assertion |\n"
            "| PAIR-C01 | First C01 condition | First C01 assertion |\n"
            "| PAIR-C02 | Second C02 condition | Second C02 assertion |\n"
            "| PAIR-C01 | Second C01 condition | Second C01 assertion |\n"
        )
        with self.assertRaises(validator.SpecError) as caught:
            validator.validate_spec(markdown, "PAIR", 2)

        self.assertIn(
            "PAIR-C01 (lines 2, 4), PAIR-C02 (lines 1, 3)",
            str(caught.exception),
        )

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

    def test_json_cli_reports_invalid_utf8_without_traceback(self):
        from contextlib import redirect_stdout
        import io
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            relative_path, _ = validator.SPECS["PAIR"]
            spec_path = root / relative_path
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_bytes(b"\xff\xfe")
            output = io.StringIO()
            with redirect_stdout(output):
                result = validator.main(["--root", temporary_root, "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 1)
        self.assertFalse(payload["ok"])
        self.assertIn("utf-8", payload["error"].lower())
        self.assertFalse(payload["runtime_security_tested"])

    def test_text_cli_reports_invalid_utf8_without_traceback(self):
        from contextlib import redirect_stderr, redirect_stdout
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            relative_path, _ = validator.SPECS["PAIR"]
            spec_path = root / relative_path
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_bytes(b"\xff\xfe")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = validator.main(["--root", temporary_root])

        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("FAIL repository validation failed", stderr.getvalue())
        self.assertIn("PAIR:", stderr.getvalue())
        self.assertIn("utf-8", stderr.getvalue().lower())
        self.assertNotIn("Traceback", stderr.getvalue())

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

    def test_repository_validation_reports_all_specification_failures(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            for relative_path, _ in validator.SPECS.values():
                spec_path = root / relative_path
                spec_path.parent.mkdir(parents=True, exist_ok=True)
                spec_path.write_text("", encoding="utf-8")

            with self.assertRaises(validator.SpecError) as raised:
                validator.validate_repository(root)

        message = str(raised.exception)
        for prefix in ("PAIR", "SESS", "NET"):
            self.assertIn(prefix + ":", message)
            self.assertNotIn(prefix + ": " + prefix + ":", message)
        self.assertIn("PAIR-C01", message)
        self.assertIn("SESS-C01", message)
        self.assertIn("NET-C01", message)

    def test_repository_validation_aggregates_invalid_utf8_and_missing_specs(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            pair_path = root / validator.SPECS["PAIR"][0]
            sess_path = root / validator.SPECS["SESS"][0]
            pair_path.parent.mkdir(parents=True, exist_ok=True)
            sess_path.parent.mkdir(parents=True, exist_ok=True)
            pair_path.write_bytes(bytes([255, 254]))
            sess_path.write_text("", encoding="utf-8")

            with self.assertRaises(validator.SpecError) as raised:
                validator.validate_repository(root)

        message = str(raised.exception)
        self.assertIn("PAIR:", message)
        self.assertIn("utf-8", message.lower())
        self.assertIn("SESS:", message)
        self.assertIn("SESS-C01", message)
        self.assertIn("NET:", message)
        self.assertIn("specification not found", message)
        for prefix in ("PAIR", "SESS", "NET"):
            self.assertNotIn(prefix + ": " + prefix + ":", message)

    def test_missing_specification_fails_repository_validation(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            with self.assertRaisesRegex(validator.SpecError, "PAIR: specification not found"):
                validator.validate_repository(Path(temporary_root))


    def test_json_cli_aggregates_mixed_specification_failures(self):
        from contextlib import redirect_stdout
        import io
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            pair_path = root / validator.SPECS["PAIR"][0]
            sess_path = root / validator.SPECS["SESS"][0]
            pair_path.parent.mkdir(parents=True, exist_ok=True)
            sess_path.parent.mkdir(parents=True, exist_ok=True)
            pair_path.write_bytes(bytes([255, 254]))
            sess_path.write_text("", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                result = validator.main(["--root", temporary_root, "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 1)
        self.assertFalse(payload["ok"])
        error = payload["error"]
        self.assertIn("PAIR:", error)
        self.assertIn("utf-8", error.lower())
        self.assertIn("SESS:", error)
        self.assertIn("SESS-C01", error)
        self.assertIn("NET:", error)
        self.assertIn("specification not found", error)
        for prefix in ("PAIR", "SESS", "NET"):
            self.assertNotIn(prefix + ": " + prefix + ":", error)
        self.assertEqual(payload["scope"], "documentation-integrity-only")
        self.assertFalse(payload["runtime_security_tested"])


    def test_text_cli_aggregates_mixed_specification_failures(self):
        from contextlib import redirect_stderr, redirect_stdout
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            pair_path = root / validator.SPECS["PAIR"][0]
            sess_path = root / validator.SPECS["SESS"][0]
            pair_path.parent.mkdir(parents=True, exist_ok=True)
            sess_path.parent.mkdir(parents=True, exist_ok=True)
            pair_path.write_bytes(bytes([255, 254]))
            sess_path.write_text("", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = validator.main(["--root", temporary_root])

        diagnostic = stderr.getvalue()
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("FAIL repository validation failed", diagnostic)
        self.assertIn("PAIR:", diagnostic)
        self.assertIn("utf-8", diagnostic.lower())
        self.assertIn("SESS:", diagnostic)
        self.assertIn("SESS-C01", diagnostic)
        self.assertIn("NET:", diagnostic)
        self.assertIn("specification not found", diagnostic)
        for prefix in ("PAIR", "SESS", "NET"):
            self.assertNotIn(prefix + ": " + prefix + ":", diagnostic)
        self.assertNotIn("Traceback", diagnostic)


    def test_regular_file_root_reports_all_specs_as_missing(self):
        import tempfile

        with tempfile.NamedTemporaryFile() as invalid_root:
            with self.assertRaises(validator.SpecError) as raised:
                validator.validate_repository(Path(invalid_root.name))

        message = str(raised.exception)
        self.assertIn("PAIR: specification not found", message)
        self.assertIn("SESS: specification not found", message)
        self.assertIn("NET: specification not found", message)
        positions = [message.index(prefix + ":") for prefix in ("PAIR", "SESS", "NET")]
        self.assertEqual(positions, sorted(positions))


    def test_repository_aggregate_diagnostics_follow_specification_order(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            pair_path = root / validator.SPECS["PAIR"][0]
            sess_path = root / validator.SPECS["SESS"][0]
            pair_path.parent.mkdir(parents=True, exist_ok=True)
            sess_path.parent.mkdir(parents=True, exist_ok=True)
            pair_path.write_bytes(bytes([255, 254]))
            sess_path.write_text("", encoding="utf-8")

            with self.assertRaises(validator.SpecError) as raised:
                validator.validate_repository(root)

        message = str(raised.exception)
        positions = [message.index(prefix + ":") for prefix in ("PAIR", "SESS", "NET")]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("utf-8", message.lower())
        self.assertIn("SESS-C01", message)
        self.assertIn("NET: specification not found", message)


    def test_repository_validation_aggregates_filesystem_read_errors(self):
        from unittest.mock import patch
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            pair_path = root / validator.SPECS["PAIR"][0]
            sess_path = root / validator.SPECS["SESS"][0]
            pair_path.parent.mkdir(parents=True, exist_ok=True)
            sess_path.parent.mkdir(parents=True, exist_ok=True)
            pair_path.write_text("| PAIR-C01 | Condition | Assertion |\n", encoding="utf-8")
            sess_path.write_text("", encoding="utf-8")
            original_read_text = Path.read_text

            def controlled_read_text(path, *args, **kwargs):
                if path == pair_path:
                    raise PermissionError("simulated read denial")
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", autospec=True,
                              side_effect=controlled_read_text):
                with self.assertRaises(validator.SpecError) as raised:
                    validator.validate_repository(root)

        message = str(raised.exception)
        self.assertIn("PAIR: simulated read denial", message)
        self.assertIn("SESS: missing SESS-C01", message)
        self.assertIn("NET: specification not found", message)
        positions = [message.index(prefix + ":") for prefix in ("PAIR", "SESS", "NET")]
        self.assertEqual(positions, sorted(positions))


    def test_cli_modes_render_aggregated_filesystem_read_errors(self):
        from contextlib import redirect_stderr, redirect_stdout
        from unittest.mock import patch
        import io
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            pair_path = root / validator.SPECS["PAIR"][0]
            pair_path.parent.mkdir(parents=True, exist_ok=True)
            pair_path.write_text("| PAIR-C01 | Condition | Assertion |\n", encoding="utf-8")
            original_read_text = Path.read_text

            def controlled_read_text(path, *args, **kwargs):
                if path == pair_path:
                    raise PermissionError("simulated CLI read denial")
                return original_read_text(path, *args, **kwargs)

            for json_mode in (False, True):
                with self.subTest(json_mode=json_mode):
                    stdout = io.StringIO()
                    stderr = io.StringIO()
                    argv = ["--root", temporary_root]
                    if json_mode:
                        argv.append("--json")
                    with patch.object(Path, "read_text", autospec=True,
                                      side_effect=controlled_read_text):
                        with redirect_stdout(stdout), redirect_stderr(stderr):
                            result = validator.main(argv)

                    self.assertEqual(result, 1)
                    self.assertNotIn("Traceback", stdout.getvalue() + stderr.getvalue())
                    if json_mode:
                        payload = json.loads(stdout.getvalue())
                        self.assertFalse(payload["ok"])
                        self.assertIn("PAIR: simulated CLI read denial", payload["error"])
                        self.assertIn("NET: specification not found", payload["error"])
                        self.assertEqual(stderr.getvalue(), "")
                        self.assertFalse(payload["runtime_security_tested"])
                    else:
                        self.assertEqual(stdout.getvalue(), "")
                        self.assertIn("FAIL repository validation failed", stderr.getvalue())
                        self.assertIn("PAIR: simulated CLI read denial", stderr.getvalue())
                        self.assertIn("NET: specification not found", stderr.getvalue())


    def test_text_cli_success_labels_documentation_only_scope(self):
        from contextlib import redirect_stdout
        import io
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
                result = validator.main(["--root", temporary_root])

        rendered = output.getvalue()
        self.assertEqual(result, 0)
        for prefix, case_count in (("PAIR", 22), ("SESS", 40), ("NET", 42)):
            self.assertIn(f"PASS {prefix}: {case_count} unique, contiguous cases validated", rendered)
        self.assertIn("documentation integrity only", rendered)
        self.assertIn("no runtime security behavior was tested", rendered)


if __name__ == "__main__":
    unittest.main()