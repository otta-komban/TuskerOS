import json
import unittest
from pathlib import Path

from marketplace.tools.transaction_state import (
    TransactionStateError,
    transition_transaction,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "transaction-state-vectors.json"


class TransactionStateVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vectors = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def new_transaction(self):
        return {
            "transaction_id": "fixture-transaction",
            "state": "prepared",
            "plan_digest": "a" * 64,
            "snapshot_digest": "b" * 64,
        }

    def test_all_valid_transition_vectors(self):
        self.assertEqual(self.vectors["version"], 1)
        for vector in self.vectors["valid"]:
            with self.subTest(vector=vector["id"]):
                transaction = self.new_transaction()
                for step in vector["steps"]:
                    transaction = transition_transaction(
                        transaction, step["event"], step["evidence"]
                    )
                self.assertEqual(transaction["state"], vector["final_state"])
                self.assertEqual(transaction["terminal"], vector["terminal"])

    def test_all_invalid_transition_vectors_fail_closed(self):
        for vector in self.vectors["invalid"]:
            with self.subTest(vector=vector["id"]):
                transaction = self.new_transaction()
                with self.assertRaises(TransactionStateError):
                    for step in vector["steps"]:
                        transaction = transition_transaction(
                            transaction, step["event"], step["evidence"]
                        )


if __name__ == "__main__":
    unittest.main()
