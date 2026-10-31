"""Backend-neutral, deterministic task lifecycle primitives.

This module is intentionally an internal adapter boundary: it does not select a
persistence backend or amend the draft wire schemas. A production repository
must implement the same atomic append/CAS contract as InMemoryLifecycleStore.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re
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
    def transition(self, task_id: str, expected_version: int, task: Mapping[str, Any], event: Mapping[str, Any], idempotency_key: str | None, idempotency_fingerprint: str | None) -> dict[str, Any]: ...
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
        if not isinstance(task, Mapping) or not isinstance(event, Mapping):
            raise LifecycleError("task snapshot and creation event must be mappings")
        if "task_id" not in task or "event_id" not in event:
            raise LifecycleError("task snapshot and creation event require task_id and event_id")
        task_id, event_id = task["task_id"], event["event_id"]
        if not isinstance(task_id, str) or not task_id or not isinstance(event_id, str) or not event_id:
            raise LifecycleError("task_id and event_id must be non-empty strings")
        if type(task.get("version")) is not int or type(event.get("sequence")) is not int:
            raise LifecycleError("initial task version and event sequence must be integers")
        with self._lock:
            if task_id in self._tasks:
                raise IdempotencyConflict(f"task already exists: {task_id}")
            if event.get("task_id") != task_id or event["sequence"] != 1 or task["version"] != 1:
                raise LifecycleError("initial task snapshot and event must share task_id and start at version/sequence 1")
            if event_id in self._event_ids.get(task_id, set()):
                raise IdempotencyConflict(f"duplicate event: {event_id}")
            self._tasks[task_id] = deepcopy(dict(task))
            self._events[task_id] = [deepcopy(dict(event))]
            self._event_ids[task_id] = {event_id}
            return deepcopy(self._tasks[task_id])

    def transition(self, task_id: str, expected_version: int, task: Mapping[str, Any], event: Mapping[str, Any], idempotency_key: str | None, idempotency_fingerprint: str | None) -> dict[str, Any]:
        if not isinstance(task, Mapping) or not isinstance(event, Mapping):
            raise LifecycleError("task snapshot and transition event must be mappings")
        if "event_id" not in event:
            raise LifecycleError("transition event requires event_id")
        if not isinstance(task_id, str) or not task_id:
            raise LifecycleError("transition task_id must be a non-empty string")
        if type(expected_version) is not int:
            raise LifecycleError("expected_version must be an integer")
        if not isinstance(event["event_id"], str) or not event["event_id"]:
            raise LifecycleError("event_id must be a non-empty string")
        if type(task.get("version")) is not int or type(event.get("sequence")) is not int:
            raise LifecycleError("task version and event sequence must be integers")
        if idempotency_key is not None or idempotency_fingerprint is not None:
            if (not isinstance(idempotency_key, str) or not idempotency_key
                    or not isinstance(idempotency_fingerprint, str) or not idempotency_fingerprint):
                raise LifecycleError("idempotency key and fingerprint must be non-empty strings supplied together")
        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                raise LifecycleError(f"unknown task: {task_id}")
            if idempotency_key:
                prior = self._idempotency.get((task_id, idempotency_key))
                if prior:
                    prior_fingerprint, prior_task = prior
                    if prior_fingerprint != idempotency_fingerprint:
                        raise IdempotencyConflict("idempotency key reused for a different transition")
                    return deepcopy(prior_task)
            if current["version"] != expected_version:
                raise VersionConflict(f"expected version {expected_version}, found {current['version']}")
            if task.get("task_id") != task_id or event.get("task_id") != task_id:
                raise LifecycleError("task snapshot and event must match the transition task_id")
            next_version = expected_version + 1
            if task.get("version") != next_version or event.get("sequence") != next_version:
                raise LifecycleError("task version and event sequence must advance together by exactly one")
            event_id = event["event_id"]
            if event_id in self._event_ids[task_id]:
                raise IdempotencyConflict(f"duplicate event: {event_id}")
            # Commit task snapshot, event and idempotency record as one critical section.
            self._tasks[task_id] = deepcopy(dict(task))
            self._events[task_id].append(deepcopy(dict(event)))
            self._event_ids[task_id].add(event_id)
            if idempotency_key:
                self._idempotency[(task_id, idempotency_key)] = (
                    str(idempotency_fingerprint), deepcopy(dict(task))
                )
            return deepcopy(self._tasks[task_id])

    def idempotent_result(self, task_id: str, key: str, fingerprint: str) -> dict[str, Any] | None:
        if not isinstance(task_id, str) or not task_id:
            raise LifecycleError("idempotency task_id must be a non-empty string")
        if not isinstance(key, str) or not key or not isinstance(fingerprint, str) or not fingerprint:
            raise LifecycleError("idempotency key and fingerprint must be non-empty strings")
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
        if not isinstance(task_id, str) or not isinstance(request_id, str):
            raise LifecycleError("task_id and request_id must be UUID strings")
        if origin is not None and not isinstance(origin, Mapping):
            raise LifecycleError("origin must be a mapping when supplied")
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

    @staticmethod
    def _fingerprint(payload: Mapping[str, Any]) -> str:
        try:
            return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise LifecycleError("idempotent request data must be JSON-serializable") from exc

    def transition(self, task_id: str, target: str, *, expected_version: int,
                   event_type: str = "task.state_changed", idempotency_key: str | None = None,
                   event_id: str | None = None, verified: bool = False,
                   operation_stopped: bool = False, side_effects: bool = False,
                   details: Mapping[str, Any] | None = None) -> dict[str, Any]:
        # Validate public-call shapes before dictionary/set membership or store access;
        # malformed caller values must fail as LifecycleError, never leak TypeError.
        if not isinstance(task_id, str) or not task_id:
            raise LifecycleError("task_id must be a non-empty string")
        if type(expected_version) is not int:
            raise LifecycleError("expected_version must be an integer")
        if not isinstance(target, str):
            raise LifecycleError("target state must be a string")
        if not isinstance(event_type, str):
            raise LifecycleError("event type must be a string")
        if idempotency_key is not None and (
            not isinstance(idempotency_key, str) or not idempotency_key
        ):
            raise LifecycleError("idempotency_key must be a non-empty string when supplied")
        if details is not None and not isinstance(details, Mapping):
            raise LifecycleError("transition details must be a mapping")
        if any(type(flag) is not bool for flag in (verified, operation_stopped, side_effects)):
            raise LifecycleError("transition guard flags must be booleans")
        current = self.store.get(task_id)
        if current is None:
            raise LifecycleError(f"unknown task: {task_id}")
        fingerprint = self._fingerprint({
            "operation": "transition", "event_type": event_type, "target": target,
            "verified": verified, "operation_stopped": operation_stopped,
            "side_effects": side_effects, "details": dict(details or {}),
        }) if idempotency_key else None
        # An exact replay is returned even though its original write advanced the
        # version. Check the idempotency record before rejecting stale retries.
        if idempotency_key:
            prior = self.store.idempotent_result(task_id, idempotency_key, fingerprint)
            if prior is not None:
                return prior
        if event_type not in ALLOWED_EVENT_TYPES:
            raise LifecycleError(f"event type is not defined by the task-event schema: {event_type}")
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
        # The store atomically enforces the next sequence against expected_version.
        event = self._event(next_task, event_type, event_id, sequence=expected_version + 1)
        return self.store.transition(task_id, expected_version, next_task, event, idempotency_key, fingerprint)

    def request_cancellation(self, task_id: str, *, expected_version: int, reason: str = "user_requested") -> dict[str, Any]:
        if not isinstance(task_id, str) or not task_id:
            raise LifecycleError("task_id must be a non-empty string")
        if type(expected_version) is not int:
            raise LifecycleError("expected_version must be an integer")
        if not isinstance(reason, str):
            raise LifecycleError("cancellation reason must be a string")
        if reason not in {"user_requested", "policy_requested", "shutdown", "superseded"}:
            raise LifecycleError("unsupported cancellation reason")
        key = f"cancel:{task_id}:{expected_version}"
        fingerprint = self._fingerprint({
            "operation": "request_cancellation", "reason": reason,
        })
        prior = self.store.idempotent_result(task_id, key, fingerprint)
        if prior is not None:
            return prior
        current = self.store.get(task_id)
        if current is None:
            raise LifecycleError(f"unknown task: {task_id}")
        if current["state"] in TERMINAL_STATES:
            raise InvalidTransition("cannot cancel a terminal task")
        if current["version"] != expected_version:
            raise VersionConflict("task version changed")
        next_task = deepcopy(current)
        next_task.update({"updated_at": self._now(), "version": expected_version + 1})
        event = self._event(next_task, "task.cancel_requested", sequence=expected_version + 1)
        return self.store.transition(task_id, expected_version, next_task, event, key, fingerprint)

    def confirm_cancellation(self, task_id: str, *, expected_version: int, operation_stopped: bool) -> dict[str, Any]:
        if not isinstance(task_id, str) or not task_id:
            raise LifecycleError("task_id must be a non-empty string")
        if type(expected_version) is not int:
            raise LifecycleError("expected_version must be an integer")
        if type(operation_stopped) is not bool:
            raise LifecycleError("operation_stopped must be a boolean")
        if not operation_stopped:
            raise InvalidTransition("cancellation is not terminal until the active operation is confirmed stopped")
        return self.transition(task_id, "cancelled", expected_version=expected_version,
                               event_type="task.cancelled", operation_stopped=True)

    def replay(self, task_id: str) -> dict[str, Any]:
        """Validate and return the event stream; never dispatch/re-execute operations."""
        if not isinstance(task_id, str) or not task_id:
            raise LifecycleError("task_id must be a non-empty string")
        task = self.store.get(task_id)
        if task is None:
            raise LifecycleError(f"unknown task: {task_id}")
        if not isinstance(task, Mapping):
            raise LifecycleError("task snapshot is not a valid mapping")
        if task.get("task_id") != task_id:
            raise LifecycleError("task snapshot identity does not match requested task")
        snapshot_state = task.get("state")
        if not isinstance(snapshot_state, str) or snapshot_state not in TASK_STATES:
            raise LifecycleError("task snapshot contains an unknown task state")
        events = self.store.events(task_id)
        if not isinstance(events, list):
            raise LifecycleError("event stream is not a valid list")
        if not events:
            raise LifecycleError("event stream is empty")
        if any(not isinstance(event, Mapping) for event in events):
            raise LifecycleError("event stream contains a malformed event record")
        allowed_event_fields = {
            "schema_version", "event_id", "task_id", "sequence", "occurred_at",
            "type", "state", "correlation_id", "origin", "step", "progress",
            "approval", "result", "error", "evidence_refs",
        }
        object_payload_fields = {"step", "progress", "approval", "result", "error"}
        for event in events:
            if set(event) - allowed_event_fields:
                raise LifecycleError("event stream contains unexpected event fields")
            required_fields = {
                "schema_version", "event_id", "task_id", "sequence", "occurred_at",
                "type", "state", "correlation_id", "origin",
            }
            if not required_fields.issubset(event):
                raise LifecycleError("event stream contains missing required event fields")
            if event.get("schema_version") != "0.1.0-draft":
                raise LifecycleError("event stream contains an unsupported schema version")
            occurred_at = event.get("occurred_at")
            # JSON Schema format=date-time is RFC 3339, not every spelling
            # accepted by datetime.fromisoformat (e.g. space separators or
            # compact offsets). Enforce the wire shape before calendar parsing.
            rfc3339 = (
                isinstance(occurred_at, str)
                and re.fullmatch(
                    r"\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"
                    r"(?:\\.\\d+)?(?:Z|[+-]\\d{2}:\\d{2})",
                    occurred_at,
                ) is not None
            )
            try:
                parsed_timestamp = datetime.fromisoformat(
                    occurred_at.replace("Z", "+00:00")
                ) if rfc3339 else None
            except (ValueError, OverflowError):
                parsed_timestamp = None
            if (parsed_timestamp is None or parsed_timestamp.tzinfo is None
                    or parsed_timestamp.utcoffset() is None):
                raise LifecycleError("event stream contains an invalid occurred_at value")
            if not isinstance(event.get("correlation_id"), str) or len(event["correlation_id"]) > 128:
                raise LifecycleError("event stream contains an invalid correlation_id")
            origin = event.get("origin")
            origin_kind = origin.get("kind") if isinstance(origin, Mapping) else None
            if (not isinstance(origin_kind, str)
                    or origin_kind not in {"local", "remote", "extension", "system"}
                    or set(origin) - {"kind", "display_label"}):
                raise LifecycleError("event stream contains an invalid origin")
            if ("display_label" in origin
                    and (not isinstance(origin["display_label"], str)
                         or len(origin["display_label"]) > 80)):
                raise LifecycleError("event stream contains an invalid origin")
            for identity_field in ("event_id", "task_id"):
                identity = event.get(identity_field)
                try:
                    UUID(identity)
                except (ValueError, TypeError, AttributeError) as exc:
                    raise LifecycleError(
                        f"event stream contains an invalid {identity_field}"
                    ) from exc
            sequence = event.get("sequence")
            if type(sequence) is not int or sequence < 1:
                raise LifecycleError("event stream contains an invalid sequence")
            if "evidence_refs" in event:
                refs = event["evidence_refs"]
                if (not isinstance(refs, list)
                        or any(not isinstance(ref, str) or len(ref) > 512 for ref in refs)):
                    raise LifecycleError("event stream contains invalid evidence_refs")
            for payload_field in object_payload_fields:
                if payload_field in event and event[payload_field] is not None and not isinstance(
                    event[payload_field], Mapping
                ):
                    raise LifecycleError(
                        f"event stream contains an invalid {payload_field} payload"
                    )
        if any(type(event.get("sequence")) is not int or event.get("sequence") != index
               for index, event in enumerate(events, 1)):
            raise LifecycleError("event sequence is not contiguous")
        event_ids = [event.get("event_id") for event in events]
        if any(not isinstance(event_id, str) or not event_id for event_id in event_ids):
            raise LifecycleError("event stream contains missing or invalid event IDs")
        if len(set(event_ids)) != len(event_ids):
            raise LifecycleError("event stream contains duplicate event IDs")
        for event_id in event_ids:
            try:
                UUID(event_id)
            except (ValueError, TypeError, AttributeError) as exc:
                raise LifecycleError("event stream contains an invalid event ID") from exc
        if any(event.get("task_id") != task_id for event in events):
            raise LifecycleError("event stream contains an event for another task")
        if any(not isinstance(event.get("type"), str) or event.get("type") not in ALLOWED_EVENT_TYPES
               for event in events):
            raise LifecycleError("event stream contains an unknown event type")
        first = events[0]
        if first.get("type") != "task.created" or first.get("state") != "queued":
            raise LifecycleError("event stream must begin with task.created in queued state")
        previous_state = "queued"
        for index, event in enumerate(events):
            event_type = event.get("type")
            if not isinstance(event_type, str) or event_type not in ALLOWED_EVENT_TYPES:
                raise LifecycleError("event stream contains an unknown event type")
            state = event.get("state")
            # Persisted event data is untrusted. Check the type before frozenset
            # membership so lists/dicts fail closed as LifecycleError, not TypeError.
            if not isinstance(state, str) or state not in TASK_STATES:
                raise LifecycleError("event stream contains an unknown task state")
            if index and event.get("type") == "task.created":
                raise LifecycleError("event stream contains a duplicate task.created event")
            if index and state != previous_state:
                if state not in ALLOWED_TRANSITIONS.get(previous_state, set()):
                    raise LifecycleError(
                        f"event stream contains an invalid state transition: {previous_state} -> {state}"
                    )
            if event.get("type") == "task.cancel_requested" and state != previous_state:
                raise LifecycleError("cancellation request event must not change task state")
            if event.get("type") == "task.cancelled" and state != "cancelled":
                raise LifecycleError("task.cancelled event must carry cancelled state")
            previous_state = state
        if type(task.get("version")) is not int or task.get("version") != len(events):
            raise LifecycleError("task version does not match event stream length")
        if events[-1].get("state") != task.get("state"):
            raise LifecycleError("task snapshot state does not match final event")
        return {"task": task, "events": events}
