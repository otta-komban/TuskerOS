# Privileged Broker Security Contract

**Owner:** AEGIS-06 security requirements; NEXUS-07 implementation contract pending  
**Version:** 0.1.0-draft

## Security boundary

The broker is a narrow privileged executor, not a general-purpose shell, RPC trampoline or policy engine. It independently authenticates its caller and independently verifies authorization immediately before every privileged operation. Core, model output, approval UI and extension code are untrusted request producers.

## Request envelope

A broker request contains only protocol version, fixed registered broker_operation_id, opaque authorization_ref, proposal/decision correlation IDs, canonical resource identifiers, bounded operation arguments, and a mutation idempotency key where the registration requires one.

The caller cannot provide a principal identity as authority, select an executable, choose a policy result, override limits or set an approval flag. The broker obtains caller identity from authenticated IPC peer credentials and compares it with the principal/session binding returned by the authorization authority.

## Mandatory broker checks

1. Authenticate IPC peer (for local Linux IPC, use kernel-provided peer credentials and a protected socket/service boundary); remote callers must arrive through the authenticated remote adapter, never directly impersonate local peers.
2. Resolve operation ID against the broker's own immutable allowlist and verify it maps to a compiled/packaged handler.
3. Resolve the authorization reference through the trusted authority; do not trust caller-supplied decision JSON or unsigned booleans.
4. Verify audience, exact operation, action digest, canonical resources, principal/session binding, policy/registry version, expiry, revocation and one-time consumption.
5. Validate arguments again against the operation-specific schema and enforce hard-coded broker-side bounds.
6. Recheck security-sensitive preconditions immediately before dispatch.
7. Execute only the fixed handler with least privilege and bounded timeout/resources.
8. Verify postconditions independently and emit correlated audit evidence.
9. Return a typed result; never leak credentials or unrestricted privileged output.

Any failed or indeterminate check returns a typed rejection and performs zero privileged side effects.

## Execution constraints

- No arbitrary shell, command string, dynamic module path, plugin-provided executable, or generic root API.
- Prefer one operation per broker method with explicit typed arguments and fixed resource scope.
- Run the broker under a dedicated service identity; use narrowly scoped OS capabilities/polkit rules/SELinux policy where appropriate, not unrestricted root delegation.
- Separate read and mutation handlers. Deny unregistered operations by default.
- Enforce per-operation timeout, input/output size, concurrency and rate limits.
- Treat symlink traversal, path replacement, TOCTOU, mount changes and namespace confusion as explicit threat cases; use directory/file descriptors and safe kernel APIs where feasible.
- Cancellation is best effort and must be acknowledged. Compensation/rollback is a separate authorized operation.

## Result and unknown-outcome contract

Broker results distinguish SUCCEEDED, REJECTED, FAILED, CANCELLED and UNKNOWN. A timeout or transport disconnect after dispatch is UNKNOWN, not proof of failure or cancellation. Return operation ID, correlation ID, idempotency key hash/reference, execution ID, timestamps, postcondition status and audit reference.

For a mutating operation, persist a durable execution record keyed by operation + idempotency key before dispatch. Repeated requests with the same key return/reconcile the existing execution; they do not blindly repeat side effects. If the broker cannot establish whether a side effect occurred, it returns UNKNOWN and requires state reconciliation or a separately authorized recovery action.

## Required tests from NEXUS-07

- Positive: a registered low-risk read with matching authenticated peer and valid authorization executes exactly once and produces a verified typed result.
- Negative: a denied/expired/replayed authorization, wrong peer, mismatched operation/resource or unknown operation produces zero handler calls.
- Concurrency: two simultaneous consumes of one authorization yield at most one dispatch.
- Failure: crash/disconnect after dispatch produces UNKNOWN and safe reconciliation, not blind retry.
- Isolation: direct socket access by an untrusted process and caller-selected operation IDs are rejected.
- Audit: unavailable required audit path blocks sensitive operations; audit contains no secret material.

This contract is draft until NEXUS-07 confirms transport, identity and implementation constraints. No privileged execution is authorized by this document alone.


## Approval handoff adapter outcomes (AEGIS-06 C0013)

The broker accepts only the fresh opaque `authorization_ref` returned with a post-approval `ALLOW`. It MUST NOT accept `approval_request_id` as a consume credential. The approval request ID is retained only for correlation and reconciliation.

The authorization adapter's typed outcomes and mandatory zero-grant behavior are defined in `security/AUTHORIZATION_LIFECYCLE.md` ("Canonical consume outcomes"). In particular:
- `CONSUMED` returns a unique consumption ID and narrow grant only after the authority has durably committed the one-time state transition and required pre-dispatch audit evidence.
- `ALREADY_CONSUMED` never triggers a second dispatch; reconcile the existing consumption/execution.
- `CONSUME_OUTCOME_UNKNOWN` never authorizes dispatch or blind retry; reconcile using the request correlation, consumption ID when known, and operation idempotency key.
- `AUDIT_UNAVAILABLE`, identity/time/authority failures and every mismatch return no grant and cause zero handler calls.
- Broker dispatch follows its own durable dispatch-intent record and required dispatch-start audit. A failure before that boundary is zero handler calls; a disconnect after possible dispatch is `UNKNOWN`.

The fresh-ALLOW handoff and typed outcomes are AEGIS-owned semantic clarifications. NEXUS-07 must still confirm the transport/API shape, durable transaction primitive, authenticated peer injection and runtime implementation before this draft can be frozen.
