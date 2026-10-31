"""Backend-neutral, deterministic task lifecycle primitives.

This module is intentionally an internal adapter boundary: it does not select a
persistence backend or amend the draft wire schemas. A production repository
must implement the same atomic append/CAS contract as InMemoryLifecycleStore.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping, Protocol
from uuid import UUID, uuid4

TASK_STATES = frozenset({
    "queued", "planning", "awaiting_approval", "running", "verifying",
    "completed", "failed", "cancelled", "partially_completed",
})
TERMINAL_STATES = frozenset({"completed", "failed", "cancelled", "partially_completed"})
# Keep emitted event names inside the currently approved draft event schema.
ALLOWED_EVENT_TYPES = frozenset(["task.created","task.plan_ready","task.awaiting_approval","task.state_changed","step.started","step.progress","step.finished","task.verification_started","task.cancel_requested","task.finished","task.error","task.reconciled","task.cancelled"])
ALLOWED_TRANSITIONS = {
    "queued": {"planning", "failed", "cancelled"},
    "planning": {"awaiting_approval", "running", "failed", "cancelled"},
    "awaiting_approval": {"running", "failed", "cancelled"},
    "running": {"verifying", "failed", "cancelled", "partially_completed"},
    "verifying": {"completed", "failed", "cancelled", "partially_completed"},
}


class LifecycleError(ValueError):
    """Base class for rejected lifecycle operations."""


class InvalidTransition(LifecycleError):
    pass


class VersionConflict(LifecycleError):
    pass


class IdempotencyConflict(LifecycleError):
    pass


class LifecycleStore(Protocol):
    def create(self, task: Mapping[str, Any], event: Mapping[str, Any]) -> dict[str, Any]: ...
    def transition(self, task_id: str, expected_version: int, task: Mapping[str, Any], event: Mapping[str, Any], idempotency_key: str | None) -> dict[str, Any]: ...
    def get(self, task_id: str) -> dict[str, Any] | None: ...
    def events(self, task_id: str) -> list[dict[str, Any]]: ...
    def idempotent_result(self, task_id: str, key: str, fingerprint: str) -> dict[str, Any] | None: ...


@dataclass
class InMemoryLifecycleStore:
    """Thread-safe reference store; replace with durable transactional storage."""
    _tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    _events: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    _event_ids: dict[str, set[str]] = field(default_factory=dict)
    _idempotency: dict[tuple[str, str], tuple[str, dict[str, Any]]] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def create(self, task: Mapping[str, Any], event: Mapping[str, Any]) -> dict[str, Any]:
        task_id, event_id = str(task["task_id"]), str(event["event_id"])
        with self._lock:
            if task_id in self._tasks:
                raise IdempotencyConflict(f"task already exists: {task_id}")
            if event_id in self._event_ids.get(task_id, set()):
                raise IdempotencyConflict(f"duplicate event: {event_id}")
            self._tasks[task_id] = deepcopy(dict(task))
            self._events[task_id] = [deepcopy(dict(event))]
            self._event_ids[task_id] = {event_id}
            return deepcopy(self._tasks[task_id])

    def transition(self, task_id: str, expected_version: int, task: Mapping[str, Any], event: Mapping[str, Any], idempotency_key: str | None) -> dict[str, Any]:
        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                raise LifecycleError(f"unknown task: {task_id}")
            if idempotency_key:
                prior = self._idempotency.get((task_id, idempotency_key))
                if prior:
                    prior_fingerprint, prior_task = prior
                    if prior_fingerprint != str(event["type"]) + ":" + str(event["state"]):
                        raise IdempotencyConflict("idempotency key reused for a different transition")
                    return deepcopy(prior_task)
            if current["version"] != expected_version:
                raise VersionConflict(f"expected version {expected_version}, found {current['version']}")
            event_id = str(event["event_id"])
            if event_id in self._event_ids[task_id]:
                raise IdempotencyConflict(f"duplicate event: {event_id}")
            # Commit task snapshot, event and idempotency record as one critical section.
            self._tasks[task_id] = deepcopy(dict(task))
            self._events[task_id].append(deepcopy(dict(event)))
            self._event_ids[task_id].add(event_id)
            if idempotency_key:
                self._idempotency[(task_id, idempotency_key)] = (
                    str(event["type"]) + ":" + str(event["state"]), deepcopy(dict(task))
                )
            return deepcopy(self._tasks[task_id])

    def idempotent_result(self, task_id: str, key: str, fingerprint: str) -> dict[str, Any] | None:
        with self._lock:
            prior = self._idempotency.get((task_id, key))
            if prior is None:
                return None
            if prior[0] != fingerprint:
                raise IdempotencyConflict("idempotency key reused for a different transition")
            return deepcopy(prior[1])

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return deepcopy(task) if task is not None else None

    def events(self, task_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._events.get(task_id, []))


class LifecycleEngine:
    """Validates transitions and delegates atomic persistence to a store."""
    def __init__(self, store: LifecycleStore):
        self.store = store

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _event(task: Mapping[str, Any], event_type: str, event_id: str | None = None, **extra: Any) -> dict[str, Any]:
        sequence = extra.pop("sequence", None)
        event = {
            "schema_version": "0.1.0-draft", "event_id": event_id or str(uuid4()),
            "task_id": task["task_id"], "sequence": sequence or 1,
            "occurred_at": LifecycleEngine._now(), "type": event_type,
            "state": task["state"], "correlation_id": task.get("request_id", task["task_id"]),
            "origin": deepcopy(task.get("origin", {"kind": "local"})),
        }
        event.update(extra)
        return event

    def create_task(self, task_id: str, request_id: str, origin: Mapping[str, Any] | None = None) -> dict[str, Any]:
        try:
            UUID(task_id)
            UUID(request_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise LifecycleError("task_id and request_id must be UUIDs") from exc
        now = self._now()
        task = {
            "schema_version": "0.1.0-draft", "task_id": task_id, "request_id": request_id,
            "created_at": now, "updated_at": now, "state": "queued",
            "origin": deepcopy(dict(origin or {"kind": "local"})), "version": 1,
        }
        return self.store.create(task, self._event(task, "task.created"))

    def transition(self, task_id: str, target: str, *, expected_version: int,
                   event_type: str = "task.state_changed", idempotency_key: str | None = None,
                   event_id: str | None = None, verified: bool = False,
                   operation_stopped: bool = False, side_effects: bool = False,
                   details: Mapping[str, Any] | None = None) -> dict[str, Any]:
        current = self.store.get(task_id)
        if current is None:
            raise LifecycleError(f"unknown task: {task_id}")
        if event_type not in ALLOWED_EVENT_TYPES:
            raise LifecycleError(f"event type is not defined by the task-event schema: {event_type}")
        fingerprint = event_type + ":" + target
        # An exact replay is returned even though its original write advanced the
        # version. Check the idempotency record before rejecting stale retries.
        if idempotency_key:
            prior = self.store.idempotent_result(task_id, idempotency_key, fingerprint)
            if prior is not None:
                return prior
        # Reject stale callers before validating against a newer state snapshot.
        # The store repeats this check atomically to close the read/write race.
        if current["version"] != expected_version:
            raise VersionConflict(f"expected version {expected_version}, found {current['version']}")
        source = current["state"]
        if event_id is not None:
            try:
                UUID(event_id)
            except (ValueError, TypeError, AttributeError) as exc:
                raise LifecycleError("event_id must be a UUID") from exc
        if target not in TASK_STATES:
            raise InvalidTransition(f"unknown target state: {target}")
        if source in TERMINAL_STATES:
            raise InvalidTransition(f"terminal state is immutable: {source}")
        if target not in ALLOWED_TRANSITIONS.get(source, set()):
            raise InvalidTransition(f"transition not allowed: {source} -> {target}")
        if target == "completed" and (source != "verifying" or not verified):
            raise InvalidTransition("completed requires verifying state and verified postconditions")
        if target == "cancelled" and not operation_stopped:
            raise InvalidTransition("cancellation requires executor confirmation that the operation stopped")
        if target == "partially_completed" and not side_effects:
            raise InvalidTransition("partial completion requires known side effects")
        if target == "failed" and details and details.get("outcome_unknown"):
            raise InvalidTransition("unknown mutation outcome must be reconciled, not failed")
        next_task = deepcopy(current)
        next_task.update({"state": target, "updated_at": self._now(), "version": expected_version + 1})
        existing_events = self.store.events(task_id)
        event = self._event(next_task, event_type, event_id, sequence=len(existing_events) + 1)
        return self.store.transition(task_id, expected_version, next_task, event, idempotency_key)

    def request_cancellation(self, task_id: str, *, expected_version: int, reason: str = "user_requested") -> dict[str, Any]:
        if reason not in {"user_requested", "policy_requested", "shutdown", "superseded"}:
            raise LifecycleError("unsupported cancellation reason")
        current = self.store.get(task_id)
        if current is None:
            raise LifecycleError(f"unknown task: {task_id}")
        if current["state"] in TERMINAL_STATES:
            raise InvalidTransition("cannot cancel a terminal task")
        if current["version"] != expected_version:
            raise VersionConflict("task version changed")
        next_task = deepcopy(current)
        next_task.update({"updated_at": self._now(), "version": expected_version + 1})
        events = self.store.events(task_id)
        event = self._event(next_task, "task.cancel_requested", sequence=len(events) + 1)
        return self.store.transition(task_id, expected_version, next_task, event, f"cancel:{task_id}:{expected_version}")

    def confirm_cancellation(self, task_id: str, *, expected_version: int, operation_stopped: bool) -> dict[str, Any]:
        if not operation_stopped:
            raise InvalidTransition("cancellation is not terminal until the active operation is confirmed stopped")
        return self.transition(task_id, "cancelled", expected_version=expected_version,
                               event_type="task.cancelled", operation_stopped=True)

    def replay(self, task_id: str) -> dict[str, Any]:
        """Return the deterministic event stream; never dispatch/re-execute operations."""
        events = self.store.events(task_id)
        if any(event.get("sequence") != index for index, event in enumerate(events, 1)):
            raise LifecycleError("event sequence is not contiguous")
        if len({event.get("event_id") for event in events}) != len(events):
            raise LifecycleError("event stream contains duplicate event IDs")
        return {"task": self.store.get(task_id), "events": events}
