"""Additional CommonMark tab-boundary regression tests for the spec validator."""
import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("validate_conformance_specs.py")
MODULE_SPEC = importlib.util.spec_from_file_location("pilot08_spec_validator_tabs", MODULE_PATH)
validator = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = validator
MODULE_SPEC.loader.exec_module(validator)


class TabFenceBoundaryTests(unittest.TestCase):
    def test_tab_indented_fence_opener_is_indented_code_not_a_fence(self):
        markdown = (
            "| PAIR-C01 | Real case | Reject |\n"
            "\t```markdown\n"
            "| PAIR-C01 | Tab-indented code example | Ignored |\n"
            "| PAIR-C02 | Outside code block | Reject |\n"
        )
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [
                ("PAIR-C01", "Real case", "Reject"),
                ("PAIR-C02", "Outside code block", "Reject"),
            ],
        )

    def test_tab_indented_fence_closer_does_not_close_open_fence(self):
        markdown = (
            "| PAIR-C01 | Before fence | Reject |\n"
            "```markdown\n"
            "| PAIR-C02 | Inside fence | Ignored |\n"
            "\t```\n"
            "| PAIR-C03 | Still inside unclosed fence | Ignored |\n"
        )
        self.assertEqual(
            validator.parse_case_rows(markdown, "PAIR"),
            [("PAIR-C01", "Before fence", "Reject")],
        )


if __name__ == "__main__":
    unittest.main()
