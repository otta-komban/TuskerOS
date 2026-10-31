# AEGIS-06 Threat Model and Phase 1 Delivery Plan

**Agent:** AEGIS-06 — Security Gatekeeper  
**Assigned branch:** `06-AEGIS`  
**Baseline inspected:** `345fc5a3d0f831fc714bae0cc88fa842cd9bed79` (same as live `main`)  
**Task ID:** Awaiting Chief Architect assignment  
**Status:** Planning deliverable; no shared contract or privileged runtime change is authorized by this document.

## 1. Mission and security objectives

AEGIS is the authorization boundary between untrusted intent and privileged system effects. The planner, model, extension, remote caller and approval UI are not authorities. AEGIS must make a deterministic decision from validated action data and trusted identity context; a broker must independently authenticate its caller and consume a fresh, exact-scope authorization before any privileged dispatch.

Security objectives:

1. Default deny for unknown, malformed, stale, unverifiable or unsupported requests.
2. No caller-controlled identity, policy decision, approval state or authorization capability.
3. Approval binds the exact action, principal/session/device, operation, canonical resources, policy/registry versions, preconditions and expiry.
4. A single atomic consume wins; ambiguous outcomes never authorize dispatch or blind retry.
5. Broker APIs remain narrow, typed and allowlisted; no generic shell/root interface.
6. Required audit evidence is durable, integrity-protected, access-controlled and redacted.
7. Failure of identity, registry, policy, clock, authorization storage or required audit fails closed.
8. Privileged operations remain disabled until cross-agent integration and release evidence satisfy `security/PRIVILEGED_RELEASE_GATE.md`.

## 2. Assets and trust boundaries

### Protected assets

- Authenticated principal, session and device bindings.
- Immutable proposal/action digests, canonical resource scopes and precondition snapshots.
- Approval state, opaque authorization references, expiry and one-time consumption records.
- Trusted operation registry, registry version and fixed operation-to-handler mapping.
- Policy configuration/version and risk classification.
- Broker dispatch intent, idempotency records and execution outcomes.
- Audit events, HMAC chain state, external checkpoints and audit-key material.

### Trust boundaries

| Boundary | Trusted side | Untrusted input / required enforcement |
|---|---|---|
| Planner/model to AEGIS | AEGIS policy engine | Typed proposal only; validate schema, bounds, operation and resources. Ignore model-supplied risk or authority claims. |
| OS/session identity to policy | Trusted identity adapter | Derive identity from authenticated OS/session context. Never trust principal/session/device fields asserted in request JSON. |
| Approval presenter to authority | Authenticated user-decision capture | Display trusted operation metadata and exact scope. Approval is a decision, not a reusable bearer grant. |
| Policy/authority to broker | Trusted authorization authority | Fresh opaque authorization reference; broker rechecks peer, operation, resources, digest, expiry and consume outcome. |
| Broker to system handler | Fixed NEXUS handler mapping | Typed operation-specific arguments, independent checks, bounded execution and durable dispatch intent. |
| Runtime to audit sink | AEGIS audit producer/store | Redact secrets and unnecessary payloads; fail closed where pre-dispatch audit is mandatory. |
| Filesystem to security store | OS filesystem and deployment controls | Reject symlinks, unsafe inode/path changes and shared database aliases; protect directory and key lifecycle. |

## 3. Threat register

| ID | Threat / failure mode | Required security response | Current evidence boundary |
|---|---|---|---|
| TH-01 | Model, extension, remote caller or UI forges principal, origin, decision, approval or authorization fields | Reject authority-shaped caller fields; derive identity out-of-band; only AEGIS may issue a decision | Proposal/decision schemas are closed; NEXUS public invocation and trusted internal-context boundary still require final interface review. |
| TH-02 | Confused deputy or privilege escalation through generic shell, arbitrary executable path or caller-selected handler | Fixed registered operation IDs and typed handlers; no generic root API; broker independently validates | Broker contract specifies this invariant; production handler mapping and OS confinement are not evidenced. |
| TH-03 | Approval substitution, replay, expiry or use after action/resource/identity change | Bind immutable digest and all context; revalidate at consume; atomic one-time state transition | Lifecycle and approval schema describe binding; production authority/consumer integration remains pending. |
| TH-04 | Resource resolver drops, broadens or changes the target between approval and dispatch | Bind both requested and canonical resource identity; re-resolve and compare preconditions immediately before dispatch | Policy runtime has resource-resolution checks; NEXUS-side independent consume/precondition enforcement remains unproven. |
| TH-05 | Concurrent consume or lost response causes duplicate mutation | Durable compare-and-set; unique consumption ID; reconcile ambiguous result; never blindly redispatch | Lifecycle contract requires this; NEXUS has accepted the invariant semantically, but transport/store implementation is not accepted or evidenced. |
| TH-06 | Registry tampering, rollback, malformed unrelated entry or stale version | Verify trusted provenance, schema and immutable version; reject whole registry on invalidity | Policy code validates registry entry shape; trusted runtime loading/signature verification and revocation remain integration blockers. |
| TH-07 | Security database symlink, hard-link, path-swap or unsafe permission attack | Open without following symlinks, verify regular file/inode/link count, owner-only mode and no path replacement before SQL | Current runtime contains database-path hardening; exact tests must be rerun on this branch before relying on it as acceptance evidence. |
| TH-08 | Audit alteration, truncation, sequence rewriting, secret leakage or checkpoint rollback | HMAC chain, sequence continuity, redaction, externally retained checkpoints, access controls and recovery tests | Store contains HMAC-chain and checkpoint mechanisms; key provisioning/rotation, external retention, access control and recovery remain platform work. |
| TH-09 | Policy, identity, registry, clock, storage or audit outage falls through to execution | Deny with zero handler calls; no permissive fallback or caller-controlled bypass | Policy/store contracts specify fail-closed outcomes; production NEXUS zero-dispatch integration evidence is absent. |
| TH-10 | Canonicalization ambiguity, Unicode normalization or unsupported numeric input changes digest meaning | Implement and test RFC 8785 JCS; preserve Unicode code points; reject invalid surrogate input and unsupported values | Current runtime README records incomplete full-JCS support; reference vectors alone are not production conformance. |
| TH-11 | Oversized, deeply nested or high-rate inputs exhaust memory, CPU, storage or broker capacity | Bound payload, nesting, path, output, time, concurrency and rate; reject before mutation | Several runtime validators impose bounds; unified end-to-end resource-limit evidence remains required. |
| TH-12 | Timeout/cancellation is mistaken for failure or confirmed cancellation, then operation is retried | Return UNKNOWN after possible dispatch; reconcile durable execution/idempotency state; cancellation and compensation are separate authorized actions | Broker contract defines UNKNOWN/reconciliation; NEXUS runtime evidence remains outstanding. |

## 4. Baseline findings verified during this review

- The assigned branch exists and is at the same commit as live `main`; there is no branch-only implementation delta at the inspected baseline.
- PR #70, “Require literal true from policy verification callbacks,” is merged. The current `security/runtime/policy.py` requires literal boolean `True` from registry, identity and argument-verifier callbacks.
- The active approval-request schema is v0.2.0 and includes a required binding object for session, device, registry version, canonical resource scope and precondition digest.
- The active audit-event v0.1.0 schema requires `task_id` and `step_id`. The candidate v0.2.0 schema also requires them and adds registry status/version fields.
- The v0.2.0 audit proposal still documents unresolved lifecycle coverage/producer semantics for presentation, dismissal, invalidation, revocation, consume outcomes and reconciliation. Do not promote the candidate or infer producer conformance.
- NEXUS-07 has accepted key security invariants in principle (authenticated IPC peer, fresh opaque authorization reference, atomic consume, registry ownership, idempotency and UNKNOWN reconciliation). The concrete transport/API, trusted context injection, authorization authority/store and runtime implementation remain unselected or unaccepted.
- `security/runtime/broker.py` is an authorization adapter, not evidence of a production privileged broker with system handlers. `security/runtime/README.md` and the privileged release gate explicitly retain production blockers.
- The legacy branch `06-security-gatekeeper` is divergent from current `main` (9 commits ahead / 572 behind at review). Its unique changes are preserved for separate review; none are blindly cherry-picked or merged here.

These are source/metadata observations, not a claim that tests were run in this response or that a production security boundary is operational.

## 5. Phase 1 work plan

| Step | Deliverable | Dependencies | Acceptance criteria |
|---|---|---|---|
| P1.1 | Reconcile legacy AEGIS changes against the current baseline | Exact source diffs and test evidence | Each unique commit reviewed independently; port only minimal, compatible changes with regression tests; preserve old refs/logs. |
| P1.2 | Complete approval/audit schema-to-lifecycle audit | TUSKER task/step semantics; NEXUS producer feedback | Field-by-field matrix for required/nullable/conditional fields, lifecycle event coverage, provenance, versioning and compatibility; unresolved shared changes escalated for Chief Architect approval. |
| P1.3 | Verify policy, approval and SQLite store behavior | Existing runtime tests and CI environment | Exact-head tests for deny-by-default, literal-true callbacks, stale/altered approvals, peer binding, replay, one-time consume, concurrency, audit failure and database path attacks. |
| P1.4 | Freeze trusted broker authorization interface | Chief Architect approval; NEXUS runtime/API owner; TUSKER envelope mapping | Typed internal-only context, authenticated peer provenance, consume request/response, durable transaction boundary, registry provenance, idempotency and UNKNOWN reconciliation accepted by owners. |
| P1.5 | Prove cross-boundary denial and dispatch invariants | NEXUS implementation and disposable integration environment | Every denial/mismatch/unavailable dependency yields zero handler calls; two-consumer race has one winner; ambiguous dispatch reconciles without duplicate side effects. |
| P1.6 | Close audit durability and recovery evidence | ATLAS service/OS packaging; NEXUS producer; owner-managed key lifecycle | Redaction, tamper/truncation detection, sequence continuity, access control, key rotation, external checkpoint retention, disk-full behavior and recovery are tested. |
| P1.7 | Publish privileged release decision | AEGIS + NEXUS + dependent owner sign-offs | Every release-gate row has exact-head test/build evidence and reviewer; otherwise status remains BLOCKED and privileged handlers stay disabled. |

## 6. Explicit non-goals and stop conditions

- Do not invent or freeze a NEXUS transport, IPC method, socket path, service identity, storage engine or wire schema.
- Do not change shared schemas, lifecycle semantics or privilege boundaries without Chief Architect approval and producer/consumer compatibility evidence.
- Do not treat a mock callback, schema test, HMAC unit test or design document as proof of production authorization or broker enforcement.
- Do not enable privileged handlers or execute destructive/system mutations as part of this phase.
- Stop the affected implementation step if trusted identity, registry provenance, atomic consume, audit durability or owner approval is missing.

## 7. Rollback and validation record

This file is a documentation-only planning artifact. Rollback is a focused revert of this document commit; no runtime state, schema, user data or privileged configuration is changed. No tests were run for this documentation-only change. Runtime validation must be recorded separately with exact command, exit code, test count and tested SHA.

## 8. Immediate next action

Obtain a Chief Architect task ID and approval for the internal AEGIS/NEXUS broker interface. In parallel, complete the read-only audit of the candidate audit-event lifecycle mapping and review the nine unique commits on the preserved legacy branch. Keep privileged dispatch disabled until P1.4–P1.7 are evidenced.
