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


class HostileJournalDict(dict):
    def keys(self):
        raise RuntimeError("keys must not be called")

    def items(self):
        raise RuntimeError("items must not be called")

    def __getitem__(self, key):
        raise RuntimeError("getitem must not be called")


class HostileKey:
    def __repr__(self):
        raise RuntimeError("repr must not be called")


class HostileValue:
    def __repr__(self):
        raise RuntimeError("repr must not be called")

    def __str__(self):
        raise RuntimeError("str must not be called")

    def __eq__(self, other):
        raise RuntimeError("eq must not be called")


class RecoveryJournalTests(unittest.TestCase):
    def test_journal_must_begin_in_planned_state(self):
        report = validate_journal(chain(["interrupted"]))
        self.assertFalse(report.valid)
        self.assertTrue(any("initial state must be planned" in e for e in report.errors))

    def test_idempotency_declaration_must_remain_stable(self):
        records = chain(["planned", "prepared"], idempotent=True)
        records[1]["idempotent"] = False
        records[1]["checksum"] = record_checksum(records[1])
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("idempotent declaration changed" in e for e in report.errors))

    def test_checksum_fields_require_lowercase_sha256_hex(self):
        records = chain(["planned"])
        records[0]["checksum"] = "A" * 64
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("checksum must be 64 lowercase hexadecimal" in e for e in report.errors))
        records = chain(["planned", "prepared"])
        records[1]["previous_checksum"] = "g" * 64
        records[1]["checksum"] = record_checksum(records[1])
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("previous_checksum must be 64 lowercase hexadecimal" in e for e in report.errors))

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

    def test_unknown_state_followed_by_record_is_rejected_without_crashing(self):
        records = chain(["planned", "prepared"])
        records[0]["state"] = "unknown"
        records[0]["checksum"] = record_checksum(records[0])
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("unknown state" in e for e in report.errors))

    def test_jsonl_preserves_unicode_line_separator_inside_string(self):
        record = seal_record(sequence=1, operation_id="install\u2028one",
                             state="planned", idempotent=False)
        encoded = __import__("json").dumps(record, ensure_ascii=False) + "\n"
        parsed = parse_jsonl(encoded)
        self.assertEqual(parsed[0]["operation_id"], "install\u2028one")

    def test_jsonl_accepts_crlf_and_one_final_newline(self):
        record = seal_record(sequence=1, operation_id="install-001",
                             state="planned", idempotent=False)
        encoded = __import__("json").dumps(record) + "\r\n"
        self.assertEqual(parse_jsonl(encoded), [record])

    def test_non_string_state_is_rejected_without_crashing(self):
        records = chain(["planned"])
        records[0]["state"] = []
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("unknown state" in e for e in report.errors))

    def test_non_string_object_keys_are_rejected_without_formatting_them(self):
        records = chain(["planned"])
        records[0][HostileKey()] = "unexpected"
        report = validate_journal(records)
        self.assertFalse(report.valid)
        self.assertTrue(any("object keys must be plain strings" in e
                            for e in report.errors))

    def test_dict_subclasses_are_rejected_without_invoking_overrides(self):
        hostile = HostileJournalDict(chain(["planned"])[0])
        report = validate_journal([hostile])
        self.assertFalse(report.valid)
        self.assertTrue(any("expected a plain dictionary" in e
                            for e in report.errors))

    def test_record_checksum_rejects_dict_subclasses(self):
        hostile = HostileJournalDict(chain(["planned"])[0])
        with self.assertRaisesRegex(JournalValidationError, "plain dictionary"):
            record_checksum(hostile)

    def test_malformed_scalar_values_are_rejected_without_custom_hooks(self):
        record = chain(["planned"])[0]
        record["sequence"] = HostileValue()
        record["operation_id"] = HostileValue()
        record["state"] = HostileValue()
        record["previous_checksum"] = HostileValue()
        record["checksum"] = HostileValue()
        report = validate_journal([record])
        self.assertFalse(report.valid)
        self.assertTrue(any("sequence must be a positive integer" in e
                            for e in report.errors))
        self.assertTrue(any("state must be a plain string" in e
                            for e in report.errors))

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
            parse_jsonl("{}\n" * (MAX_RECORDS + 1))

    def test_validator_bounds_iterable_record_count(self):
        report = validate_journal({} for _ in range(MAX_RECORDS + 1))
        self.assertFalse(report.valid)
        self.assertEqual(report.record_count, MAX_RECORDS)
        self.assertTrue(any("maximum record count" in e for e in report.errors))

    def test_validator_rejects_non_iterable_input(self):
        report = validate_journal(None)
        self.assertFalse(report.valid)
        self.assertIn("journal records must be iterable", report.errors)

    def test_validator_reports_iterator_runtime_failure(self):
        def broken_records():
            yield chain(["planned"])[0]
            raise RuntimeError("fixture iterator failure")

        report = validate_journal(broken_records())
        self.assertFalse(report.valid)
        self.assertEqual(report.record_count, 0)
        self.assertTrue(any("journal iteration failed: RuntimeError" in e
                            for e in report.errors))


if __name__ == "__main__":
    unittest.main()
