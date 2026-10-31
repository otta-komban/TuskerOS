import unittest

from marketplace.tools.transaction_state import (
    TransactionStateError,
    transition_transaction,
)


class TransactionStateTests(unittest.TestCase):
    def setUp(self):
        self.tx = {
            "transaction_id": "txn-1", "state": "prepared",
            "plan_digest": "a" * 64, "snapshot_digest": "b" * 64,
        }

    def test_prepared_cannot_start_execution(self):
        with self.assertRaisesRegex(TransactionStateError, "not allowed"):
            transition_transaction(self.tx, "execution_started", {"lock_ref": "lock-1"})

    def test_approval_requires_external_verification_reference(self):
        with self.assertRaisesRegex(TransactionStateError, "requires approval_id"):
            transition_transaction(self.tx, "approval_verified", {"approval_id": "a1"})

    def test_happy_path_reaches_committed(self):
        tx = transition_transaction(self.tx, "approval_verified", {
            "approval_id": "a1", "verification_ref": "aegis:verify:1", "authority": "aegis"
        })
        tx = transition_transaction(tx, "revalidated", {"snapshot_digest": "b" * 64})
        tx = transition_transaction(tx, "execution_started", {"lock_ref": "dnf-lock:1"})
        tx = transition_transaction(tx, "committed", {"result_ref": "dnf-transaction:1"})
        self.assertEqual(tx["state"], "committed")
        self.assertTrue(tx["terminal"])
        self.assertEqual(len(tx["history"]), 4)

    def test_revalidation_requires_exact_snapshot(self):
        tx = transition_transaction(self.tx, "approval_verified", {
            "approval_id": "a1", "verification_ref": "aegis:verify:1", "authority": "aegis"
        })
        with self.assertRaisesRegex(TransactionStateError, "match"):
            transition_transaction(tx, "revalidated", {"snapshot_digest": "c" * 64})

    def test_stale_snapshot_terminates_transaction(self):
        tx = transition_transaction(self.tx, "approval_verified", {
            "approval_id": "a1", "verification_ref": "aegis:verify:1", "authority": "aegis"
        })
        tx = transition_transaction(tx, "revalidated", {"snapshot_digest": "b" * 64})
        tx = transition_transaction(tx, "stale", {"observed_snapshot_digest": "c" * 64})
        self.assertTrue(tx["terminal"])

    def test_execution_requires_lock_reference(self):
        tx = transition_transaction(self.tx, "approval_verified", {
            "approval_id": "a1", "verification_ref": "aegis:verify:1", "authority": "aegis"
        })
        tx = transition_transaction(tx, "revalidated", {"snapshot_digest": "b" * 64})
        with self.assertRaisesRegex(TransactionStateError, "lock reference"):
            transition_transaction(tx, "execution_started")

    def test_rollback_failure_is_terminal_and_requires_result(self):
        tx = transition_transaction(self.tx, "approval_verified", {
            "approval_id": "a1", "verification_ref": "aegis:verify:1", "authority": "aegis"
        })
        tx = transition_transaction(tx, "revalidated", {"snapshot_digest": "b" * 64})
        tx = transition_transaction(tx, "execution_started", {"lock_ref": "pkg-lock"})
        with self.assertRaisesRegex(TransactionStateError, "result_ref"):
            transition_transaction(tx, "rollback_failed")
        tx = transition_transaction(tx, "rollback_failed", {"result_ref": "rollback:report:1"})
        self.assertTrue(tx["terminal"])

    def test_terminal_state_cannot_transition_again(self):
        tx = transition_transaction(self.tx, "cancelled", {"reason_code": "user_requested"})
        with self.assertRaisesRegex(TransactionStateError, "not allowed"):
            transition_transaction(tx, "approval_verified", {
                "approval_id": "a1", "verification_ref": "v1", "authority": "aegis"
            })

    def test_input_record_is_not_mutated(self):
        original = dict(self.tx)
        transition_transaction(self.tx, "cancelled", {"reason_code": "user_requested"})
        self.assertEqual(self.tx, original)


    def test_rejects_malformed_digest(self):
        tx = dict(self.tx, plan_digest="not-a-digest")
        with self.assertRaisesRegex(TransactionStateError, "SHA-256"):
            transition_transaction(tx, "cancelled", {"reason_code": "user_requested"})

    def test_rejects_terminal_flag_mismatch(self):
        tx = dict(self.tx, terminal=True)
        with self.assertRaisesRegex(TransactionStateError, "terminal flag"):
            transition_transaction(tx, "cancelled", {"reason_code": "user_requested"})

    def test_rejects_untrusted_arbitrary_evidence_fields(self):
        with self.assertRaisesRegex(TransactionStateError, "sensitive"):
            transition_transaction(self.tx, "cancelled", {"password": "secret"})

    def test_rejects_malformed_history(self):
        tx = dict(self.tx, history=[{"secret": "do-not-store"}])
        with self.assertRaisesRegex(TransactionStateError, "history"):
            transition_transaction(tx, "cancelled", {"reason_code": "user_requested"})

    def test_rejects_non_string_current_state(self):
        tx = dict(self.tx, state=[])
        with self.assertRaisesRegex(TransactionStateError, "state must be a non-empty string"):
            transition_transaction(tx, "cancelled", {"reason_code": "user_requested"})


    def test_stale_transition_requires_observed_snapshot_digest(self):
        tx = transition_transaction(self.tx, "approval_verified", {
            "approval_id": "a1", "verification_ref": "v1", "authority": "aegis"
        })
        tx = transition_transaction(tx, "revalidated", {"snapshot_digest": "b" * 64})
        with self.assertRaisesRegex(TransactionStateError, "observed snapshot digest"):
            transition_transaction(tx, "stale")

    def test_rejects_broken_history_chain(self):
        tx = transition_transaction(self.tx, "cancelled", {"reason_code": "user_requested"})
        tx["history"][0]["from"] = "revalidated"
        with self.assertRaisesRegex(TransactionStateError, "continuity"):
            transition_transaction(tx, "cancelled", {"reason_code": "user_requested"})

    def test_rejects_history_without_required_approval_evidence(self):
        tx = dict(self.tx, state="approval_verified", history=[{
            "from": "prepared", "event": "approval_verified", "evidence": {"approval_id": "a1"}
        }])
        with self.assertRaisesRegex(TransactionStateError, "approval verification evidence"):
            transition_transaction(tx, "revalidated", {"snapshot_digest": "b" * 64})

    def test_rejects_invalid_observed_digest_in_stale_history(self):
        tx = dict(self.tx, state="stale", terminal=True, history=[
            {"from": "prepared", "event": "approval_verified",
             "evidence": {"approval_id": "a1", "verification_ref": "v1", "authority": "aegis"}},
            {"from": "approval_verified", "event": "revalidated",
             "evidence": {"snapshot_digest": "b" * 64}},
            {"from": "revalidated", "event": "stale",
             "evidence": {"observed_snapshot_digest": "different"}}
        ])
        with self.assertRaisesRegex(TransactionStateError, "invalid stale"):
            transition_transaction(tx, "cancelled", {"reason_code": "user_requested"})


    def test_non_prepared_state_requires_history(self):
        tx = dict(self.tx, state="approval_verified")
        with self.assertRaisesRegex(TransactionStateError, "without history"):
            transition_transaction(tx, "revalidated", {"snapshot_digest": "b" * 64})


    def test_cancelled_transition_requires_non_empty_reason_code(self):
        with self.assertRaisesRegex(TransactionStateError, "cancelled requires a non-empty reason_code"):
            transition_transaction(self.tx, "cancelled")
        with self.assertRaisesRegex(TransactionStateError, "evidence must map text keys"):
            transition_transaction(self.tx, "cancelled", {"reason_code": "  "})

    def test_rejected_transition_requires_non_empty_reason_code(self):
        tx = transition_transaction(self.tx, "approval_verified", {
            "approval_id": "a1", "verification_ref": "v1", "authority": "aegis"
        })
        with self.assertRaisesRegex(TransactionStateError, "rejected requires a non-empty reason_code"):
            transition_transaction(tx, "rejected")

    def test_historical_cancelled_event_requires_reason_code(self):
        tx = dict(self.tx, state="cancelled", terminal=True, history=[{
            "from": "prepared", "event": "cancelled", "evidence": {}
        }])
        with self.assertRaisesRegex(TransactionStateError, "cancelled requires a non-empty reason_code"):
            transition_transaction(tx, "cancelled", {"reason_code": "user_requested"})

    def test_historical_rejected_event_requires_reason_code(self):
        tx = dict(self.tx, state="rejected", terminal=True, history=[
            {"from": "prepared", "event": "approval_verified", "evidence": {
                "approval_id": "a1", "verification_ref": "v1", "authority": "aegis"
            }},
            {"from": "approval_verified", "event": "rejected", "evidence": {}},
        ])
        with self.assertRaisesRegex(TransactionStateError, "rejected requires a non-empty reason_code"):
            transition_transaction(tx, "cancelled", {"reason_code": "user_requested"})


if __name__ == "__main__":
    unittest.main()
