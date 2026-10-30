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
        tx = transition_transaction(self.tx, "cancelled")
        with self.assertRaisesRegex(TransactionStateError, "not allowed"):
            transition_transaction(tx, "approval_verified", {
                "approval_id": "a1", "verification_ref": "v1", "authority": "aegis"
            })

    def test_input_record_is_not_mutated(self):
        original = dict(self.tx)
        transition_transaction(self.tx, "cancelled")
        self.assertEqual(self.tx, original)


if __name__ == "__main__":
    unittest.main()
