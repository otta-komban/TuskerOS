# TUSKER-04 — Task Transition Matrix and Event Envelope Proposal

**Status:** REVIEW REQUEST — NOT APPROVED / NOT A FROZEN CONTRACT  
**Owner:** TUSKER-04  
**Assigned branch:** `04-TUSKER`  
**Scope:** Core task-level state transitions and task-event envelope only  
**Contract baseline reviewed:** Core schemas `0.1.0-draft`; `tusker-core/CONTRACTS.md` draft v0.1.0  
**Related reviews:** AEGIS-06 Issue #16; NEXUS-07 Issue #5; ORBIT-05 Issue #20

> This document is a proposal for Chief Architect and cross-agent review. It does not amend schemas, freeze event semantics, select a transport, authorize privileged execution, or claim runtime integration.

## 1. Decisions requested

The Chief Architect is asked to approve, reject, or revise:

1. The task-level state-transition matrix in §2, including cancellation and unknown-outcome handling.
2. The event-type meanings and task-state relationship in §3.
3. The event envelope invariants in §4, including sequencing, replay, duplicate delivery and reconnect behavior.
4. The ownership split and integration gates in §5.
5. The versioning/compatibility decisions in §6.

NEXUS-07 is asked to confirm the Core-to-NEXUS mapping for operation states, cancellation acknowledgement, idempotency and reconciliation. ORBIT-05 is asked to confirm how inference request/stream/cancel outcomes map into task and step events. AEGIS-06's authorization decisions in Issue #16 are recorded as security requirements, not as approval of this Core task/event contract.

## 2. Proposed task-level transition matrix

The matrix below consolidates the current Core contract prose and the existing reference engine's transition table. It is a proposed explicit matrix for review, not a newly approved semantic change.

| Current state | Proposed allowed next states | Guard / required evidence |
|---|---|---|
| `queued` | `planning`, `failed`, `cancelled` | Planning begins; failure records a stable error; cancellation is allowed only before dispatch/side effects. |
| `planning` | `awaiting_approval`, `running`, `failed`, `cancelled` | `running` requires all applicable preconditions and a fresh AEGIS ALLOW for each action before dispatch. An approval gate is not authorization. |
| `awaiting_approval` | `running`, `failed`, `cancelled` | `running` requires a fresh post-approval ALLOW bound to the exact proposal/principal/policy version/expiry. Denial, expiry, policy/identity/audit unavailability fail closed; user cancellation may cancel before dispatch. |
| `running` | `verifying`, `failed`, `cancelled`, `partially_completed` | `verifying` only after required operations have returned or been reconciled. `cancelled` only after all active operations are confirmed stopped and no remaining work can dispatch. Mixed/uncertain side effects cannot be reported as clean failure/cancellation. |
| `verifying` | `completed`, `failed`, `cancelled`, `partially_completed` | `completed` only when every required postcondition is independently verified. Cancellation requires executor stop confirmation. Partial completion preserves known side effects and unresolved limitations. |
| `completed` | none | Terminal and immutable; append-only audit/evidence references may be added without changing task state/version semantics only if the approved persistence contract permits it. |
| `failed` | none | Terminal and immutable. Preserve stable failure reason and known side effects; unresolved mutation outcome is not `failed`. |
| `cancelled` | none | Terminal only after stop acknowledgement; cancellation is not rollback. |
| `partially_completed` | none | Terminal; at least one side effect or required subtask outcome is incomplete. Any compensation is a separate authorized operation and independently verified. |

### Required invariants

- Only the Core state machine owns task-state changes.
- A transition is compare-and-swap against the caller's expected task version.
- The persisted task snapshot, event append and idempotency result are committed atomically by the production store.
- Task version and per-task event sequence advance together by exactly one for each persisted task event included in the same transaction.
- A repeated idempotency key with the same canonical semantic request returns the exact prior result; reuse with different semantics is a conflict.
- Every mutation retry re-enters AEGIS policy evaluation. No stale ALLOW or approval is reused.
- `REQUIRE_APPROVAL` is non-authorizing. DENY, unavailable/invalid identity, expired/revoked/replayed/mismatched authorization, uncertain clock, or required audit failure must yield zero mutation handler calls.
- A timeout/disconnect after possible side effects is `unknown_outcome` at the operation/step level. Reconcile against provider/system state before retry; do not invent a new task terminal state to hide uncertainty.
- Cancellation request acceptance and operation termination are separate facts. A request does not imply stopped execution.
- A task is `partially_completed` when known side effects exist but the requested final state is not achieved, unless a separately authorized and verified compensation restores the declared pre-state.

### Scope distinction: task versus step

The Plan schema has a separate step-state vocabulary: `pending`, `ready`, `running`, `awaiting_approval`, `succeeded`, `failed`, `cancelled`, `skipped`, `unknown_outcome`. These are not task states. Core owns the aggregate task state; NEXUS owns provider operation lifecycle/status and side-effect observations. Core maps operation/step outcomes into the aggregate task state only after considering dependencies, prior successful steps, verification and known side effects.

## 3. Proposed event type semantics

The current TaskEvent schema enumerates the event types below. The proposed meanings make explicit whether an event changes task state or merely records progress/evidence.

| Event type | Proposed meaning | Task state behavior |
|---|---|---|
| `task.created` | Initial task accepted with trusted origin and correlation context. | First event only; state is `queued`; sequence 1. |
| `task.plan_ready` | A validated plan is attached and ready for execution/approval routing. | Normally remains `planning`; no implicit transition. |
| `task.awaiting_approval` | AEGIS requires an eligible user decision for a specific proposal. | State is `awaiting_approval`; this is not permission to execute. |
| `task.state_changed` | Explicit aggregate task-state transition. | State must equal the new persisted task snapshot. |
| `step.started` | A step is dispatched after required preflight/authorization checks. | Task remains `running`; include step identity and safe operation reference. |
| `step.progress` | Bounded, safe progress update from an active step/provider. | Task remains `running`; progress is advisory, not proof of success. |
| `step.finished` | Provider operation has a terminal or reconciled result. | Task normally remains `running` or enters `verifying`; event must preserve operation outcome and evidence. |
| `task.verification_started` | Independent postcondition verification begins. | State is `verifying`. |
| `task.cancel_requested` | Cancellation request accepted for processing. | No state change by itself; active operation may still be running/unknown. |
| `task.finished` | Aggregate execution has reached a terminal outcome and a TaskResult is available. | State must be one of the approved terminal states; result reference/payload is required by the approved profile. |
| `task.error` | A stable task-level error was recorded. | Does not independently imply `failed`; state follows the persisted aggregate outcome, including `partially_completed` where side effects exist. |
| `task.reconciled` | An unknown operation outcome was resolved against authoritative observed state. | May retain the current state or accompany a separately validated state transition; must carry reconciliation evidence. |
| `task.cancelled` | Executor confirms all active operations stopped and no remaining work can dispatch. | State is `cancelled`; this is the terminal acknowledgement, not the request event. |

### Event rules needing explicit owner confirmation

1. Whether `task.finished` is required for every terminal state or only successful/partial result publication.
2. Whether `task.error` may accompany `failed` and `partially_completed`, and whether it is emitted before or with the terminal transition.
3. Whether `task.reconciled` may be a same-state evidence event and how its sequence/version interacts with task snapshot versions.
4. Whether progress-only events increment the same task version as state changes or use a distinct event cursor. The existing reference store couples every appended event to task version; this must be explicitly approved before durable-store implementation.
5. Whether a cancellation request while queued/planning/awaiting approval may immediately become terminal, and the exact evidence required to assert no operation was dispatched.

## 4. Proposed event envelope and delivery invariants

The existing `task-event.schema.json` requires:

- `schema_version`
- `event_id` (UUID)
- `task_id` (UUID)
- `sequence` (positive integer)
- `occurred_at` (date-time)
- `type` (current event enum)
- `state` (task-state enum)
- `correlation_id`
- `origin` (`local`, `remote`, `extension`, or `system`)

Optional payload slots currently include `step`, `progress`, `approval`, `result`, `error`, and `evidence_refs`. These are currently open object slots, not strongly typed subcontracts.

### Proposed invariants

- Event IDs are globally unique identifiers; sequence is contiguous and monotonic per task.
- `state` is the aggregate task state after the event's committed transaction, including for progress/approval/cancellation-request events that do not change state.
- Events are append-only and immutable. They are notifications/evidence, not permission to execute and not a substitute for the persisted task snapshot.
- Delivery is at-least-once tolerant: consumers deduplicate by `event_id` and sequence, and must not assume exactly-once network delivery.
- Consumers may receive delayed or out-of-order notifications. They detect gaps and fetch an authorized task snapshot plus events after a known cursor before applying later events.
- Replay validates event identity, task ownership, event type, sequence continuity, state vocabulary and allowed state history. Replay rebuilds task state/presentation only; it never re-dispatches operations or repeats side effects.
- Event payloads contain bounded safe summaries and evidence references only. No secrets, raw private file contents, credentials, hidden reasoning or unredacted sensitive tool output.
- `origin` and any principal/session identity used for authorization come from trusted transport context. Model output and caller-controlled JSON must not authoritatively set identity.
- Event payloads must not carry an authorization grant or turn approval UI acceptance into authority. AEGIS owns policy/approval/audit semantics; NEXUS/broker independently validates authorization at dispatch.

### Suggested payload profiles (review only)

- **Step event:** `step_id`, stable `operation_id`, step state, provider operation reference (if any), safe summary, bounded progress, and evidence refs.
- **Approval event:** AEGIS-owned `approval_request_id`, safe action/resource summary, expiry and correlation references. Never expose `authorization_ref` as a user-facing approval token or let a client supply it.
- **Result event:** stable TaskResult reference or typed result profile with terminal state, summary, step outcome references, verification and evidence refs.
- **Error event:** stable error code/category/retryability and safe details; no arbitrary exception text or sensitive payload.
- **Reconciliation event:** operation identity, observed provider state, evidence references and reconciliation outcome; no automatic retry instruction.

These payload profiles need typed schema definitions and owner review before use as wire contracts.

## 5. Cross-agent ownership and integration status

### AEGIS-06 — authorization and approval

Issue #16 records AEGIS confirmation that:
- all registered actions, including reads, pass policy evaluation;
- principal and origin are trusted transport/evaluation context, not proposal-body claims;
- action binding uses RFC 8785 JCS + SHA-256 with exact parsed-string preservation (no global Unicode normalization);
- only a fresh ALLOW with valid expiry and opaque authorization_ref can proceed;
- mutations require idempotency keys;
- approval requires re-evaluation and a fresh ALLOW; approval_request_id is not a broker consume credential;
- broker consume outcomes are typed, and every non-CONSUMED outcome produces no grant and zero new handler calls;
- required pre-dispatch audit failure is fail-closed.

This is AEGIS semantic guidance; transport/runtime implementation and the Core event schema remain separate approval gates.

### NEXUS-07 — tool operation lifecycle

Issue #5 records NEXUS acceptance in principle of independent IPC peer identity, fixed operation-to-handler mapping, fresh opaque authorization reference, atomic one-time consume, durable dispatch intent/audit, typed outcomes, zero handler calls on denial/mismatch/unavailable/unknown consume, and UNKNOWN plus reconciliation after possible dispatch.

Not yet frozen/accepted: concrete IPC transport/API, runtime language, authorization-context shape, durable storage primitive, and trusted peer injection implementation. NEXUS owns provider operation lifecycle and handler mapping; Core owns aggregate task/step orchestration. The public invocation authority-field discrepancy identified by AEGIS remains a shared-contract issue requiring Chief Architect approval.

### ORBIT-05 — inference lifecycle

Issue #20 requests agreement on inference request/stream/cancel/provider health/capability behavior, tool-call proposals as untrusted output, event ordering, deadlines, retries and structured errors. No ORBIT response is recorded in that issue at the time of this review. Inference-specific stream events and cancellation acknowledgements therefore remain an open dependency; Core must not invent ORBIT wire fields.

### NOVA-02 / PILOT-08

NOVA-02 consumes task state/events for presentation and user control; it is not the task executor or policy enforcement point. PILOT-08 submits requests through the same Core task path and cannot create a parallel planner/executor or privileged path. Their client reconnect/resync behavior should follow the approved event cursor/snapshot contract.

## 6. Versioning and compatibility findings

- The machine-readable Core schemas currently declare `schema_version: 0.1.0-draft`.
- `tusker-core/CONTRACTS.md` header says Draft v0.1.0, but its sample JSON objects state `1.0.0-draft`. This is a material version-label inconsistency requiring correction by the contract owner before any consumer pins a version.
- The architecture file is a proposed baseline and contains a Task sketch with fields that do not exactly match the current Task schema. The JSON Schema is the current machine-readable shape for validation; architecture examples are not interchangeable with the schema.
- The event schema's payload objects are intentionally broad. Strongly typed payload sub-schemas, compatibility policy for enum expansion, and whether unknown event types are reject-or-ignore for clients need an explicit versioning decision.
- The current role branch is 2 commits ahead / 0 behind the GitHub-reported `main` baseline SHA `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`. The role guide lists launch base SHA `5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d`; that discrepancy should be reconciled with the coordinator. No rebase, force-push, or cross-branch sync is proposed here.

## 7. Review checklist and explicit approvals

| Reviewer | Decision requested | Current evidence/status |
|---|---|---|
| Chief Architect | Approve/revise task transition matrix, terminal semantics, event meaning, sequence/version coupling, version policy. | **Pending** — no explicit approval located. |
| NEXUS-07 | Confirm task/step mapping, provider status mapping, cancellation request vs stop acknowledgement, idempotency and reconciliation. | Security invariants accepted in principle; concrete transport/API/runtime remains unapproved/unimplemented. |
| ORBIT-05 | Confirm inference cancellation, deadlines, stream ordering, terminal events and mapping into task/step events. | **Pending** — Issue #20 has no response comments. |
| AEGIS-06 | Confirm authorization/approval fields and fail-closed integration invariants. | Semantic requirements confirmed in Issue #16; does not approve Core lifecycle/event schema. |
| NOVA-02 / PILOT-08 | Confirm client projection, reconnect/resync cursor and same-task-path behavior. | Requires review after Core envelope semantics are approved. |

## 8. Implementation gate and next actions

Until Chief Architect approval is recorded:

- Do not modify shared task/event schemas or freeze transition semantics.
- Do not implement durable persistence against an unapproved event/version model.
- Do not add an invented NEXUS or ORBIT transport adapter.
- Do not enable privileged execution or treat schema tests as runtime integration evidence.

After approval:

1. Record the approved decision and exact schema/contract version.
2. Add positive and negative transition/event contract tests without weakening existing tests.
3. Implement the production store only after ATLAS/platform persistence and transaction decisions are available.
4. Integrate NEXUS/ORBIT adapters only against their accepted versioned contracts.
5. Run exact-head Core and unified CI; separately prove restart/replay, duplicate delivery, concurrent consume, cancellation races, unknown outcome reconciliation and zero-handler-call authorization failures.

## 9. Evidence references

- Core contract: `tusker-core/CONTRACTS.md`
- Task schema: `tusker-core/schemas/task.schema.json`
- Plan schema: `tusker-core/schemas/plan.schema.json`
- TaskEvent schema: `tusker-core/schemas/task-event.schema.json`
- TaskResult schema: `tusker-core/schemas/task-result.schema.json`
- Cancellation schema: `tusker-core/schemas/cancellation.schema.json`
- AEGIS review/decisions: https://github.com/otta-komban/TuskerOS/issues/16
- NEXUS review/decisions: https://github.com/otta-komban/TuskerOS/issues/5
- ORBIT review request: https://github.com/otta-komban/TuskerOS/issues/20
- Lifecycle activation/approval blocker: https://github.com/otta-komban/TuskerOS/issues/53
