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
the task snapshot, and persist the idempotency-key result. `InMemoryLifecycleStore`
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
