import json
import tempfile
import unittest
import uuid
from pathlib import Path

from validate_ledger import validate


class LedgerValidationTests(unittest.TestCase):
    def record(self, **overrides):
        item = {
            "completion_id": "ATLAS-01-000001",
            "response_id": str(uuid.uuid4()),
            "agent_id": "ATLAS-01",
            "branch": "agent/01-fedora-base",
            "response_summary": "Implemented and tested one focused resolver fix.",
            "evidence_refs": ["https://github.com/otta-komban/TuskerOS/commit/abc1234"],
            "recorded_at_utc": "2026-10-31T08:00:00Z",
            "record_version": 1,
        }
        item.update(overrides)
        return item

    def validate_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            path.write_text(text, encoding="utf-8")
            return validate(path)

    def test_empty_ledger_is_valid(self):
        self.assertEqual(self.validate_text(""), [])

    def test_one_record_is_valid(self):
        self.assertEqual(self.validate_text(json.dumps(self.record()) + "\n"), [])

    def test_coordinator_record_is_valid(self):
        item = self.record(
            completion_id="COORDINATOR-000001",
            agent_id="COORDINATOR",
            branch="main",
            response_summary="Verified and recorded one coordinator-owned project result.",
            evidence_refs=["https://github.com/otta-komban/TuskerOS/pull/49"],
        )
        self.assertEqual(self.validate_text(json.dumps(item) + "\\n"), [])

    def test_coordinator_wrong_branch_is_rejected(self):
        item = self.record(
            completion_id="COORDINATOR-000001", agent_id="COORDINATOR", branch="coordinator/other"
        )
        errors = self.validate_text(json.dumps(item) + "\\n")
        self.assertTrue(any("branch does not match COORDINATOR" in error for error in errors))

    def test_duplicate_response_is_rejected(self):
        item = self.record()
        second = self.record(completion_id="ATLAS-01-000002", response_id=item["response_id"])
        errors = self.validate_text(json.dumps(item) + "\n" + json.dumps(second) + "\n")
        self.assertTrue(any("duplicate response_id" in error for error in errors))

    def test_multiple_records_need_sequential_ids(self):
        first = self.record()
        second = self.record(completion_id="ATLAS-01-000003")
        errors = self.validate_text(json.dumps(first) + "\n" + json.dumps(second) + "\n")
        self.assertTrue(any("expected completion_id ATLAS-01-000002" in error for error in errors))

    def test_wrong_branch_is_rejected(self):
        errors = self.validate_text(json.dumps(self.record(branch="main")) + "\n")
        self.assertTrue(any("branch does not match" in error for error in errors))

    def test_blank_lines_are_rejected(self):
        self.assertTrue(any("blank lines" in error for error in self.validate_text("\n")))


if __name__ == "__main__":
    unittest.main()
