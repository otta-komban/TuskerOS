# Provisional lifecycle engine

`adapters/lifecycle.py` provides the first executable Core lifecycle boundary. It
is deliberately backend-neutral and does not modify the draft wire schemas or
choose SQLite/WAL while the ATLAS-01 storage decision is pending.

## Use

```python
from adapters.lifecycle import InMemoryLifecycleStore, LifecycleEngine

engine = LifecycleEngine(InMemoryLifecycleStore())
task = engine.create_task("task-uuid", "request-uuid", {"kind": "local"})
task = engine.transition("task-uuid", "planning", expected_version=task["version"])
task = engine.transition("task-uuid", "running", expected_version=task["version"])
task = engine.transition("task-uuid", "verifying", expected_version=task["version"])
task = engine.transition(
    "task-uuid", "completed", expected_version=task["version"], verified=True
)
```

## Repository contract

A production implementation of `LifecycleStore` must atomically compare the
expected task version, append exactly one monotonically sequenced event, update
the task snapshot, and persist the idempotency-key result. The initial snapshot
and creation event both start at 1. Every accepted transition must atomically
advance both task `version` and event `sequence` to
`expected_version + 1`; a store must reject mismatched task IDs, versions or
sequences without changing any state. The engine derives the next sequence from
the expected version rather than a separate event-list read, and the store is
the final authority enforcing the invariant under concurrent writes.
`InMemoryLifecycleStore`
provides a thread-safe reference implementation for tests only; it is not durable
across process restart.

## Safety properties in this milestone

- Invalid transitions and all writes to terminal task states are rejected.
- `completed` requires the verifier to assert `verified=True`.
- Cancellation request is a nonterminal event; `cancelled` requires explicit
  executor confirmation that the active operation stopped.
- An unknown mutation outcome cannot be converted directly to `failed`.
- Partial completion requires known side effects.
- Expected-version checks reject stale writers; idempotency keys return the
  original result on replay and reject reuse for a different transition.
- Replay validates event IDs and contiguous sequence numbers and never dispatches
  or repeats an external operation.

This is an internal provisional implementation. Durable crash recovery, schema
consumer agreement, AEGIS authorization dispatch gates, NEXUS execution wiring,
and persistent event delivery remain separate integration work.

## Idempotency request identity

Idempotency keys are scoped to a task and paired with a canonical JSON fingerprint of
the operation's semantic inputs. For state transitions this includes the event type,
target state, verification and cancellation-stop flags, side-effect declaration, and
details payload. Cancellation requests include their reason. Repeating the same key
with the same fingerprint returns the original result; reusing it with different
semantic inputs raises an idempotency conflict. Event IDs are intentionally excluded
from the fingerprint so a transport retry can replay the original operation.

A durable store adapter must atomically persist the fingerprint with the task snapshot
and event, and must check an existing key before checking the expected task version.
