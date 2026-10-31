import copy
import unittest

from scripts.validate_release_report import DuplicateJSONKeyError, strict_json_loads, validate_report

DIGEST = "a" * 64


def valid_report():
    return {
        "report_version": "1.0.0",
        "report_id": "fixture-001",
        "subject": {"manifest_sha256": DIGEST, "release_id": "synthetic-fixture"},
        "validator": {"name": "fixture-validator", "version": "0.0-test"},
        "started_at_utc": "2026-10-30T10:00:00Z",
        "finished_at_utc": "2026-10-30T10:00:02Z",
        "overall_status": "passed",
        "summary": {"total": 1, "passed": 1, "failed": 0, "blocked": 0, "not_run": 0},
        "checks": [{
            "check_id": "fixture-schema-check",
            "category": "schema",
            "status": "passed",
            "subject_digest": DIGEST,
            "message": "Synthetic test fixture only; not release evidence."
        }]
    }


class ReleaseReportSemanticTests(unittest.TestCase):
    def test_strict_json_parser_accepts_unique_nested_keys(self):
        self.assertEqual(strict_json_loads('{"outer":{"inner":1}}'), {"outer": {"inner": 1}})

    def test_strict_json_parser_rejects_duplicate_top_level_key(self):
        with self.assertRaises(DuplicateJSONKeyError):
            strict_json_loads('{"status":"passed","status":"failed"}')

    def test_strict_json_parser_rejects_duplicate_nested_key(self):
        with self.assertRaises(DuplicateJSONKeyError):
            strict_json_loads('{"subject":{"manifest_sha256":"a","manifest_sha256":"b"}}')

    def test_accepts_consistent_report(self):
        self.assertEqual(validate_report(valid_report()), [])

    def test_rejects_summary_count_mismatch(self):
        report = valid_report()
        report["summary"]["passed"] = 0
        self.assertTrue(any("summary.passed" in e for e in validate_report(report)))

    def test_rejects_wrong_overall_status(self):
        report = valid_report()
        report["overall_status"] = "blocked"
        self.assertTrue(any("overall_status" in e for e in validate_report(report)))

    def test_rejects_mismatched_check_subject(self):
        report = valid_report()
        report["checks"][0]["subject_digest"] = "b" * 64
        self.assertTrue(any("subject_digest" in e for e in validate_report(report)))

    def test_rejects_duplicate_check_ids(self):
        report = valid_report()
        report["checks"].append(copy.deepcopy(report["checks"][0]))
        report["summary"] = {"total": 2, "passed": 2, "failed": 0, "blocked": 0, "not_run": 0}
        self.assertTrue(any("duplicate" in e for e in validate_report(report)))

    def test_blocked_status_is_not_pass(self):
        report = valid_report()
        report["checks"][0]["status"] = "blocked"
        report["summary"] = {"total": 1, "passed": 0, "failed": 0, "blocked": 1, "not_run": 0}
        report["overall_status"] = "blocked"
        self.assertEqual(validate_report(report), [])

    def test_rejects_reversed_report_interval(self):
        report = valid_report()
        report["finished_at_utc"] = "2026-10-30T09:59:59Z"
        self.assertTrue(any("precedes" in e for e in validate_report(report)))

    def test_rejects_non_utc_timestamp(self):
        report = valid_report()
        report["started_at_utc"] = "2026-10-30T10:00:00+01:00"
        self.assertTrue(any("ending in Z" in e for e in validate_report(report)))

    def test_malformed_status_types_return_errors_not_exceptions(self):
        report = valid_report()
        report["checks"][0]["status"] = []
        report["overall_status"] = []
        errors = validate_report(report)
        self.assertTrue(any("status: unsupported" in error for error in errors))
        self.assertTrue(any("overall_status" in error for error in errors))

    def test_expected_manifest_digest_pin(self):
        self.assertEqual(validate_report(valid_report(), DIGEST), [])
        self.assertTrue(validate_report(valid_report(), "c" * 64))

    def test_non_string_expected_digest_returns_validation_error(self):
        errors = validate_report(valid_report(), [])
        self.assertTrue(any("--expected-manifest-digest" in error for error in errors))

    def test_fractional_summary_count_is_rejected(self):
        report = valid_report()
        report["summary"]["passed"] = 1.0
        errors = validate_report(report)
        self.assertTrue(any("summary.passed: expected integer 1" in error for error in errors))

    def test_boolean_summary_count_is_rejected(self):
        report = valid_report()
        report["summary"]["passed"] = True
        errors = validate_report(report)
        self.assertTrue(any("summary.passed: expected integer 1" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
