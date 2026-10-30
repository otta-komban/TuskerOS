"""NEXUS result-to-Core lifecycle mapping tests."""
import unittest

from adapters.nexus_result import classify_tool_result


def result(status, post_state="unknown", operation_state="unknown"):
    return {
        "status": status,
        "postcondition": {"state": post_state, "details": {}},
        "cancellation": {
            "request_state": "not_requested",
            "operation_state": operation_state,
        },
        "side_effects": [],
    }


class NexusResultMappingTests(unittest.TestCase):
    def test_succeeded_requires_verified_postcondition(self):
        self.assertEqual(
            classify_tool_result(result("succeeded", "verified")), "completed"
        )
        self.assertEqual(
            classify_tool_result(result("succeeded", "not_applicable")), "completed"
        )
        self.assertEqual(
            classify_tool_result(result("succeeded", "not_verified")),
            "verification_required",
        )
        self.assertEqual(
            classify_tool_result(result("succeeded", "unknown")),
            "verification_required",
        )

    def test_needs_approval_never_becomes_authorization(self):
        self.assertEqual(
            classify_tool_result(result("needs_approval")),
            "reauthorization_required",
        )

    def test_running_remains_nonterminal(self):
        self.assertEqual(classify_tool_result(result("running")), "running")

    def test_cancelled_requires_confirmed_stop(self):
        self.assertEqual(
            classify_tool_result(result("cancelled", operation_state="stopped")),
            "cancelled",
        )
        for state in ("running", "completed", "unknown", None):
            with self.subTest(operation_state=state):
                self.assertEqual(
                    classify_tool_result(
                        result("cancelled", operation_state=state)
                    ),
                    "reconcile",
                )

    def test_failure_preserves_side_effect_review(self):
        for status in ("rejected", "failed"):
            with self.subTest(status=status):
                self.assertEqual(
                    classify_tool_result(result(status)),
                    "failed_preserve_effects",
                )

    def test_unknown_or_malformed_outcome_reconciles(self):
        self.assertEqual(
            classify_tool_result(result("unknown_outcome")), "reconcile"
        )
        self.assertEqual(classify_tool_result(result("future_status")), "reconcile")
        self.assertEqual(classify_tool_result(None), "reconcile")
        self.assertEqual(classify_tool_result({}), "reconcile")


if __name__ == "__main__":
    unittest.main()
