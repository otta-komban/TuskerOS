# FORGE-09 Transaction Executor Delivery Plan

**Owner:** FORGE-09 — Ecosystem & Extensions  
**Branch:** `09-FORGE`  
**Baseline:** `main` and `09-FORGE` both resolve to `345fc5a3d0f831fc714bae0cc88fa842cd9bed79` at intake.  
**Status:** Intake complete; executable transaction work is blocked on cross-agent contracts and an owner-assigned task ID.  
**Related review:** [Issue #29 — package transaction approval and rollback boundary](https://github.com/otta-komban/TuskerOS/issues/29)

## 1. Verified current state

The baseline contains:
- A deterministic catalog resolver and dependency/ownership planning helpers.
- A non-executing transaction preview/approval-claim contract.
- A pure package transaction lifecycle validator and JSON Schema.
- A draft package transaction adapter contract.

The current lifecycle helper is structural only. Approval, snapshot and lock references are correlation evidence, not proof of external operations. The transaction preview's `claims_valid_unverified` result is not authorization. No trusted package-manager executor, durable transaction journal, broker authorization consumer, or verified rollback implementation is present in this baseline.

## 2. Dependency and approval gates

| Dependency | Current evidence | Required before execution |
|---|---|---|
| AEGIS-06 authorization | Issue #29 records acceptance of exact-plan/snapshot binding and a short-lived opaque `authorization_ref`; this is a security baseline, not runtime approval. | Typed trusted consume result, atomic one-time consumption, principal/session/device binding, expiry/revocation checks and durable pre-dispatch audit receipt. |
| NEXUS-07 broker | `system-integration/INTERFACE_CONTRACTS.md` is draft v0.2 and explicitly provisional. | Approved transport, authenticated peer identity, fixed handler and authorization handoff. |
| PHOENIX-10 package adapter | No accepted package transaction backend contract is available in the inspected baseline. | Supported package-manager backend, native lock semantics, authoritative installed-state source, execution result/read-back, interruption and recovery guarantees. |
| Chief Architect | `AGENT_TASKS.md` requires initial queues to be converted into assigned issue/task IDs. | Explicit task ID and approval for any shared trust or adapter contract changes. |

No FORGE implementation may invent an authorization issuer, trust root, signing envelope, broker API, package-manager lock, or rollback guarantee.

## 3. Delivery sequence

### Gate 0 — Contract and task assignment
- [ ] Obtain a Chief Architect task ID and acceptance scope.
- [ ] Obtain PHOENIX-10's supported package-manager adapter and recovery contract.
- [ ] Obtain NEXUS-07 acceptance of the broker transport/peer-authentication boundary.
- [ ] Map AEGIS-06's opaque authorization reference, consume result and audit receipt to an approved interface.
- [ ] Record compatibility/versioning and ownership decisions before changing shared contracts.

### Gate 1 — Isolated transaction adapter
- [ ] Implement only against the approved adapter interface.
- [ ] Use an isolated fixture repository and disposable test state; never mutate the host package database in unit tests.
- [ ] Bind the immutable ordered operation set, package identity/version/source, transaction ID and fresh installed-state snapshot.
- [ ] Require trusted authorization and durable pre-dispatch audit before dispatch.
- [ ] Enforce native locking, bounded execution, cancellation and idempotency/reconciliation.
- [ ] Verify package state by read-back; never infer commit from process exit status alone.

### Gate 2 — Failure and recovery conformance
- [ ] Test denial, expiry, replay, revocation, scope mismatch and altered plan/snapshot.
- [ ] Test dependency conflict/cycle, downgrade, source substitution and package identity mismatch.
- [ ] Test lock contention/timeout, cancellation, partial application and process interruption.
- [ ] Test recovery and rollback only where the selected backend supports them; report partial or unknown outcomes truthfully.
- [ ] Test durable audit failure and ensure it blocks dispatch/terminal success according to the approved AEGIS policy.
- [ ] Test concurrent requests and duplicate transaction IDs.

### Gate 3 — Trust and release integration
- [ ] Implement signed catalog metadata verification only against an approved publisher trust-root/key lifecycle contract.
- [ ] Reject unsigned, invalid, revoked, ambiguous or incompatible metadata by default.
- [ ] Integrate install/update/remove with the approved broker and audit path.
- [ ] Produce exact-SHA CI evidence and a focused PR for integrator review.

## 4. Security invariants

- Default deny; metadata, display flags and caller-supplied claims never confer trust.
- No package-manager side effect without fresh authorization for the exact immutable operation set and current installed-state snapshot.
- A changed package, version, source, principal, policy/registry version or precondition invalidates authorization.
- A consumed authorization reference cannot dispatch a second transaction.
- A disconnect after dispatch is an unknown outcome requiring read-back reconciliation, not blind retry.
- Rollback is a separate compensating operation; report success only after restoration is verified.
- No secrets, bearer references or sensitive command output in logs.

## 5. Current blocker and next action

**Blocker:** PHOENIX-10 has not yet supplied the concrete package-manager transaction/lock/recovery guarantees required to implement the adapter. NEXUS broker transport remains provisional, and the Chief Architect task ID is not present in the inspected task plan.

**Next action:** obtain the missing owner decisions and task assignment through Issue #29 / the coordinator. Until then, continue only with read-only audits and isolated, non-privileged tests that do not assume an unapproved interface.

## 6. Verification record

- Branch existence: verified, `09-FORGE`.
- Branch comparison: `main...09-FORGE` = 0 ahead / 0 behind.
- Baseline SHA: `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`.
- Files reviewed: `AGENTS.md`, agent operating rules, role guide, launch manifest, logging policy, transaction lifecycle helper/schema/tests, adapter contract and NEXUS interface proposal.
- Tests run in this intake: none. Existing tests are not represented as passing by this plan.
- Code/schema changes: none.
