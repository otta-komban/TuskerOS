import unittest

from marketplace.tools.transaction_contract import (
    TransactionContractError,
    build_audit_event,
    build_rollback_report,
    create_transaction_preview,
    revalidate_snapshot,
    validate_approval_claims,
)


class TransactionContractTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "state_version": 1,
            "packages": [{"package_id": "demo.app", "version": "1.0.0",
                          "owners": [{"kind": "bundle", "id": "demo"}],
                          "dependencies": []}],
        }
        self.operations = [{"action": "remove", "package_id": "demo.app", "version": "1.0.0"}]
        self.preview = create_transaction_preview(self.snapshot, self.operations, "txn-001")
        self.token = {
            "token_id": "approval-1", "actor": "user:local", "authority": "aegis-policy",
            "plan_digest": self.preview["plan_digest"],
            "snapshot_digest": self.preview["snapshot_digest"],
            "operations_digest": self.preview["operations_digest"],
            "approved_actions": ["remove"], "expires_at": "2026-11-01T00:00:00Z",
        }

    def test_preview_is_bound_to_snapshot_and_operations(self):
        self.assertEqual(self.preview["execution"], "not_performed")
        self.assertEqual(len(self.preview["plan_digest"]), 64)

    def test_duplicate_operations_rejected(self):
        with self.assertRaisesRegex(TransactionContractError, "duplicate"):
            create_transaction_preview(self.snapshot, self.operations * 2, "txn-2")

    def test_changed_snapshot_fails_revalidation(self):
        changed = {"state_version": 1, "packages": []}
        with self.assertRaisesRegex(TransactionContractError, "changed"):
            revalidate_snapshot(self.preview, changed)

    def test_unchanged_snapshot_revalidates(self):
        self.assertTrue(revalidate_snapshot(self.preview, self.snapshot))

    def test_matching_approval_claims_validate_as_unverified(self):
        result = validate_approval_claims(self.token, self.preview, "2026-10-31T12:00:00Z")
        self.assertEqual(result["status"], "claims_valid_unverified")

    def test_expired_approval_rejected(self):
        with self.assertRaisesRegex(TransactionContractError, "expired"):
            validate_approval_claims(self.token, self.preview, "2026-11-02T00:00:00Z")

    def test_tampered_plan_digest_rejected(self):
        token = dict(self.token, plan_digest="0" * 64)
        with self.assertRaisesRegex(TransactionContractError, "plan_digest"):
            validate_approval_claims(token, self.preview, "2026-10-31T12:00:00Z")

    def test_incomplete_action_scope_rejected(self):
        token = dict(self.token, approved_actions=["install"])
        with self.assertRaisesRegex(TransactionContractError, "does not cover"):
            validate_approval_claims(token, self.preview, "2026-10-31T12:00:00Z")

    def test_rollback_report_is_descriptive_only(self):
        report = build_rollback_report("txn-1", "rollback_failed", ["lib.a"], ["demo.app"])
        self.assertEqual(report["execution"], "not_performed_by_contract")

    def test_rollback_failed_requires_failed_package(self):
        with self.assertRaisesRegex(TransactionContractError, "requires failed"):
            build_rollback_report("txn-1", "rollback_failed", ["lib.a"], [])

    def test_audit_event_rejects_secret_like_fields(self):
        with self.assertRaisesRegex(TransactionContractError, "sensitive"):
            build_audit_event("txn-1", "2026-10-31T12:00:00Z", "user", "approved",
                              "a" * 64, "b" * 64, "ok", {"approval_token": "secret"})

    def test_audit_event_accepts_allowlisted_details(self):
        event = build_audit_event("txn-1", "2026-10-31T12:00:00Z", "user", "previewed",
                                  "a" * 64, "b" * 64, "prepared", {"package_count": 2})
        self.assertEqual(event["details"]["package_count"], 2)


if __name__ == "__main__":
    unittest.main()
