"""Reusable behavioral contract tests for LifecycleStore adapters.

A persistent adapter can reuse this suite by subclassing
LifecycleStoreContractMixin and implementing make_store(). The suite is
backend-neutral and deliberately tests observable atomicity rather than a
particular database or transaction API.
"""
from __future__ import annotations

import threading
import unittest

from adapters.lifecycle import (
    IdempotencyConflict,
    InMemoryLifecycleStore,
    LifecycleError,
    VersionConflict,
)


class LifecycleStoreContractMixin:
    """Mixin: subclasses provide make_store() returning a fresh LifecycleStore."""

    def make_store(self):
        raise NotImplementedError

    def setUp(self):
        self.store = self.make_store()
        self.task_id = "00000000-0000-4000-8000-000000000101"
        self.task = {"task_id": self.task_id, "version": 1, "state": "queued"}
        self.event = {
            "event_id": "00000000-0000-4000-8000-000000000201",
            "task_id": self.task_id,
            "sequence": 1,
            "type": "task.created",
        }
        self.store.create(self.task, self.event)

    def candidate(self, *, version=2, sequence=2, event_id="00000000-0000-4000-8000-000000000202", task_id=None):
        next_task = {"task_id": task_id or self.task_id, "version": version, "state": "planning"}
        next_event = {
            "event_id": event_id,
            "task_id": task_id or self.task_id,
            "sequence": sequence,
            "type": "task.state_changed",
        }
        return next_task, next_event

    def test_create_starts_snapshot_and_event_at_one(self):
        self.assertEqual(self.store.get(self.task_id)["version"], 1)
        self.assertEqual([e["sequence"] for e in self.store.events(self.task_id)], [1])

    def test_transition_atomically_advances_snapshot_and_event(self):
        task, event = self.candidate()
        result = self.store.transition(self.task_id, 1, task, event, None, None)
        self.assertEqual(result, task)
        self.assertEqual(self.store.get(self.task_id), task)
        self.assertEqual([e["sequence"] for e in self.store.events(self.task_id)], [1, 2])

    def test_mismatched_version_and_sequence_leave_store_unchanged(self):
        task, event = self.candidate(sequence=3)
        before_task, before_events = self.store.get(self.task_id), self.store.events(self.task_id)
        with self.assertRaises(LifecycleError):
            self.store.transition(self.task_id, 1, task, event, None, None)
        self.assertEqual(self.store.get(self.task_id), before_task)
        self.assertEqual(self.store.events(self.task_id), before_events)

    def test_cross_task_event_leaves_store_unchanged(self):
        task, event = self.candidate()
        event["task_id"] = "00000000-0000-4000-8000-000000000199"
        before_task, before_events = self.store.get(self.task_id), self.store.events(self.task_id)
        with self.assertRaises(LifecycleError):
            self.store.transition(self.task_id, 1, task, event, None, None)
        self.assertEqual(self.store.get(self.task_id), before_task)
        self.assertEqual(self.store.events(self.task_id), before_events)

    def test_stale_compare_and_swap_leaves_store_unchanged(self):
        task, event = self.candidate()
        before_task, before_events = self.store.get(self.task_id), self.store.events(self.task_id)
        with self.assertRaises(VersionConflict):
            self.store.transition(self.task_id, 9, task, event, None, None)
        self.assertEqual(self.store.get(self.task_id), before_task)
        self.assertEqual(self.store.events(self.task_id), before_events)

    def test_duplicate_event_id_leaves_store_unchanged(self):
        task, event = self.candidate(event_id=self.event["event_id"])
        before_task, before_events = self.store.get(self.task_id), self.store.events(self.task_id)
        with self.assertRaises(IdempotencyConflict):
            self.store.transition(self.task_id, 1, task, event, None, None)
        self.assertEqual(self.store.get(self.task_id), before_task)
        self.assertEqual(self.store.events(self.task_id), before_events)

    def test_idempotency_replay_and_fingerprint_conflict(self):
        task, event = self.candidate()
        first = self.store.transition(self.task_id, 1, task, event, "write-1", "fingerprint-A")
        replay = self.store.transition(self.task_id, 1, task, event, "write-1", "fingerprint-A")
        self.assertEqual(first, replay)
        with self.assertRaises(IdempotencyConflict):
            self.store.transition(self.task_id, 1, task, event, "write-1", "fingerprint-B")
        self.assertEqual(self.store.get(self.task_id), task)
        self.assertEqual([e["sequence"] for e in self.store.events(self.task_id)], [1, 2])

    def test_concurrent_compare_and_swap_has_exactly_one_winner(self):
        barrier = threading.Barrier(2)
        outcomes = []
        lock = threading.Lock()

        def writer(index):
            task, event = self.candidate(
                event_id=f"00000000-0000-4000-8000-{202 + index:012d}"
            )
            barrier.wait(timeout=2)
            try:
                self.store.transition(self.task_id, 1, task, event, None, None)
                outcome = "committed"
            except VersionConflict:
                outcome = "conflict"
            with lock:
                outcomes.append(outcome)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=3)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(outcomes), ["committed", "conflict"])
        self.assertEqual(self.store.get(self.task_id)["version"], 2)
        self.assertEqual([e["sequence"] for e in self.store.events(self.task_id)], [1, 2])


class InMemoryLifecycleStoreContractTests(LifecycleStoreContractMixin, unittest.TestCase):
    def make_store(self):
        return InMemoryLifecycleStore()


if __name__ == "__main__":
    unittest.main()
