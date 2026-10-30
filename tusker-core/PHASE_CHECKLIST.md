# TUSKER-04 Phase Checklist

**Owner:** TUSKER-04  
**Branch:** `04-tusker-core`  
**Status:** P0 substantially documented; P1 in cross-agent review  
**Rule:** Every task and subtask stays independently checkable. Checkboxes are not complete without evidence.

## P0 — Discovery and requirements

- [x] Translate project mission into supported task categories.
  - [x] Files and directories.
  - [x] Applications and processes.
  - [x] Desktop and user settings.
  - [x] Devices and peripherals.
  - [x] Networking and connectivity.
  - [x] Developer workflows.
  - [x] System maintenance.
  - [x] Remote-assisted tasks through authenticated adapter.
- [x] Define risk, success and clarification behavior.
  - [x] Distinguish read-only, low-risk reversible, sensitive, privileged, destructive and security-critical work.
  - [x] Define reversible versus irreversible side effects.
  - [x] Require clarification for ambiguous targets or high-impact intent.
  - [x] Require explicit user confirmation where policy demands it.
  - [x] Define postconditions and evidence for completion.
- [x] Define end-to-end lifecycle.
  - [x] Request and authenticated origin.
  - [x] Conversation/context selection.
  - [x] Intent classification and clarification.
  - [x] Plan validation and dependency ordering.
  - [x] Authorization preflight and approval.
  - [x] Typed execution and progress.
  - [x] Independent verification.
  - [x] Result, audit/evidence references and recovery.
- [x] Define failure taxonomy.
  - [x] Misunderstanding and ambiguity.
  - [x] Model/provider unavailable or malformed output.
  - [x] Tool unavailable or unsupported operation.
  - [x] Permission denied, approval expired or policy unavailable.
  - [x] Precondition/stale-state conflict.
  - [x] Timeout and unknown mutation outcome.
  - [x] Cancellation race and partial execution.
  - [x] Persistence failure and restart recovery.
  - [x] Verification failure.
- [ ] Review requirements and acceptance criteria with Chief Architect.
- [ ] Record measurable latency/reliability targets after a baseline environment is selected.

## P1 — Architecture and contracts

- [x] Separate conversation, intent, planner, scheduler, executor, policy client, verifier, event manager, persistence and recovery responsibilities.
- [x] Draft versioned task, plan, step, action proposal, tool adapter, event, approval reference, result, error and cancellation contracts.
- [x] Draft task state machine and transition invariants.
- [x] Add provisional JSON Schema 2020-12 files for Task, Plan, TaskEvent, TaskResult and Cancellation (not yet consumer-approved or validator-tested).
- [x] Add one representative valid JSON fixture for each Core schema (JSON syntax checked; full JSON Schema validation remains pending).
- [x] Review NEXUS invocation/result/descriptor constraints and align Core operation-name and timeout ceilings.
- [x] Align optional Core idempotency-key shape bounds with NEXUS and specify a descriptor-aware mutation admission gate; conformance tests authored, not yet executed.
- [x] Align optional Core idempotency-key shape bounds with NEXUS and specify a descriptor-aware mutation admission gate; conformance tests authored, not yet executed.
- [x] Review AEGIS action-proposal/policy-decision semantics and document fail-closed adapter requirements.
- [x] Draft local persistence, retention, export/delete and migration requirements.
- [x] Review NEXUS-07 tool contract proposal and submit owner feedback.
- [x] Review AEGIS-06 security contract proposal and submit owner feedback.
- [x] Submit NOVA-02 desktop event/control proposal.
- [x] Submit PILOT-08 remote task lifecycle proposal.
- [x] Open ORBIT-05 inference contract coordination issue.
- [ ] Obtain explicit ORBIT-05 acknowledgement and contract.
  - [x] Review published provider proposal and request exact normative request/event/error schemas and cancellation/disconnection semantics (issue #25; owner response pending).
- [x] Obtain AEGIS-06 semantic confirmation for UUID IDs, mutation idempotency, fail-closed ALLOW validation and DENY/REQUIRE_APPROVAL fields (issue #16 comment 6531421607; transport/one-time broker consumption still open).
- [ ] Obtain explicit NEXUS-07 confirmation of invocation/result/cancellation fields.
- [ ] Obtain explicit NOVA-02 confirmation of event/snapshot/control fields.
  - [x] Compare event envelope against Core schema; add missing terminal cancellation event and require trusted origin metadata; request NOVA confirmation (issue #9; owner response pending).
- [ ] Obtain explicit PILOT-08 confirmation of remote task/identity fields.
  - [x] Publish Core owner response for DEC-TUS-001 through DEC-TUS-007 and post it to issue #14; decisions remain REVISE except pause/resume DEFERRED, with implementation blockers explicitly retained.
- [ ] Obtain ATLAS-01 decision on IPC, packaging, service lifecycle and runtime paths.
  - [x] Re-request concrete transport, peer identity, user-service lifecycle, XDG paths and SQLite/WAL recommendation (issue #27; owner response pending).
- [ ] Record accepted shared decisions and exact contract versions.

## P2 — Foundation

- [ ] Confirm implementation language/runtime and packaging constraints with ATLAS-01.
- [ ] Record ADR for IPC transport and service lifecycle.
- [ ] Record ADR for local persistence, encryption and retention.
- [ ] Create core service/module skeleton.
- [ ] Implement configuration validation and safe defaults.
- [ ] Implement transactional task persistence and schema migrations.
- [ ] Implement central task state machine and transition validation.
- [ ] Implement append-only task events and sequence replay.
- [ ] Implement model provider interface and deterministic mock provider.
- [ ] Implement tool gateway interface and deterministic mock tools.
- [ ] Implement AEGIS policy-client interface and deny/unavailable test doubles.
- [ ] Implement verification interface and fake postcondition observers.
- [ ] Add structured, redacted diagnostics and health reporting.
- [ ] Add schema validation and contract fixtures.
- [ ] Add unit tests for all valid/invalid task transitions.
- [ ] Add tests for persistence failure, restart replay and migration interruption.

## P3 — Working MVP

- [ ] Connect one installed local model provider through ORBIT-05.
- [ ] Support read-only natural-language system question.
- [ ] Support one low-risk allowlisted action through NEXUS-07.
- [ ] Require AEGIS authorization for every mutation.
- [ ] Present a multi-step plan before sensitive operations.
- [ ] Verify postconditions independently.
- [ ] Demonstrate completed, failed, skipped and uncertain step reporting.
- [ ] Demonstrate offline operation with an installed local model.
- [ ] Record end-to-end VM/test environment and evidence.

## P4 — Complete feature set

- [ ] Add dependency-aware multi-step planning.
- [ ] Add bounded retries and idempotency.
- [ ] Add stale-state refresh and precondition revalidation.
- [ ] Add timeout and unknown-outcome reconciliation.
- [ ] Add cancellation propagation and race handling.
- [ ] Add safe checkpoint pause/resume only for capable tasks.
- [ ] Add partial completion and authorized compensation hooks.
- [ ] Add local context/memory retention controls.
- [ ] Add clarification for ambiguous/high-impact instructions.
- [ ] Add task provenance/activity history and safe explanation.

## P5 — Integration

- [ ] Integrate ORBIT-05 inference, streaming, capability and offline behavior.
- [ ] Integrate AEGIS-06 authorization, approval, broker and audit references.
- [ ] Integrate NEXUS-07 tool registry, preconditions, results, cancellation and postconditions.
- [ ] Integrate NOVA-02 event stream, task snapshot, notifications and controls.
- [ ] Integrate PILOT-08 authenticated remote task adapter with same Core task identity.
- [ ] Run cross-component contract tests.
- [ ] Publish compatibility matrix and unresolved integration blockers.

## P6 — Verification and hardening

- [ ] Build deterministic intent/planning/tool-selection evaluation fixtures.
- [ ] Test prompt injection in files, web pages, tool output and extension metadata.
- [ ] Test model attempts to bypass permissions or fabricate tool results.
- [ ] Test malformed/oversized inputs and unknown schema versions.
- [ ] Test offline mode and provider outage.
- [ ] Test process restart during planning, approval, execution and verification.
- [ ] Test duplicate submissions and idempotency collisions.
- [ ] Test concurrent tasks with conflicting resources.
- [ ] Test cancellation races and non-cancellable tools.
- [ ] Test policy denial, expiry, replay, mismatch and policy outage.
- [ ] Test tool timeout with side effect completed/not completed/unknown.
- [ ] Measure latency, RAM, CPU, context usage and long-session stability on named hardware profiles.
- [ ] Publish reliability/security/performance results and limitations.

## P7 — Release and handover

- [ ] Freeze and document stable public Core API and schemas.
- [ ] Publish examples/fixtures for every supported task category.
- [ ] Publish test fixtures for every task state transition.
- [ ] Document configuration, local data, retention, export/delete and migrations.
- [ ] Document approval, offline, failure, cancellation and recovery behavior for users.
- [ ] Publish compatibility and API version policy.
- [ ] Publish unresolved risk register and maintenance handover.
- [ ] Obtain release sign-off with reproducible test evidence.


### C0015 — AEGIS approval/consume semantic closure

- [x] Record that approval resumes only through a fresh AEGIS ALLOW and new authorization_ref after exact-proposal/current-context re-evaluation.
- [x] Record that the broker consumes authorization_ref, never approval_request_id; prior unconsumed references are invalidated on re-issue.
- [x] Record typed consume outcomes and zero-dispatch behavior for every non-CONSUMED outcome.
- [x] Record required pre-dispatch audit fail-closed semantics and reconciliation requirements for ALREADY_CONSUMED / CONSUME_OUTCOME_UNKNOWN.
- [ ] Obtain NEXUS strict authorization_context, trusted peer injection, atomic consume transport and durable execution reconciliation contract.
- [ ] Implement and execute cross-layer authorization conformance tests; no implementation/test pass is claimed.
