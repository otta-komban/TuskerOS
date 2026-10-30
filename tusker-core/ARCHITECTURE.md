# TUSKER-04 — AI Core Architecture (P0/P1 baseline)

**Status:** Proposed baseline; cross-agent contracts pending approval  
**Owner:** TUSKER-04  
**Branch:** `04-tusker-core`  
**Owned scope:** `tusker-core/`, task orchestration, planner/executor APIs, local task state, agent evaluation and core documentation.

## 1. Mission and non-negotiable properties

Tusker Core is a model-independent local agent service. It converts user requests into observable, permission-checked, verifiable tasks. It must not be required for the desktop or operating system to remain usable.

- Local-first; supported installed-model workflows operate offline.
- No paid/cloud inference dependency in the default configuration.
- Model output is untrusted input, never authorization.
- No unrestricted shell or root execution from the model.
- Every mutating tool call passes deterministic AEGIS authorization.
- Sensitive/destructive operations require explicit approval.
- Every completion claim is backed by tool evidence and postcondition checks.
- Persistence is local by default, with explicit retention/export/deletion controls.
- Core crashes and model/tool failures are isolated from the OS.
- All retries, timeouts, cancellation and partial completion are explicit and bounded.

## 2. Logical architecture

User / NOVA-02 UI / PILOT-08 remote client
  -> Core API + Session Manager
  -> Intent & Clarification
  -> Planner
  -> Task Scheduler / State Machine
  -> Authorization preflight (AEGIS-06)
  -> Typed Tool Gateway (NEXUS-07)
  -> Independent Verification
  -> Result / Audit references / UI events

ORBIT-05 supplies model inference behind a provider-neutral adapter. The model adapter cannot call tools directly and cannot grant itself permission.

Internal modules:
- api: local IPC/API boundary, authentication of local callers, request validation.
- conversation: session/message context and privacy filtering.
- intent: task category, constraints, ambiguity and confidence signals.
- planner: typed DAG/ordered steps, dependencies, preconditions and expected outcomes.
- scheduler: concurrency limits, ordering, deadlines and idempotency.
- execution: tool gateway, bounded retries, timeout and cancellation propagation.
- policy_client: AEGIS preflight/approval/status interface; fail closed.
- verification: independent observations and postcondition evaluation.
- events: ordered task events and replay.
- persistence: transactional task/session/event records and migrations.
- recovery: interrupted-task reconciliation and safe resume/compensation.
- evaluation: deterministic fixtures, scenario suite and metrics.

## 3. Task lifecycle

Canonical states:
queued -> planning -> awaiting_approval -> running -> verifying -> completed

Terminal/alternate states:
failed, cancelled, partially_completed

Rules:
- State transitions are validated centrally and persisted transactionally.
- A task may enter running only after required authorization is granted.
- Approval denial prevents the associated operation; it is not retried as a model decision.
- Cancellation is cooperative, propagated to active tools, and acknowledged only after the executor reports its state.
- A timeout is not proof that an operation did not happen. Reconcile actual state before retrying.
- A task with mixed successful and failed steps is partially_completed unless safe compensation restores the declared pre-state.
- Recovery never blindly replays a non-idempotent operation.
- completed requires successful verification of all required postconditions.

## 4. Proposed versioned contracts (P1)

Use JSON-compatible schemas with explicit `schema_version`, stable machine-readable identifiers, bounded strings/arrays, UTC RFC3339 timestamps and structured errors. Exact transport (D-Bus vs local Unix socket/HTTP) remains an ADR after ATLAS-01/NOVA-02 platform review.

### Task
`Task`: {schema_version, task_id, session_id, request_id, created_at, updated_at, state, user_request, normalized_intent, plan_id, risk_summary, current_step_id, result_ref, error, version}

### Plan / Step
`Plan`: {schema_version, plan_id, task_id, created_at, steps[], dependencies[], expected_outcomes[], requires_confirmation}
`Step`: {step_id, order, tool_name, tool_version, input, preconditions[], expected_postconditions[], risk, timeout_ms, retry_policy, idempotency_key, state}

Plan inputs are untrusted until validated. Tool names must resolve through the NEXUS registry; no arbitrary command string is an executable tool definition.

### Tool invocation/result
`ToolCall`: {schema_version, call_id, task_id, step_id, tool_name, input, caller_identity, idempotency_key, deadline}
`ToolResult`: {schema_version, call_id, status, output, started_at, finished_at, side_effects[], evidence_refs[], error, cancellation_status}

### Authorization / approval
`AuthorizationRequest`: {schema_version, request_id, task_id, step_id, actor, action, resource_summary, risk, rationale, expires_at}
`AuthorizationDecision`: {schema_version, request_id, decision_id, outcome, policy_version, decided_by, decided_at, expires_at, audit_ref}
Outcomes: allow, deny, approval_required, expired, unavailable. Core must fail closed on unavailable/invalid policy responses. Approval is bound to exact action/resource/input digest and expires; changed inputs require a new decision.

### Progress event
`TaskEvent`: {schema_version, event_id, task_id, sequence, occurred_at, type, state, step_id, progress, safe_summary, evidence_refs[], correlation_id}
Events are append-only and monotonically sequenced per task. Do not put secrets or raw private file contents in summaries.

### Result / error
`TaskResult`: {schema_version, task_id, final_state, summary, completed_steps[], failed_steps[], skipped_steps[], verification[], evidence_refs[], limitations[]}
`CoreError`: {code, category, message, retryable, retry_after_ms, details_safe, correlation_id}
Categories include invalid_request, intent_uncertain, model_unavailable, tool_unavailable, permission_denied, approval_expired, precondition_failed, timeout, cancelled, verification_failed, persistence_failure, partial_execution and internal_error.

### Cancellation
`CancelRequest`: {schema_version, task_id, requested_by, reason, requested_at}
`CancelResult`: {task_id, accepted, state, active_step_id, tool_acknowledgements[], safe_to_retry, evidence_refs[]}

### Audit reference
Audit payload ownership belongs to AEGIS-06. Core emits correlation/task/step identifiers and references, not a competing authorization ledger.

## 5. Agent dependencies and agreements

- ORBIT-05: provider-neutral inference request/stream/cancel/health/capability contract; model errors and context limits.
- AEGIS-06: preflight authorization, approval binding/expiry, denial semantics, audit references and fail-closed behavior.
- NEXUS-07: typed tool registry, schema versions, preconditions, risk, result/error, progress, cancellation, idempotency and verification/rollback capabilities.
- NOVA-02: task/event presentation, progress, approval surface, pause/resume/cancel and connection-loss behavior. UI is not the policy enforcement point.
- PILOT-08: authenticated remote caller identity, task submission/status/events/cancel and approval routing; remote requests use identical local policy.
- ATLAS-01: service packaging, user/system service boundary, IPC/runtime paths, logging and configuration conventions.

No cross-agent interface is considered agreed until the owner acknowledges it and the shared contract/decision records are updated.

## 6. Local persistence and privacy

Initial logical entities: sessions, messages, tasks, plans, steps, task_events, verification_records, migration_metadata and user_preferences. Prefer SQLite with transactions/WAL if approved by the platform review; keep the storage adapter replaceable.

- Store under a per-user application data directory with restrictive permissions.
- Separate operational metadata from optional conversation content.
- Never persist credentials, authorization tokens or raw secrets in task logs.
- Retention is configurable; export/delete operations must include documented scope and confirmation for destructive deletion.
- Schema migrations are versioned, transactional and tested against interrupted migration.
- Event replay is deterministic and does not re-execute side effects.
- Backups and restore behavior must be documented and tested.

## 7. Failure and recovery policy

| Failure | Required behavior |
|---|---|
| Model/provider unavailable | Preserve task; report unavailable; allow retry when safe |
| Ambiguous/high-impact intent | Ask user; do not guess |
| Tool unavailable | Fail/partial with typed error; no fabricated success |
| Permission denied | Stop affected step; do not route around policy |
| Approval expired | Re-request approval for unchanged or refreshed action |
| Timeout | Reconcile state before retry |
| Partial execution | Report exact successful/failed/skipped steps |
| Cancellation race | Reconcile tool state; disclose irreversible effects |
| Core restart | Replay events/state; reconcile running steps before resume |
| Persistence failure | Stop new mutations; surface degraded state |
| Verification failure | Never report completed; mark uncertain/failed/partial |

## 8. Measurable quality goals (provisional)

- 100% of mutating tool calls have a recorded authorization decision.
- 0 tool invocations when authorization is denied, expired or unavailable.
- 100% of completed tasks have required postcondition evidence.
- 100% of cancellation/timeout scenarios report uncertain side effects honestly.
- No automatic retry of a non-idempotent operation without reconciliation.
- Deterministic tests cover every legal/illegal state transition.
- Offline tests prove core + installed provider workflow requires no network.
- Performance targets are set only after baseline measurements on named VM/hardware profiles.

## 9. Risks and open decisions

1. IPC choice and service lifecycle depend on Fedora/KDE packaging and desktop integration review.
2. SQLite is proposed, not yet accepted; encryption-at-rest and key management need a privacy/security decision.
3. Approval UI and policy protocol need AEGIS-06/NOVA-02 agreement.
4. Tool schemas and rollback guarantees depend on NEXUS-07 capabilities; compensation is not universally possible.
5. Model quality is probabilistic; deterministic validation and postcondition checks remain mandatory.
6. Long-running tasks need process ownership, restart reconciliation and resource limits.
7. Concurrent tasks may conflict on shared resources; resource locking/serialization policy needs explicit design.
8. User data migration, retention defaults and deletion semantics need a documented product decision.

## 10. Phase plan

### P0 — Discovery
- [x] Repository and branch inspected; baseline confirmed to contain LICENSE only.
- [x] Mission, task lifecycle, task categories and failure classes extracted from master blueprint.
- [ ] Confirm supported task categories and acceptance criteria with Chief Architect.
- [ ] Obtain dependency-agent requirements and record unresolved assumptions.
- [ ] Establish baseline reliability/performance evaluation plan.

### P1 — Architecture and contracts
- [x] Draft module boundaries and logical architecture.
- [x] Draft task, plan, step, tool, event, approval, result, error and cancellation schemas.
- [x] Draft local persistence/privacy and recovery model.
- [ ] Review transport and storage ADRs with ATLAS-01.
- [ ] Obtain ORBIT-05, AEGIS-06, NEXUS-07, NOVA-02 and PILOT-08 contract acknowledgements.
- [ ] Record accepted interfaces in shared contract/decision documents when those shared paths are available.

### P2 — Foundation (next)
- [ ] Confirm language/runtime and packaging constraints before choosing implementation stack.
- [ ] Create service skeleton and configuration.
- [ ] Implement state machine and persistence adapter.
- [ ] Add mock model/tool providers and deterministic fixtures.
- [ ] Add schema validation, event replay and diagnostics.
- [ ] Run unit/contract tests including failure and restart cases.

## 11. Handover status

No production code, runtime test, cross-agent agreement or end-to-end behavior is claimed by this document. This is a proposed P0/P1 architecture baseline. Next action: inspect the full shared planning pack and obtain dependent-agent contract feedback before committing to transport/runtime choices.
