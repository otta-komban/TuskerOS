# TUSKER-04 Core Contracts

**Owner:** TUSKER-04  
**Status:** Draft v0.1.0 — for cross-agent review; not a frozen shared API  
**Branch:** `04-tusker-core`  
**Related owners:** ORBIT-05 (inference), AEGIS-06 (authorization), NEXUS-07 (tools), NOVA-02 (desktop), PILOT-08 (remote)

## 1. Contract rules

- All external payloads are versioned, bounded, typed and validated at the receiving boundary.
- UUIDs identify task/step/event/proposal/request records; timestamps are UTC RFC3339.
- Unknown optional fields may be ignored; unsupported major versions and missing required fields are rejected.
- Model output, files, web pages, tool output, remote payloads and extension metadata are untrusted data.
- A plan is a proposal, not authority. Core cannot assign its own permission/risk result.
- No arbitrary shell command is a public tool API.
- Every mutating operation is authorized by AEGIS-06 immediately before dispatch and independently validated by NEXUS-07/broker.
- A timeout or lost connection does not prove a mutation failed. Resolve outcome before retry.
- Task/event APIs expose safe summaries and evidence references, not hidden reasoning, secrets, or raw private content.

## 2. Ownership boundaries

| Contract | Owner |
|---|---|
| Session, conversation, task, plan, step and task-event state | TUSKER-04 |
| Inference request/stream/cancel/provider health/capabilities | ORBIT-05 |
| Action proposal, policy decision, approval, privileged broker and audit | AEGIS-06 |
| Tool registry, per-tool schemas, operation lifecycle and side effects | NEXUS-07 |
| Task presentation, notification, user control surfaces | NOVA-02 |
| Remote authentication/device identity and transport adapter | PILOT-08 |

PILOT-08 submits a user request to Core; it does not create an alternate planner or executor. NOVA-02 presents Core state; it does not own task execution. ORBIT-05 returns model output; it does not call tools or authorize actions.

## 3. Task state machine

Canonical states:

- `queued`
- `planning`
- `awaiting_approval`
- `running`
- `verifying`
- `completed`
- `failed`
- `cancelled`
- `partially_completed`

Typical successful path:

`queued -> planning -> running -> verifying -> completed`

Approval path:

`planning -> awaiting_approval -> running` (only after fresh AEGIS authorization)

Alternate outcomes:
- `planning -> failed` for invalid/unsupported/ambiguous request that cannot be clarified.
- `awaiting_approval -> failed` for denial, expiry, or policy unavailability; record precise reason.
- `running -> cancelled` only after active tool cancellation/termination is confirmed and remaining work is stopped.
- `running|verifying -> partially_completed` when some side effects occurred and full requested outcome is not achieved.
- Any nonterminal state may enter `failed` for unrecoverable internal/persistence errors, preserving known side effects.
- A timed-out mutation with unresolved outcome remains in a recoverable/reconciling state internally; it MUST NOT be represented as safely failed or cancelled. Public state may remain `running` with a typed `outcome_unknown` status until reconciliation.

Terminal states: `completed`, `failed`, `cancelled`, `partially_completed`. Terminal tasks are immutable except for appended audit/evidence events or explicit administrative retention operations.

### Transition invariants

1. Only the Core state machine can change task state; transitions are validated and persisted transactionally.
2. No mutating step enters dispatch until AEGIS returns a valid, unexpired ALLOW for the exact action digest and trusted principal.
3. REQUIRE_APPROVAL is not authorization. A denial, expiry, missing identity, invalid decision, policy outage or required audit failure prevents dispatch.
4. Every retry of a mutation re-enters policy evaluation. Never replay stale approval or authorization.
5. Cancellation prevents future steps and requests supported interruption. Cancellation is not rollback.
6. A non-idempotent operation is never blindly retried after timeout or restart. Reconcile actual state first.
7. `completed` requires all required postconditions to be independently verified.
8. Mixed success/failure is `partially_completed` unless separately authorized and verified compensation restores the declared pre-state.
9. Pause/resume is exposed only when a task/provider has a safe checkpoint. It is not promised for arbitrary system operations.

## 4. Core data contracts (draft)

All objects include `schema_version: "1.0.0-draft"` until a version is agreed by consumers.

### Task

```json
{
  "schema_version": "1.0.0-draft",
  "task_id": "uuid",
  "session_id": "uuid",
  "request_id": "uuid",
  "created_at": "RFC3339 UTC",
  "updated_at": "RFC3339 UTC",
  "state": "queued",
  "origin": {"kind": "local", "principal_ref": "opaque trusted reference"},
  "user_request": "bounded user-authored text",
  "intent": {"category": "files", "summary": "safe normalized summary"},
  "plan_id": null,
  "current_step_id": null,
  "result_ref": null,
  "error": null,
  "version": 1
}
```

The trusted origin/principal is derived from the authenticated caller adapter. It is never accepted from model output or an untrusted request body.

### Plan and Step

```json
{
  "schema_version": "1.0.0-draft",
  "plan_id": "uuid",
  "task_id": "uuid",
  "created_at": "RFC3339 UTC",
  "steps": [{
    "step_id": "uuid",
    "sequence": 1,
    "operation_id": "registered.operation.id",
    "input": {},
    "depends_on": [],
    "preconditions": [],
    "expected_postconditions": [],
    "risk_hint": "untrusted advisory only",
    "timeout_ms": 10000,
    "retry_policy": {"max_attempts": 1, "requires_reconcile": true},
    "idempotency_key": "opaque-key",
    "state": "pending"
  }],
  "requires_confirmation": true
}
```

Core validates the plan against the NEXUS tool registry. `risk_hint` is never used as an authorization decision. The policy engine derives risk from the registered operation, canonical arguments and resources.

### AEGIS action proposal handoff

Core constructs the typed proposal using the AEGIS-owned field names:

```json
{
  "schema_version": "0.1.0-draft",
  "action_id": "registered.operation.id",
  "proposal_id": "uuid",
  "task_id": "uuid",
  "step_id": "uuid",
  "origin": "local",
  "arguments": {},
  "resources": [],
  "idempotency_key": "required-for-mutation",
  "requested_at": "RFC3339 UTC"
}
```

The trusted identity adapter supplies principal and origin context outside untrusted request data. Exact serialization, canonical digest, principal shape and decision transport remain subject to AEGIS-06 approval.

Expected AEGIS decision values: `DENY`, `REQUIRE_APPROVAL`, `ALLOW`. Only a fresh ALLOW bound to exact digest, principal, policy version and expiry permits dispatch. Core records `decision_id`, `policy_version`, `action_digest`, expiry and audit reference; NEXUS/broker independently validates authorization.

### Tool invocation and result (NEXUS adapter boundary)

Core-to-NEXUS adapter maps a step to the NEXUS operation contract. Required correlation data:

- `request_id`: unique tool invocation ID.
- `task_id`, `step_id`: Core ownership references.
- `correlation_id`: end-to-end trace ID.
- `idempotency_key`: stable for the logical mutation attempt group, per NEXUS contract.
- `operation_id`: provider operation identity, when returned.

Core expects a typed result containing status, structured result, observed side effects, timing, postcondition status, evidence references and stable error. The NEXUS draft statuses `succeeded`, `rejected`, `needs_approval`, `running`, `cancelled`, `failed`, `unknown_outcome` are compatible in principle. Core should not treat `needs_approval` from NEXUS as a substitute for its AEGIS preflight.

### Task event

```json
{
  "schema_version": "1.0.0-draft",
  "event_id": "uuid",
  "task_id": "uuid",
  "sequence": 12,
  "occurred_at": "RFC3339 UTC",
  "type": "task.state_changed",
  "state": "running",
  "step_id": "uuid-or-null",
  "progress": {"completed": 1, "total": 3, "safe_summary": "Preparing selected files"},
  "origin": {"kind": "local", "display_label": "This device"},
  "approval_ref": null,
  "result_ref": null,
  "error": null,
  "evidence_refs": [],
  "correlation_id": "opaque-id"
}
```

Event IDs are unique and sequence is monotonic per task. Events are append-only notifications, not the source of truth. Consumers tolerate duplicate, delayed and out-of-order delivery. On reconnect or sequence gap, clients fetch an authorized task snapshot and resume from a known cursor.

Suggested event types: `task.created`, `task.plan_ready`, `task.awaiting_approval`, `task.state_changed`, `step.started`, `step.progress`, `step.finished`, `task.verification_started`, `task.cancel_requested`, `task.finished`, `task.error`.

### Approval presentation reference

Core forwards an AEGIS-owned immutable approval reference containing:
- approval request ID and expiry;
- trusted operation display name and exact target/resource summary;
- risk class and meaningful impact/reversibility;
- requesting principal/device context safe for display;
- action digest reference and correlation IDs.

NOVA-02 displays the approval request and captures a user decision. AEGIS validates/consumes the decision and issues authorization. UI acceptance alone never authorizes execution.

### Task result and error

```json
{
  "schema_version": "1.0.0-draft",
  "task_id": "uuid",
  "final_state": "partially_completed",
  "summary": "Safe concise result",
  "completed_steps": [],
  "failed_steps": [],
  "skipped_steps": [],
  "verification": [],
  "evidence_refs": [],
  "limitations": []
}
```

Errors use stable `code`, `category`, `retryable`, `correlation_id` and safe details. Initial categories: `invalid_request`, `intent_uncertain`, `model_unavailable`, `tool_unavailable`, `permission_denied`, `approval_expired`, `precondition_failed`, `timeout`, `cancelled`, `verification_failed`, `persistence_failure`, `partial_execution`, `outcome_unknown`, `internal_error`.

### Cancellation

```json
{
  "schema_version": "1.0.0-draft",
  "task_id": "uuid",
  "requested_by": "trusted principal reference",
  "reason": "user_requested",
  "requested_at": "RFC3339 UTC"
}
```

Cancellation response reports request acceptance, observed task state, active step, tool acknowledgements, possible side effects and whether retry is safe. Core reports `cancelled` only after all active work is confirmed stopped; otherwise it reports still-running/unknown/partial as appropriate.

## 5. Conversation, memory and privacy

- Conversation history is local by default and separated from task execution records.
- Store only the minimum context needed for the current request; retrieval is scoped to the active user/session and declared retention.
- User-provided content and retrieved documents are untrusted data, not system instructions.
- Do not persist hidden reasoning. Store user messages, safe assistant summaries, plan/task metadata, tool evidence references and user-visible outcomes according to retention settings.
- Provide explicit controls for history retention, export and deletion. Deletion scope must include derived task/context records as documented; audit records required for security may follow a separate AEGIS retention policy.
- Credentials, tokens, private keys, secret environment values and raw sensitive tool output must never enter normal conversation/task logs.
- Offline mode must not silently fall back to cloud inference. A provider change requires explicit product/user policy and clear UI disclosure.

## 6. Recovery and persistence invariants

- Persist each accepted state transition and its event in one transaction.
- Event replay rebuilds presentation/state; it never replays side effects.
- On restart, any step marked running is reconciled against provider/system state before resuming.
- A missing provider, policy service or persistence backend blocks new mutations; read-only diagnostics may remain available where safe.
- Duplicate submissions are deduplicated by authenticated principal + request idempotency key. Same key with materially different request payload is a conflict.
- Concurrent tasks require resource-conflict detection or serialization for overlapping mutations; the model cannot resolve races by assertion.

## 7. Open decisions

1. ORBIT-05: exact inference request/stream/cancel/capability and provider error schemas.
2. AEGIS-06: principal provenance, canonical digest, decision transport, approval consumption, audit behavior and read-only policy.
3. NEXUS-07: exact invocation/result field names, idempotency scope, progress/cancellation and postcondition evidence.
4. NOVA-02: desktop task snapshot/event consumption and approval surface contract.
5. PILOT-08: remote identity propagation, idempotency, safe projections and approval routing.
6. ATLAS-01: IPC transport, systemd lifecycle, runtime paths, user/session boundaries and packaging conventions.
7. Persistence choice (SQLite proposed) and retention/encryption requirements require platform/security decision.

## 8. Contract status

### Adapter compatibility review (2026-10-31)



**NEXUS-07 tool boundary:** Core consumes the NEXUS tool descriptor as the source of operation name, input/output schema references, bounded timeout, idempotency support/scope, cancellation guarantee, declared side effects, preconditions and postconditions. Descriptor risk/privilege metadata is descriptive policy input, never permission. Invocation uses request_id plus task_id, step_id and correlation_id; caller component/instance are descriptive only. The authorization_context is opaque trusted context and must be independently checked by NEXUS/broker. Core preserves arbitrary JSON result values, maps postcondition/cancellation/evidence fields, and reconciles unknown_outcome before retry. NEXUS invocation deadline_ms currently caps at 300000; Core must enforce the tighter of its local ceiling and descriptor/provider ceiling. Core operation IDs must match the NEXUS dotted tool-name pattern.



**AEGIS-06 policy boundary:** Core submits the AEGIS-owned action proposal shape and supplies authenticated principal/origin as trusted transport context, not proposal fields. AEGIS evaluates all registered actions, including reads. Canonical binding uses RFC 8785 JCS plus SHA-256. Core accepts only a decision whose proposal, action digest, principal binding, policy version and expiry match the exact pending step; ALLOW also requires a non-empty opaque authorization_ref. DENY, REQUIRE_APPROVAL, missing/malformed decision, policy outage, expired authorization, binding mismatch or required audit failure produce zero executor calls. The AEGIS schema leaves idempotency_key optional structurally; Core's mutation invariant requires a non-empty key regardless, pending owner confirmation.



**NOVA-02 event consumer:** NOVA's draft expects a unique event_id, monotonic per-task sequence, UTC occurred_at, authoritative state, safe origin/step/progress summaries and correlation_id. It deduplicates events and fetches an authorized snapshot on gaps/reconnect. Dismiss is UI-only; cancellation is not rollback; pause/resume is exposed only with explicit safe-checkpoint capability. The Core event schema is a producer draft and must be reconciled field-for-field with NOVA before transport implementation. In particular, schema_version and event type vocabulary are not yet agreed.



**ORBIT-05 inference boundary:** ORBIT's provider proposal defines model-agnostic bounded typed messages, ordered inference events, exactly one terminal event, cooperative cancellation and provider health/capabilities. Tool-call deltas are untrusted proposals; ORBIT never executes tools or authorizes actions. Core owns planning, task state and all policy/execution routing. Provider disconnection before a terminal event is not successful completion.



**ATLAS-01 platform boundary:** Tusker services remain optional and removable, never boot/login dependencies. Session bus is the provisional boundary for per-user desktop integration; system bus is for system-wide capability APIs owned by NEXUS/AEGIS, not a reason to expose Core's task engine as a privileged system service. Exact Core transport, service unit, runtime paths and persistence choice remain undecided; no Core service identity or D-Bus name is claimed.



**Version and identifier compatibility:** Core's UUID task/step IDs are a stricter producer choice and fit the bounded opaque-string fields accepted by NEXUS/AEGIS. Consumers must treat IDs as opaque. Core's schema version 0.1.0-draft is not interchangeable with NEXUS 1.0, AEGIS 0.1.0 or NOVA draft v0.1; adapters must validate each component's own schema version and perform explicit mapping. No shared version has been approved.


### Cross-agent reconciliation snapshot (2026-10-31)

- **NEXUS-07:** accepted Core ownership of Task/Plan/Step/TaskEvent and agreed to carry task/step/correlation identifiers, authorization-context reference, explicit cancellation request/operation state, evidence references and idempotency scope in its provisional tool contracts. Caller component fields remain descriptive, not authenticated identity. Exact AEGIS principal/decision shape remains external.
- **AEGIS-06:** confirmed the ten security integration invariants as its cross-agent baseline. Draft policy uses RFC 8785 JCS plus SHA-256 for action/resource/principal/policy binding; all registered operations, including reads, pass policy evaluation; DENY and REQUIRE_APPROVAL produce zero executor calls. Authorization transport/signing/one-time broker consumption still requires NEXUS coordination.
- **ORBIT-05:** published `tusker-ai/docs/PROVIDER-CONTRACT.md` on `05-ai-runtime`. Its proposal defines separate model-catalog and inference-provider ports, bounded typed messages, ordered stream events with one terminal event, cooperative cancellation and provider error taxonomy. ORBIT explicitly leaves tool execution and authorization to Core/AEGIS. Cross-agent approval remains pending.
- **NOVA-02:** published `desktop/contracts/task-events-v0.1.md`. Core remains authoritative for task state/events; desktop deduplicates event IDs, tracks per-task sequence, requests snapshots on gaps/reconnect, and treats dismiss as presentation-only. Approval UI does not authorize. No backend integration exists yet.
- **ATLAS-01:** base contract confirms Tusker services optional, removable and not boot/login dependencies; use session bus for per-user desktop integration and system bus for system capability APIs, subject to owner security review. No explicit Core transport/service/persistence decision was found in the inspected proposal; implementation stack remains open.
- **PILOT-08:** remote adapter proposal aligns with Core ownership; remote requests use same task lifecycle, remote approval remains policy-gated, and remote clients do not directly invoke tools. No explicit owner acknowledgement of Core's issue #14 response was found in the comments inspected.

### Provisional Core schema artifacts

Draft JSON Schema 2020-12 artifacts are in `tusker-core/schemas/`: `task.schema.json`, `plan.schema.json`, `task-event.schema.json`, `task-result.schema.json`, and `cancellation.schema.json`. They are Core-owned working drafts, not frozen cross-agent APIs. The `schemas.tuskeros.invalid` IDs are placeholders, not claimed project-controlled namespace identifiers. Fixtures, validator tests, transport bindings and migrations are not yet implemented.


This document is a Core-owned integration proposal. It is not a shared contract approval. Do not implement against unresolved field names as if frozen. Update version and contract tests after owners acknowledge the exact schemas.


### Desktop event reconciliation follow-up (2026-10-31)

A field-by-field comparison of Core's provisional `task-event.schema.json` with NOVA-02's `desktop/contracts/task-events-v0.1.md` identified two producer/consumer mismatches. The Core event enum now includes `task.cancelled` as the terminal cancellation event (distinct from `task.cancel_requested`), and `origin` is required with a required `kind` so the desktop can render trusted origin metadata. The existing event payload slots remain `step`, `progress`, `approval`, `result` and `error`; their detailed sub-schemas and exact cross-agent version remain open. Follow-up posted on issue #9 (comment 6531440523) requesting NOVA confirmation of those slots and any additional required fields. This is a producer-draft alignment, not shared approval or transport implementation.

ORBIT-05 follow-up: reviewed the provider proposal and requested a normative v0.1 inference request/event/error schema with exact bounds and cancellation/disconnection semantics (issue #25 comment 6531437037). ATLAS-01 follow-up: requested a concrete Core transport, peer-identity, systemd user-service, XDG path and SQLite/WAL recommendation (issue #27 comment 6531438627). Both decisions remain pending.


### NOVA-02 desktop event contract acceptance (2026-10-31)

NOVA-02 explicitly accepted the Core draft event envelope in issue #9: required fields are `schema_version`, `event_id`, `task_id`, `sequence`, `occurred_at`, `type`, `state`, `origin` and `correlation_id`; `step`, `progress`, `approval`, `result` and `error` are optional slots. No additional desktop-required envelope fields were requested. Origin must come from authenticated server/session context and is not trusted when client-asserted. `task.cancel_requested` is nonterminal; `task.cancelled` is terminal and must carry authoritative state `cancelled`. The consumer still requires monotonic per-task sequence, unique event IDs, snapshot recovery on gaps/reconnect, safe summaries and AEGIS-owned approval authorization. This is an accepted draft envelope, not a frozen cross-project version or implemented transport. See issue #9 acceptance comment in the current thread.

### Schema validation tooling (development only)

The Core schema suite uses Python `jsonschema` Draft 2020-12 as a development-only validator; this does not select the Core service implementation language or runtime. Install with `python -m pip install -r tusker-core/requirements-dev.txt`, then run `python -m unittest discover -s tusker-core/tests -v`. The tests check every representative valid fixture, schema self-consistency, format constraints, rejection of unknown top-level fields and unsupported schema versions, required event origin, and the terminal cancellation event. A GitHub Actions workflow runs the same command when schemas, fixtures or validator tests change.
