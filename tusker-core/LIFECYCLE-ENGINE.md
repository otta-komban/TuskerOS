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

Replay validates the event envelope against the provisional JSON Schema: required and allowed top-level fields, UUID identities, positive integer sequence values, bounded evidence references, and object-or-null payload slots. Invalid records fail closed before the stream is returned. These checks are schema conformance only and do not approve the draft contract.

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

## Replay event vocabulary

Replay rejects any event whose `type` is absent or outside the Core draft event enum, matching the write-side event-type guard. This is fail-closed validation, not a change to the shared draft schema.

Replay also validates the draft event envelope's schema version, timestamp, bounded correlation identifier, and origin kind against the existing provisional event schema. Timestamps must parse as ISO date-times with an explicit timezone; invalid calendar/time values and timezone-naive values fail with `LifecycleError`. Malformed persisted envelope values fail closed; this does not define new event meanings or alter the schema.


## Replay malformed-value handling

Replay validates the runtime types of event IDs and event types before set membership, duplicate detection, or UUID parsing. Non-string values are rejected as lifecycle corruption with a stable `LifecycleError`, rather than leaking Python `TypeError` from malformed/untrusted persisted data.

Replay applies the same type-before-enum check to persisted task-state values. A non-string state (including a list or object) and an unknown string state are rejected as lifecycle corruption with `LifecycleError`; malformed persisted values must not escape as interpreter-level type errors.

Replay validates the outer shape of the persisted snapshot and event stream before reading fields. Non-mapping task snapshots and non-mapping event records are rejected with `LifecycleError`, not leaked attribute/type errors.

The in-memory store also validates write-boundary record shapes before field
access. Creation requires mapping-shaped task/event records with task and event
identity fields; transitions require mapping-shaped records and an event ID.
Malformed inputs are rejected with `LifecycleError` before any snapshot, event,
or idempotency state is changed. This protects the adapter boundary from
interpreter-level `TypeError`/`KeyError` leaks; it does not expand the wire
schema or define new lifecycle semantics.

Replay also verifies that the event collection returned by a store adapter is
a list before iterating it. A malformed adapter response (for example, a
scalar, mapping, or string) is rejected with `LifecycleError` rather than
leaking an iteration-related interpreter exception.


## Store boundary type validation

The in-memory store rejects non-string or empty task/event identifiers and requires exact integer types for task versions, event sequences, and expected versions. In particular, boolean values are not accepted as counters even though Python considers `True == 1`. These checks run before any write, and regression tests assert that rejected records leave the task snapshot and event stream unchanged. This is input-shape hardening only; it does not approve or alter the draft lifecycle transition/event contract.


## Idempotency boundary validation

Store transitions require idempotency keys and fingerprints to be supplied together as non-empty strings; malformed, empty, or one-sided values are rejected before mutation. Direct idempotency lookups likewise validate task, key, and fingerprint identities before dictionary access. This prevents malformed adapter callers from triggering unhashable-key interpreter errors or silently bypassing idempotency handling.


## Engine transition argument validation

The public transition method validates task identity, expected-version type, target
state and event-type shapes, optional idempotency-key shape, details mapping, and
boolean guard flags before store access or enum/set membership. Invalid caller
values fail with `LifecycleError` and leave the snapshot/event stream unchanged.
This is defensive API-boundary validation; it does not add fields or change the
provisional lifecycle contract.


## Cancellation API argument validation

Cancellation requests validate task identity, expected-version type, and the
reason's string type before idempotency lookup or store access. Stop confirmation
validates task identity, expected-version type, and requires an actual boolean
stop acknowledgement. Malformed values fail with `LifecycleError` rather than
leaking dictionary/set type errors or accepting truthy non-boolean values.
Rejected calls do not mutate the task snapshot or event stream.


The public creation API rejects a supplied `origin` that is not a mapping before attempting conversion or persistence. Replay rejects empty or non-string task identifiers before calling the store. Regression tests cover malformed origins and verify malformed replay identifiers do not reach the store. These checks validate input shape only; they do not establish a canonical origin schema or change lifecycle semantics.


Replay now validates the returned task snapshot before reading its event stream: the snapshot must be a mapping, its `task_id` must match the requested identifier, and its state must be a known task state. Regression tests cover mismatched identity and malformed state, including that invalid snapshots are rejected before event retrieval. Replay also requires the snapshot `version` to be an exact integer equal to the event count; boolean, floating-point, and string values are rejected as version corruption.


Replay origin validation follows the existing provisional event schema: `origin` may contain only the required `kind` and optional string `display_label` (maximum 80 characters). Unknown origin properties and malformed or oversized labels are rejected as persisted-event corruption. This is schema-conformance validation only; it does not change the event schema or origin semantics.
