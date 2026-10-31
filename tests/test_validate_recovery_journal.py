"""Regression tests for the read-only installer recovery journal validator."""
import unittest

from scripts.validate_recovery_journal import (
    GENESIS_CHECKSUM, MAX_JOURNAL_BYTES, MAX_RECORDS, MAX_RECORD_BYTES,
    JournalValidationError, parse_jsonl, record_checksum,
    replay_eligibility, seal_record, validate_journal,
)


def chain(states, *, idempotent=False):
    result = []
    previous = GENESIS_CHECKSUM
    for sequence, state in enumerate(states, 1):
        record = seal_record(sequence=sequence, operation_id="install-001",
                             state=state, idempotent=idempotent,
                             previous_checksum=previous)
        result.append(record)
        previous = record["checksum"]
    return result


class RecoveryJournalTests(unittest.TestCase):
    def test_valid_interrupted_journal(self):
        report = validate_journal(chain(["planned", "prepared", "executing",
                                         "interrupted"], idempotent=True))
        self.assertTrue(report.valid, report.errors)
        self.assertEqual(report.last_state, "interrupted")
        self.assertEqual(report.last_sequence, 4)

    def test_duplicate_sequence_is_rejected(self):
        records = chain(["planned", "prepared"])
        records[1]["sequence"] = 1
        records[1]["checksum"] = record_checksum(records[1])
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("duplicate sequence" in e for e in report.errors))

    def test_tampered_record_is_rejected(self):
        records = chain(["planned", "prepared"])
        records[0]["state"] = "failed"
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("checksum mismatch" in e for e in report.errors))

    def test_broken_checksum_link_is_rejected(self):
        records = chain(["planned", "prepared"])
        records[1]["previous_checksum"] = "f" * 64
        records[1]["checksum"] = record_checksum(records[1])
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("previous checksum" in e for e in report.errors))

    def test_illegal_transition_is_rejected(self):
        report = validate_journal(chain(["planned", "executing"]))
        self.assertFalse(report.valid)
        self.assertTrue(any("illegal transition" in e for e in report.errors))

    def test_operation_identity_cannot_change(self):
        records = chain(["planned", "prepared"])
        records[1]["operation_id"] = "different-operation"
        records[1]["checksum"] = record_checksum(records[1])
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("operation_id changed" in e for e in report.errors))

    def test_incomplete_record_is_rejected(self):
        records = chain(["planned"])
        del records[0]["idempotent"]
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("missing fields" in e for e in report.errors))

    def test_jsonl_rejects_truncated_blank_and_duplicate_key_records(self):
        with self.assertRaises(JournalValidationError):
            parse_jsonl('{"sequence":1')
        with self.assertRaises(JournalValidationError):
            parse_jsonl('{"sequence":1}\n\n')
        with self.assertRaises(JournalValidationError):
            parse_jsonl('{"sequence":1,"sequence":2}')

    def test_non_string_state_is_rejected_without_crashing(self):
        records = chain(["planned"])
        records[0]["state"] = []
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("unknown state" in e for e in report.errors))

    def test_replay_requires_all_external_gates(self):
        record = chain(["planned", "prepared", "executing", "interrupted"],
                       idempotent=True)[-1]
        self.assertFalse(replay_eligibility(
            record, preconditions_verified=False,
            authorization_current=True)[0])
        self.assertFalse(replay_eligibility(
            record, preconditions_verified=True,
            authorization_current=False)[0])
        eligible, reason = replay_eligibility(
            record, preconditions_verified=True, authorization_current=True)
        self.assertTrue(eligible)
        self.assertIn("candidate only", reason)

    def test_non_idempotent_operation_cannot_be_replayed(self):
        record = chain(["planned", "prepared", "executing", "interrupted"],
                       idempotent=False)[-1]
        eligible, _ = replay_eligibility(
            record, preconditions_verified=True, authorization_current=True)
        self.assertFalse(eligible)


    def test_parser_enforces_total_size_limit(self):
        with self.assertRaisesRegex(JournalValidationError, "maximum size"):
            parse_jsonl(" " * (MAX_JOURNAL_BYTES + 1))

    def test_parser_enforces_record_size_limit(self):
        oversized = '{"payload":"' + ("x" * MAX_RECORD_BYTES) + '"}'
        with self.assertRaisesRegex(JournalValidationError, "record exceeds"):
            parse_jsonl(oversized)

    def test_parser_enforces_record_count_limit(self):
        with self.assertRaisesRegex(JournalValidationError, "maximum record count"):
            parse_jsonl("{}\\n" * (MAX_RECORDS + 1))

    def test_validator_bounds_iterable_record_count(self):
        report = validate_journal({} for _ in range(MAX_RECORDS + 1))
        self.assertFalse(report.valid)
        self.assertEqual(report.record_count, MAX_RECORDS)
        self.assertTrue(any("maximum record count" in e for e in report.errors))

    def test_validator_rejects_non_iterable_input(self):
        report = validate_journal(None)
        self.assertFalse(report.valid)
        self.assertIn("journal records must be iterable", report.errors)


if __name__ == "__main__":
    unittest.main()
