# Package Transaction Adapter Contract

**Owner:** FORGE-09 (contract proposal)  
**Status:** Draft; implementation is blocked on AEGIS-06 and PHOENIX-10 decisions.  
**Scope:** Define the narrow boundary between the marketplace transaction planner and a trusted platform package adapter. This document does not implement an adapter or authorize package changes.

## Trust and ownership boundaries

| Responsibility | Owner | Required behavior |
|---|---|---|
| Publisher/catalog/artifact trust, permission policy and approval-token authentication | AEGIS-06 / trusted policy service | Authenticate issuer and actor, enforce authority and action scope, expiry, replay/revocation and policy |
| Package manager selection, lock, execution, interruption handling and rollback | PHOENIX-10 / platform adapter | Use supported Fedora package-manager transactions; report actual outcomes |
| Preview, dependency/ownership planning and lifecycle record validation | FORGE-09 | Produce deterministic plans and reject malformed or stale contract data |
| Durable audit storage and access policy | AEGIS-06 with platform integration | Append-only, access-controlled, retained and tamper-evident records |

A value such as `claims_valid_unverified`, an approval reference, lock reference or result reference is correlation metadata only. It is never proof that the referenced operation happened. The adapter must independently authenticate and enforce all trust decisions.

## Required operation sequence

1. **Prepare:** FORGE-09 supplies an immutable preview containing transaction ID, exact ordered package operations, plan digest and installed-state snapshot digest. The preview is informational and has no execution authority.
2. **Authenticate and authorize:** AEGIS-06 validates the approval token cryptographically and checks actor, policy authority, expiry, replay/revocation, exact plan/snapshot/operation digests and action coverage. Failure is terminal and must not reach the package manager.
3. **Revalidate:** The adapter reads authoritative installed state immediately before acquiring the package-manager transaction lock. Any mismatch invalidates the preview; a new preview and approval are required.
4. **Lock and execute:** PHOENIX-10 acquires the package-manager-native lock, rechecks the state/plan binding under the lock where the package manager permits it, then applies only the approved operations. It must not silently add, substitute or upgrade packages outside the reviewed operation set.
5. **Verify outcome:** The adapter reads back installed state and compares it with the intended result. Only verified completion may be reported as committed.
6. **Recover:** On partial application or interruption, use package-manager-supported rollback/recovery where available. Report `rolled_back` only after verifying restoration; otherwise report `rollback_failed` or an explicit partial outcome. Never claim atomicity where the backend cannot guarantee it.
7. **Audit:** Persist a durable event for preparation, authorization decision, revalidation, execution start, terminal result and recovery. Do not store credentials, approval tokens, arbitrary exception text or secret-bearing command output.

## Adapter interface (language-neutral)

The future adapter must expose equivalent operations; names are illustrative, not a mandated ABI:

- `inspect_snapshot() -> Snapshot`: return a normalized, authoritative installed-package/ownership snapshot and its digest.
- `verify_approval(preview, token) -> VerifiedApproval | Rejection`: delegate cryptographic authentication and policy checks to AEGIS-06; return a stable verification reference and actor/authority identity only after success.
- `acquire_transaction_lock(transaction_id) -> LockHandle`: acquire the native package-manager lock with bounded waiting and cancellation; return an opaque correlation reference.
- `apply(approved_operations, lock_handle) -> ExecutionResult`: execute only the reviewed operation set and return package-manager transaction identity plus actual per-package outcomes.
- `inspect_result(expected, execution_result) -> VerifiedOutcome`: verify resulting installed state rather than trusting process exit status alone.
- `recover(execution_result) -> RecoveryResult`: attempt supported recovery and independently verify restored state.
- `append_audit(event) -> AuditReceipt`: persist an allow-listed event durably before reporting a terminal result.

All calls must be bound to one transaction ID and immutable plan digest. Lock handles are opaque, short-lived and never treated as authorization. The adapter must release locks on every exit path. Repeated requests with the same transaction ID must be idempotent or rejected as replay; they must never apply package operations twice.

## Failure and interruption requirements

- Authorization rejection, invalid signature, expired/revoked/replayed approval or scope mismatch: do not acquire a package lock or execute.
- Snapshot mismatch: mark stale; require a newly reviewed preview and approval.
- Lock timeout/cancellation: no package changes; record a non-execution outcome.
- Package manager failure before changes: report failure without claiming rollback.
- Partial changes: inspect actual state, attempt supported recovery, verify it, and expose residual changes if recovery is incomplete.
- Process crash: recover from durable transaction/audit identifiers and authoritative package-manager state; never infer success from a missing process.
- Audit persistence failure: do not report a successful terminal result unless the approved policy defines and documents a secure degraded mode. This policy requires AEGIS-06 sign-off.

## Required conformance tests before implementation approval

1. Invalid, expired, replayed, revoked and wrong-scope approval never reaches execution.
2. Any plan, operation or snapshot digest change invalidates approval.
3. Concurrent transactions cannot bypass the native package-manager lock.
4. Lock timeout and cancellation leave package state unchanged.
5. The adapter cannot add operations beyond the approved list.
6. Exit code success with an unexpected installed state is not committed.
7. Failure at every package operation boundary yields truthful partial/recovery reporting.
8. Crash/restart does not duplicate operations or lose transaction identity.
9. Rollback is reported successful only after restored state is verified.
10. Audit records are durable, append-only, allow-listed and correlated to the same transaction.
11. All package-manager operations are limited to configured repositories and package identities.
12. Shared ownership and retained dependency protections from the FORGE-09 removal planner are enforced at execution time against a fresh snapshot.

## Open decisions

Implementation remains blocked pending:
- **AEGIS-06:** token format/issuer, signature and trust-root API, actor identity, authority model, replay/revocation storage, consent semantics, audit receipt and degraded-audit policy.
- **PHOENIX-10:** supported package-manager backends, transaction/lock APIs, atomicity guarantees, installed-state source, interrupted-transaction recovery and rollback guarantees.
- **Joint:** exact adapter method signatures, error taxonomy, transaction ID lifetime/idempotency store, ownership persistence and conformance-test ownership.

Until those decisions are recorded, FORGE-09 must not add a fake executor, invoke DNF/Flatpak, or imply the transaction lifecycle is production-ready.
