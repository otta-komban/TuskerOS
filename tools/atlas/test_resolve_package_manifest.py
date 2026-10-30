"""Unit tests for the read-only ATLAS package resolver helpers."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from resolve_package_manifest import parse_query_matches, read_manifest


class QueryResultTests(unittest.TestCase):
    def test_single_nevra_and_repository(self):
        result = parse_query_matches(
            "bash-0:5.2.26-3.fc44.x86_64\tfedora\n"
        )
        self.assertEqual(result, ("bash-0:5.2.26-3.fc44.x86_64", "fedora"))

    def test_duplicate_identical_rows_are_collapsed(self):
        row = "bash-0:5.2.26-3.fc44.x86_64\tfedora"
        self.assertEqual(parse_query_matches(f"{row}\n{row}\n"), tuple(row.split("\t")))

    def test_same_nevra_from_multiple_repositories_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "ambiguous repository"):
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.x86_64\tfedora\n"
                "bash-0:5.2.26-3.fc44.x86_64\tthird-party\n"
            )

    def test_multiple_nevras_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "ambiguous NEVRA"):
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.x86_64\tfedora\n"
                "bash-0:5.2.27-1.fc44.x86_64\tfedora\n"
            )

    def test_malformed_query_row_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "unexpected"):
            parse_query_matches("bash-5.2.26-3.fc44.x86_64")

    def test_empty_query_output_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "no available match"):
            parse_query_matches("  \n")


class ManifestTests(unittest.TestCase):
    def read_text(self, content: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "manifest.csv"
        path.write_text(content, encoding="utf-8")
        return read_manifest(path)

    def test_valid_row_is_accepted(self):
        rows = self.read_text(
            "layer,package,owner,required,rationale\n"
            "desktop,bash,ATLAS-01,true,base shell\n"
        )
        self.assertEqual(rows[0]["package"], "bash")

    def test_empty_owner_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "owner must be non-empty"):
            self.read_text(
                "layer,package,owner,required,rationale\n"
                "desktop,bash,,true,base shell\n"
            )

    def test_empty_rationale_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "rationale must be non-empty"):
            self.read_text(
                "layer,package,owner,required,rationale\n"
                "desktop,bash,ATLAS-01,true,\n"
            )


if __name__ == "__main__":
    unittest.main()
