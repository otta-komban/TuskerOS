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

## Storage adapter conformance suite

`tests/test_lifecycle_store_contract.py` is a reusable behavioral suite for
implementations of `LifecycleStore`. It checks initial version/sequence,
atomic snapshot-plus-event advancement, task identity, stale compare-and-swap,
duplicate event rejection, idempotency replay/fingerprint conflicts, and
two-writer arbitration. Every rejected write is checked for absence of partial
snapshot or event mutation.

A future adapter can reuse the same suite by importing
`LifecycleStoreContractMixin`, subclassing it with a test case, and
implementing `make_store()` to return a fresh adapter instance. The current
test module binds the mixin to `InMemoryLifecycleStore`; no persistent backend
is selected or claimed by these tests. An adapter with different setup
requirements may override `setUp()` while preserving the same contract
assertions.

## Replay integrity checks

Replay is a read-only validation operation. It rejects an unknown task, an empty
event stream, missing or duplicate event IDs, cross-task events, non-contiguous
sequence numbers, a task version that differs from the event count, or a final
event state that differs from the task snapshot. These checks detect corruption;
they do not repair state or execute any operation.

Replay also verifies that the first record is the queued `task.created` event,
event IDs are UUIDs, and each subsequent state change follows the declared
transition graph. A `task.cancel_requested` event must preserve state, while
`task.cancelled` must carry the cancelled state. This is validation only; replay
does not repair or re-execute.

## Cancellation race guarantees

The in-memory reference engine is exercised under two concurrent races: a
cancellation request versus an ordinary state transition, and executor stop
confirmation versus ordinary progression after a cancellation request. Both
compete at the same expected task version. Exactly one write may win; the
losing caller receives a version/transition conflict, and the event stream and
snapshot advance together by one. These tests validate local compare-and-swap
behavior only; a production adapter must pass the same conformance suite using
its durable transaction boundary.
