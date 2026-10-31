import sys
import unittest
import threading
import json
from jsonschema import Draft202012Validator, FormatChecker
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.lifecycle import (
    InMemoryLifecycleStore, LifecycleEngine, InvalidTransition, LifecycleError,
    VersionConflict, IdempotencyConflict,
)


class LifecycleEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema_dir = ROOT / "schemas"
        with (schema_dir / "task.schema.json").open(encoding="utf-8") as stream:
            task_schema = json.load(stream)
        with (schema_dir / "task-event.schema.json").open(encoding="utf-8") as stream:
            event_schema = json.load(stream)
        checker = FormatChecker()
        cls.task_validator = Draft202012Validator(task_schema, format_checker=checker)
        cls.event_validator = Draft202012Validator(event_schema, format_checker=checker)

    def assert_contract_valid(self, task, events):
        task_errors = list(self.task_validator.iter_errors(task))
        self.assertEqual(task_errors, [], "; ".join(error.message for error in task_errors))
        for event in events:
            with self.subTest(event_type=event["type"], sequence=event["sequence"]):
                errors = list(self.event_validator.iter_errors(event))
                self.assertEqual(errors, [], "; ".join(error.message for error in errors))

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

    def test_idempotency_fingerprint_covers_semantic_request_data(self):
        task_id = self.task["task_id"]
        first = self.engine.transition(
            task_id, "planning", expected_version=1,
            idempotency_key="semantic-1", details={"reason": "initial"},
        )
        replay = self.engine.transition(
            task_id, "planning", expected_version=1,
            idempotency_key="semantic-1", details={"reason": "initial"},
        )
        self.assertEqual(first, replay)
        with self.assertRaises(IdempotencyConflict):
            self.engine.transition(
                task_id, "planning", expected_version=1,
                idempotency_key="semantic-1", details={"reason": "different"},
            )
        self.assertEqual(len(self.store.events(task_id)), 2)

    def test_cancellation_idempotency_includes_reason(self):
        task_id = self.task["task_id"]
        self.move("planning")
        self.move("running")
        first = self.engine.request_cancellation(
            task_id, expected_version=3, reason="user_requested"
        )
        replay = self.engine.request_cancellation(
            task_id, expected_version=3, reason="user_requested"
        )
        self.assertEqual(first, replay)
        with self.assertRaises(IdempotencyConflict):
            self.engine.request_cancellation(
                task_id, expected_version=3, reason="shutdown"
            )
        self.assertEqual(len(self.store.events(task_id)), 4)

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

    def test_replay_rejects_invalid_state_transition(self):
        task_id = self.task["task_id"]
        self.move("planning")
        self.store._events[task_id][1]["state"] = "completed"
        with self.assertRaisesRegex(LifecycleError, "invalid state transition"):
            self.engine.replay(task_id)

    def test_replay_requires_creation_event_and_queued_initial_state(self):
        task_id = self.task["task_id"]
        self.store._events[task_id][0]["type"] = "task.state_changed"
        with self.assertRaisesRegex(LifecycleError, "task.created"):
            self.engine.replay(task_id)

    def test_replay_rejects_unknown_event_type(self):
        task_id = self.task["task_id"]
        self.store._events[task_id][0]["type"] = "task.unrecognized"
        with self.assertRaisesRegex(LifecycleError, "unknown event type"):
            self.engine.replay(task_id)

    def test_replay_rejects_missing_event_type(self):
        task_id = self.task["task_id"]
        self.store._events[task_id][0].pop("type")
        with self.assertRaisesRegex(LifecycleError, "unknown event type"):
            self.engine.replay(task_id)

    def test_replay_rejects_non_string_event_type_without_type_error(self):
        task_id = self.task["task_id"]
        self.store._events[task_id][0]["type"] = ["task.created"]
        with self.assertRaisesRegex(LifecycleError, "unknown event type"):
            self.engine.replay(task_id)

    def test_replay_rejects_non_string_event_id_without_type_error(self):
        task_id = self.task["task_id"]
        self.store._events[task_id][0]["event_id"] = {"id": "not-a-uuid"}
        with self.assertRaisesRegex(LifecycleError, "invalid event ID"):
            self.engine.replay(task_id)

    def test_replay_rejects_malformed_event_uuid(self):
        task_id = self.task["task_id"]
        self.store._events[task_id][0]["event_id"] = "not-a-uuid"
        with self.assertRaisesRegex(LifecycleError, "invalid event ID"):
            self.engine.replay(task_id)

    def test_replay_rejects_non_string_event_state_without_type_error(self):
        task_id = self.task["task_id"]
        self.store._events[task_id][0]["state"] = ["queued"]
        with self.assertRaisesRegex(LifecycleError, "unknown task state"):
            self.engine.replay(task_id)

    def test_replay_rejects_unknown_string_event_state(self):
        task_id = self.task["task_id"]
        self.store._events[task_id][0]["state"] = "not-a-task-state"
        with self.assertRaisesRegex(LifecycleError, "unknown task state"):
            self.engine.replay(task_id)

    def test_replay_rejects_non_list_event_collection(self):
        task_id = self.task["task_id"]
        original_events = self.store.events
        for malformed in (None, 7, {"not": "an event list"}, "events"):
            with self.subTest(value=malformed):
                self.store.events = lambda _task_id, value=malformed: value
                with self.assertRaisesRegex(LifecycleError, "event stream is not a valid list"):
                    self.engine.replay(task_id)
        self.store.events = original_events

    def test_replay_rejects_non_mapping_event_record(self):
        task_id = self.task["task_id"]
        self.store._events[task_id][0] = None
        with self.assertRaisesRegex(LifecycleError, "malformed event record"):
            self.engine.replay(task_id)

    def test_replay_rejects_non_mapping_task_snapshot(self):
        task_id = self.task["task_id"]
        self.store._tasks[task_id] = ["not", "a", "task"]
        with self.assertRaisesRegex(LifecycleError, "task snapshot"):
            self.engine.replay(task_id)

    def test_replay_rejects_unknown_task(self):
        with self.assertRaisesRegex(LifecycleError, "unknown task"):
            self.engine.replay("00000000-0000-4000-8000-000000000099")

    def test_replay_rejects_corrupt_event_identity_and_snapshot(self):
        task_id = self.task["task_id"]
        self.store._events[task_id][0]["task_id"] = "00000000-0000-4000-8000-000000000099"
        with self.assertRaisesRegex(LifecycleError, "another task"):
            self.engine.replay(task_id)

    def test_replay_rejects_snapshot_version_mismatch(self):
        task_id = self.task["task_id"]
        self.store._tasks[task_id]["version"] = 2
        with self.assertRaisesRegex(LifecycleError, "version"):
            self.engine.replay(task_id)

    def test_replay_is_contiguous_and_never_executes(self):
        self.move("planning")
        replay = self.engine.replay("00000000-0000-4000-8000-000000000001")
        self.assertEqual([e["sequence"] for e in replay["events"]], [1, 2])
        self.assertEqual(replay["task"]["state"], "planning")



    def test_emitted_tasks_and_events_conform_to_draft_schemas(self):
        self.assert_contract_valid(self.task, self.store.events(self.task["task_id"]))
        self.move("planning")
        self.move("awaiting_approval")
        self.move("running")
        self.move("verifying")
        self.move("completed", verified=True)
        self.assert_contract_valid(
            self.store.get(self.task["task_id"]),
            self.store.events(self.task["task_id"]),
        )

    def test_cancellation_events_conform_to_draft_schema(self):
        self.move("planning")
        self.move("running")
        self.engine.request_cancellation(self.task["task_id"], expected_version=3)
        self.engine.confirm_cancellation(
            self.task["task_id"], expected_version=4, operation_stopped=True
        )
        self.assert_contract_valid(
            self.store.get(self.task["task_id"]),
            self.store.events(self.task["task_id"]),
        )
        self.assertEqual(
            [event["type"] for event in self.store.events(self.task["task_id"])][-2:],
            ["task.cancel_requested", "task.cancelled"],
        )

    def test_unknown_event_type_is_rejected_without_mutation(self):
        before_task = self.store.get(self.task["task_id"])
        before_events = self.store.events(self.task["task_id"])
        with self.assertRaisesRegex(ValueError, "not defined by the task-event schema"):
            self.engine.transition(
                self.task["task_id"], "planning", expected_version=1,
                event_type="task.made_up",
            )
        self.assertEqual(self.store.get(self.task["task_id"]), before_task)
        self.assertEqual(self.store.events(self.task["task_id"]), before_events)

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

    def _race_cancellation_operation(self, cancel_action, operation_action):
        barrier = threading.Barrier(2)
        outcomes = []
        lock = threading.Lock()

        def run(label, action):
            barrier.wait(timeout=2)
            try:
                result = action()
                outcome = (label, "ok", result["state"])
            except (VersionConflict, InvalidTransition) as exc:
                outcome = (label, "conflict", type(exc).__name__)
            with lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=run, args=("cancel", cancel_action)),
            threading.Thread(target=run, args=("operation", operation_action)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=3)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sum(outcome[1] == "ok" for outcome in outcomes), 1)
        self.assertEqual(sum(outcome[1] == "conflict" for outcome in outcomes), 1)
        return outcomes

    def test_cancel_request_racing_with_state_transition_has_one_winner(self):
        self.move("planning")
        self.move("running")
        task_id = self.task["task_id"]
        outcomes = self._race_cancellation_operation(
            lambda: self.engine.request_cancellation(task_id, expected_version=3),
            lambda: self.engine.transition(task_id, "verifying", expected_version=3),
        )
        task = self.store.get(task_id)
        events = self.store.events(task_id)
        self.assertEqual(task["version"], 4)
        self.assertEqual(len(events), 4)
        self.assertIn(task["state"], {"running", "verifying"})
        self.assertIn(events[-1]["type"], {"task.cancel_requested", "task.state_changed"})
        self.assertEqual(sum(item[1] == "ok" for item in outcomes), 1)

    def test_cancel_confirmation_racing_with_progression_has_one_winner(self):
        self.move("planning")
        self.move("running")
        task_id = self.task["task_id"]
        self.engine.request_cancellation(task_id, expected_version=3)
        outcomes = self._race_cancellation_operation(
            lambda: self.engine.confirm_cancellation(
                task_id, expected_version=4, operation_stopped=True
            ),
            lambda: self.engine.transition(task_id, "verifying", expected_version=4),
        )
        task = self.store.get(task_id)
        events = self.store.events(task_id)
        self.assertEqual(task["version"], 5)
        self.assertEqual(len(events), 5)
        self.assertIn(task["state"], {"cancelled", "verifying"})
        self.assertIn(events[-1]["type"], {"task.cancelled", "task.state_changed"})
        self.assertEqual(sum(item[1] == "ok" for item in outcomes), 1)

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
            except (VersionConflict, InvalidTransition):
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


    def test_store_rejects_non_atomic_version_sequence_pair(self):
        task_id = self.task["task_id"]
        current = self.store.get(task_id)
        candidate = {**current, "state": "planning", "version": 2}
        event = self.engine._event(candidate, "task.state_changed", sequence=3)
        before_task = self.store.get(task_id)
        before_events = self.store.events(task_id)
        with self.assertRaisesRegex(ValueError, "advance together"):
            self.store.transition(task_id, 1, candidate, event, None, None)
        self.assertEqual(self.store.get(task_id), before_task)
        self.assertEqual(self.store.events(task_id), before_events)

    def test_store_rejects_cross_task_event_without_mutation(self):
        task_id = self.task["task_id"]
        current = self.store.get(task_id)
        candidate = {**current, "state": "planning", "version": 2}
        event = self.engine._event(candidate, "task.state_changed", sequence=2)
        event["task_id"] = "00000000-0000-4000-8000-000000000099"
        with self.assertRaisesRegex(ValueError, "match the transition task_id"):
            self.store.transition(task_id, 1, candidate, event, None, None)
        self.assertEqual(self.store.get(task_id), current)
        self.assertEqual(len(self.store.events(task_id)), 1)

    def test_store_create_rejects_non_mapping_records(self):
        with self.assertRaisesRegex(LifecycleError, "must be mappings"):
            self.store.create(None, {})
        with self.assertRaisesRegex(LifecycleError, "must be mappings"):
            self.store.create({}, None)
        self.assertEqual(self.store._tasks, {})
        self.assertEqual(self.store._events, {})

    def test_store_create_rejects_missing_record_identity(self):
        with self.assertRaisesRegex(LifecycleError, "require task_id and event_id"):
            self.store.create({"version": 1}, {"sequence": 1})
        self.assertEqual(self.store._tasks, {})
        self.assertEqual(self.store._events, {})

    def test_store_create_rejects_boolean_version_and_sequence(self):
        task = {"task_id": "task-1", "version": True}
        event = {"event_id": "event-1", "task_id": "task-1", "sequence": 1}
        with self.assertRaisesRegex(LifecycleError, "must be integers"):
            self.store.create(task, event)
        task["version"] = 1
        event["sequence"] = True
        with self.assertRaisesRegex(LifecycleError, "must be integers"):
            self.store.create(task, event)
        self.assertEqual(self.store._tasks, {})

    def test_store_create_rejects_non_string_identity(self):
        with self.assertRaisesRegex(LifecycleError, "non-empty strings"):
            self.store.create(
                {"task_id": 123, "version": 1},
                {"event_id": "event-1", "task_id": "123", "sequence": 1},
            )
        self.assertEqual(self.store._tasks, {})

    def test_store_transition_rejects_boolean_version_and_sequence_without_mutation(self):
        task_id = self.task["task_id"]
        before_task = self.store.get(task_id)
        before_events = self.store.events(task_id)
        candidate = {**before_task, "state": "planning", "version": 2}
        event = self.engine._event(candidate, "task.state_changed", sequence=2)
        with self.assertRaisesRegex(LifecycleError, "expected_version must be an integer"):
            self.store.transition(task_id, True, candidate, event, None, None)
        with self.assertRaisesRegex(LifecycleError, "must be integers"):
            self.store.transition(task_id, 1, {**candidate, "version": True}, event, None, None)
        with self.assertRaisesRegex(LifecycleError, "must be integers"):
            self.store.transition(task_id, 1, candidate, {**event, "sequence": True}, None, None)
        self.assertEqual(self.store.get(task_id), before_task)
        self.assertEqual(self.store.events(task_id), before_events)

    def test_store_transition_rejects_non_string_event_identity_without_mutation(self):
        task_id = self.task["task_id"]
        before_task = self.store.get(task_id)
        candidate = {**before_task, "state": "planning", "version": 2}
        event = self.engine._event(candidate, "task.state_changed", sequence=2)
        event["event_id"] = 123
        with self.assertRaisesRegex(LifecycleError, "event_id must be a non-empty string"):
            self.store.transition(task_id, 1, candidate, event, None, None)
        self.assertEqual(self.store.get(task_id), before_task)

    def test_store_transition_requires_valid_idempotency_pair_without_mutation(self):
        task_id = self.task["task_id"]
        before_task = self.store.get(task_id)
        before_events = self.store.events(task_id)
        candidate = {**before_task, "state": "planning", "version": 2}
        event = self.engine._event(candidate, "task.state_changed", sequence=2)
        invalid_pairs = (
            ("key-only", None),
            (None, "fingerprint-only"),
            ([], "fingerprint"),
            ("key", {}),
            ("", "fingerprint"),
            ("key", ""),
        )
        for key, fingerprint in invalid_pairs:
            with self.subTest(key=key, fingerprint=fingerprint):
                with self.assertRaisesRegex(LifecycleError, "must be non-empty strings supplied together"):
                    self.store.transition(
                        task_id, 1, candidate, event, key, fingerprint
                    )
        self.assertEqual(self.store.get(task_id), before_task)
        self.assertEqual(self.store.events(task_id), before_events)

    def test_idempotent_lookup_rejects_malformed_identity(self):
        for task_id, key, fingerprint in (
            (None, "key", "fingerprint"),
            ("task", [], "fingerprint"),
            ("task", "key", None),
            ("task", "", "fingerprint"),
        ):
            with self.subTest(task_id=task_id, key=key, fingerprint=fingerprint):
                with self.assertRaisesRegex(LifecycleError, "must be non-empty strings"):
                    self.store.idempotent_result(task_id, key, fingerprint)

    def test_store_transition_rejects_non_mapping_records_without_mutation(self):
        task_id = self.task["task_id"]
        before_task = self.store.get(task_id)
        before_events = self.store.events(task_id)
        with self.assertRaisesRegex(LifecycleError, "must be mappings"):
            self.store.transition(task_id, 1, None, {}, None, None)
        with self.assertRaisesRegex(LifecycleError, "must be mappings"):
            self.store.transition(task_id, 1, before_task, None, None, None)
        self.assertEqual(self.store.get(task_id), before_task)
        self.assertEqual(self.store.events(task_id), before_events)

    def test_store_transition_rejects_missing_event_identity_without_mutation(self):
        task_id = self.task["task_id"]
        before_task = self.store.get(task_id)
        before_events = self.store.events(task_id)
        candidate = {**before_task, "state": "planning", "version": 2}
        with self.assertRaisesRegex(LifecycleError, "requires event_id"):
            self.store.transition(task_id, 1, candidate, {"task_id": task_id, "sequence": 2}, None, None)
        self.assertEqual(self.store.get(task_id), before_task)
        self.assertEqual(self.store.events(task_id), before_events)

    def test_event_sequence_tracks_task_version_through_cancellation(self):
        self.move("planning")
        self.move("running")
        self.engine.request_cancellation(self.task["task_id"], expected_version=3)
        stream = self.engine.replay(self.task["task_id"])["events"]
        self.assertEqual([event["sequence"] for event in stream], [1, 2, 3, 4])
        self.assertEqual(self.store.get(self.task["task_id"])["version"], 4)


if __name__ == "__main__":
    unittest.main()
