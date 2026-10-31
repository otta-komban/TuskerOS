# TUSKER-04 — Lifecycle Intake Plan and Contract Audit

**Agent:** TUSKER-04  
**Assigned branch:** `04-TUSKER`  
**Repository:** `otta-komban/TuskerOS`  
**Baseline:** `345fc5a3d0f831fc714bae0cc88fa842cd9bed79` (live `main` and assigned branch)  
**Status:** Intake/audit complete; lifecycle semantics remain provisional pending Chief Architect approval.

## 1. Task plan

### Objective
Deliver a contract-compatible Core task lifecycle with typed, append-only events, deterministic transitions, cancellation, idempotency, and safe failure/recovery behavior.

### Work sequence
1. **Intake and contract audit (this deliverable):** compare Core architecture, contracts, schemas, fixtures, lifecycle engine, tests, Issue #53, and the merged historical implementation.
2. **Transition/event proposal:** prepare a review-only transition matrix and event envelope proposal; request Chief Architect approval and NEXUS/ORBIT integration confirmation. Do not change shared semantics before approval.
3. **Lifecycle implementation:** extend the existing backend-neutral engine only against approved semantics; preserve the current schema compatibility boundary.
4. **Durable store and replay:** implement transactional snapshot/event/idempotency persistence only after ATLAS/platform persistence decisions are available; require atomic compare-and-swap and restart-safe replay.
5. **Integration and hardening:** connect NEXUS/ORBIT interfaces after owner confirmation; add race, duplicate/replay, stale-version, cancellation, malformed-data, and unknown-outcome tests.
6. **Handover:** publish API/version, compatibility, migration, rollback, test, and integration notes; open a focused PR for coordinator review.

### Acceptance criteria
- Chief Architect records the approved contract version and transition/event semantics.
- Engine writes conform to the approved Task, Plan, TaskEvent, TaskResult, and Cancellation schemas.
- State changes, event append, and idempotency outcome are atomic in the production store.
- Replay validates the persisted history and never re-executes side effects.
- Duplicate requests, conflicting idempotency keys, stale versions, cancellation races, and unknown mutation outcomes fail safely.
- Core tests and exact-head CI pass; all claims identify tested commit and workflow evidence.
- Compatibility, migration, rollback, and unresolved integration dependencies are documented.

### Dependencies / gates
- Chief Architect approval of shared lifecycle semantics and event envelope.
- NEXUS-07 confirmation of tool result, cancellation, idempotency, and authorization handoff behavior.
- ORBIT-05 confirmation of inference lifecycle/cancellation event needs.
- ATLAS-01 platform decision for Core service, IPC, and durable persistence.
- Sensitive, privileged, destructive, or externally consequential actions remain approval-gated.

## 2. Branch and history verification

- GitHub branch lookup confirms `04-TUSKER` exists.
- Live `main` SHA: `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`.
- Assigned branch `04-TUSKER` resolves to the same SHA; GitHub compare reports 0 ahead / 0 behind.
- The retired `agent/04-tusker-core` history is preserved. Its lifecycle work was delivered through PR #62, which is merged; the merged implementation is already present on this assigned branch.
- The prior legacy ref `04-tusker-core` is highly divergent (GitHub compare reports 0 ahead / 1666 behind); it will not be merged, rebased, or cherry-picked.
- No open PRs were returned by the connected GitHub listing.
- A clean local working tree cannot be verified through the GitHub API; no claim is made about local checkout state.

## 3. Existing implementation and contract audit

### Existing implementation (merged PR #62)
The current Core implementation contains a backend-neutral `LifecycleEngine` and a thread-safe `InMemoryLifecycleStore`. It enforces a finite task-state vocabulary, transition checks, terminal-state immutability, optimistic version checks, task-version/event-sequence coupling, event ID uniqueness, idempotency replay/fingerprint conflicts, confirmed-stop cancellation, and replay integrity checks.

The in-memory store is explicitly a reference/test implementation. It is not durable and does not establish crash recovery or production event delivery. The engine does not yet provide a durable event store or a production scheduler/tool-dispatch integration.

### Findings
1. **Provisional contract status:** Core schemas identify themselves as `0.1.0-draft`; the architecture and contract notes say cross-agent approval is pending. These are not frozen shared APIs.
2. **Architecture/schema naming drift:** the architecture's Task sketch includes `normalized_intent` and `risk_summary`, while the current Task schema uses `intent` and does not define those architecture fields. The architecture sketch and schema are not a single canonical field list.
3. **Step lifecycle is separate from task lifecycle:** Plan steps use `pending/ready/running/awaiting_approval/succeeded/failed/cancelled/skipped/unknown_outcome`, while Task and TaskEvent use task-level states. The existing engine validates task-level state transitions; it does not implement a step state machine.
4. **Partial schema conformance coverage:** the lifecycle-engine tests validate Task and TaskEvent instances. Separate schema tests cover representative fixtures for all five schemas, but they do not prove every engine-produced result/cancellation payload or full cross-schema workflow compatibility.
5. **Event contract remains a draft boundary:** the TaskEvent schema requires `origin`, `correlation_id`, task ID, event ID, sequence, timestamp, type, and state. The engine emits these base fields. Event payload slots are loosely typed objects/null, so their cross-agent meaning and version compatibility still need owner decisions.
6. **Durability is unresolved:** the current store keeps snapshots, events, and idempotency records in process memory. Restart-safe persistence, retention, transaction semantics, and recovery reconciliation remain unimplemented.
7. **Integration gates remain open:** the engine is not wired to NEXUS dispatch, AEGIS authorization enforcement, ORBIT inference, or NOVA event delivery. The role guide lists NEXUS and ORBIT as dependencies; the launch plan also calls out ATLAS for service/persistence decisions.
8. **Issue #53 is historical context, not a new contract approval:** it records the earlier activation/contract blockers and old branch name. The owner and Chief Architect later authorized controlled branch-isolated work in Issues #35 and #34. That authorization does not waive the requirement for Chief Architect approval before shared lifecycle semantics are changed.

## 4. First deliverable result

- Repository/role/operating guides and launch logging policy reviewed.
- Assigned branch and live main SHA verified.
- Current Core schemas, architecture, contracts, checklist, lifecycle implementation, tests, Issue #53, and historical PR #62 reviewed.
- No shared schema or lifecycle semantics changed in this intake deliverable.
- No tests run: this deliverable is a documentation/repository audit, not a code change.

## 5. Next action

Prepare a review-only transition matrix and event-envelope proposal, then request the Chief Architect's explicit approval and record NEXUS/ORBIT decisions before modifying shared semantics or implementing durable storage.
