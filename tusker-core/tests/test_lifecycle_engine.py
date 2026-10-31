import sys
import unittest
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.lifecycle import (
    InMemoryLifecycleStore, LifecycleEngine, InvalidTransition,
    VersionConflict, IdempotencyConflict,
)


class LifecycleEngineTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryLifecycleStore()
        self.engine = LifecycleEngine(self.store)
        self.task = self.engine.create_task("00000000-0000-4000-8000-000000000001", "00000000-0000-4000-8000-000000000002")

    def move(self, target, **kwargs):
        current = self.store.get("00000000-0000-4000-8000-000000000001")
        return self.engine.transition("00000000-0000-4000-8000-000000000001", target, expected_version=current["version"], **kwargs)

    def test_happy_path_requires_verification(self):
        self.move("planning")
        self.move("running")
        self.move("verifying")
        with self.assertRaises(InvalidTransition):
            self.move("completed")
        result = self.move("completed", verified=True)
        self.assertEqual(result["state"], "completed")

    def test_invalid_transition_and_terminal_immutability(self):
        with self.assertRaises(InvalidTransition):
            self.move("completed", verified=True)
        self.move("planning")
        self.move("running")
        self.move("verifying")
        self.move("completed", verified=True)
        with self.assertRaises(InvalidTransition):
            self.move("failed")

    def test_version_conflict(self):
        with self.assertRaises(VersionConflict):
            self.engine.transition("00000000-0000-4000-8000-000000000001", "planning", expected_version=9)

    def test_idempotent_transition_replay(self):
        first = self.engine.transition("00000000-0000-4000-8000-000000000001", "planning", expected_version=1, idempotency_key="plan-1")
        second = self.engine.transition("00000000-0000-4000-8000-000000000001", "planning", expected_version=1, idempotency_key="plan-1")
        self.assertEqual(first, second)
        self.assertEqual(len(self.store.events("00000000-0000-4000-8000-000000000001")), 2)
        with self.assertRaises(IdempotencyConflict):
            self.engine.transition("00000000-0000-4000-8000-000000000001", "planning", expected_version=1, idempotency_key="plan-1", event_type="different")

    def test_cancellation_is_request_then_confirmed_stop(self):
        self.move("planning")
        self.move("running")
        requested = self.engine.request_cancellation("00000000-0000-4000-8000-000000000001", expected_version=3)
        self.assertEqual(requested["state"], "running")
        with self.assertRaises(InvalidTransition):
            self.engine.confirm_cancellation("00000000-0000-4000-8000-000000000001", expected_version=4, operation_stopped=False)
        stopped = self.engine.confirm_cancellation("00000000-0000-4000-8000-000000000001", expected_version=4, operation_stopped=True)
        self.assertEqual(stopped["state"], "cancelled")

    def test_partial_requires_known_side_effects(self):
        self.move("planning")
        self.move("running")
        with self.assertRaises(InvalidTransition):
            self.move("partially_completed")
        self.assertEqual(self.move("partially_completed", side_effects=True)["state"], "partially_completed")

    def test_unknown_outcome_cannot_be_failed(self):
        self.move("planning")
        self.move("running")
        with self.assertRaises(InvalidTransition):
            self.move("failed", details={"outcome_unknown": True})

    def test_replay_is_contiguous_and_never_executes(self):
        self.move("planning")
        replay = self.engine.replay("00000000-0000-4000-8000-000000000001")
        self.assertEqual([e["sequence"] for e in replay["events"]], [1, 2])
        self.assertEqual(replay["task"]["state"], "planning")


    def test_duplicate_event_id_is_rejected(self):
        initial_event_id = self.store.events("00000000-0000-4000-8000-000000000001")[0]["event_id"]
        with self.assertRaises(IdempotencyConflict):
            self.engine.transition(
                "00000000-0000-4000-8000-000000000001", "planning",
                expected_version=1, event_id=initial_event_id,
            )

    def test_returned_snapshots_are_isolated_from_store(self):
        task = self.store.get("00000000-0000-4000-8000-000000000001")
        task["state"] = "completed"
        task["origin"]["kind"] = "remote"
        self.assertEqual(self.store.get("00000000-0000-4000-8000-000000000001")["state"], "queued")
        self.assertEqual(self.store.get("00000000-0000-4000-8000-000000000001")["origin"]["kind"], "local")
        events = self.store.events("00000000-0000-4000-8000-000000000001")
        events[0]["state"] = "failed"
        self.assertEqual(self.store.events("00000000-0000-4000-8000-000000000001")[0]["state"], "queued")

    def test_concurrent_writers_have_one_winner(self):
        barrier = threading.Barrier(2)
        outcomes = []
        lock = threading.Lock()

        def writer(target):
            barrier.wait()
            try:
                result = self.engine.transition(
                    "00000000-0000-4000-8000-000000000001", target,
                    expected_version=1,
                )
                outcome = ("ok", result["state"])
            except VersionConflict:
                outcome = ("conflict", target)
            with lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=writer, args=("planning",)),
            threading.Thread(target=writer, args=("failed",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(kind for kind, _ in outcomes), ["conflict", "ok"])
        self.assertEqual(self.store.get("00000000-0000-4000-8000-000000000001")["version"], 2)
        self.assertEqual(len(self.store.events("00000000-0000-4000-8000-000000000001")), 2)


if __name__ == "__main__":
    unittest.main()
