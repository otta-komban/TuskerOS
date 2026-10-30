# Core Authorization Adapter — Decision Record

**Owner:** TUSKER-04 (orchestration adapter)  
**Related owners:** AEGIS-06 (policy/authorization authority), NEXUS-07 (tool provider and broker transport)  
**Status:** Provisional integration design; no transport, signing format, or runtime implementation is approved by this note.  
**Branch:** `04-tusker-core`

## 1. Purpose and non-goals

Define the security-preserving handoff between Core task execution, AEGIS policy, and NEXUS tool/broker execution using the current owner-authored draft contracts. This record does not invent an AEGIS principal schema, authorization token format, IPC method, broker API, or service name.

Core is an untrusted proposal producer relative to the policy and privileged-execution boundaries. Core owns task/plan/step lifecycle and scheduling. AEGIS alone decides authorization and owns approval, authorization-reference lifecycle, and audit semantics. NEXUS owns the tool catalogue, provider operation lifecycle, and broker/tool transport. The broker independently authenticates its IPC peer and validates authorization immediately before dispatch.

## 2. Canonical operation mapping

For each executable Core step, the adapter MUST resolve one reviewed registry mapping:

- Core `operation_id` -> NEXUS descriptor `name` -> AEGIS registered `action_id` -> fixed broker `broker_operation_id`.
- The mapping is explicit and versioned; no layer derives an executable or privileged operation from free-form model text.
- Core validates input against the NEXUS descriptor input schema and derives the canonical resource set from validated arguments and the registered operation definition.
- Descriptor risk/privilege metadata is advisory registry input, not permission. AEGIS evaluates every registered operation, including reads.
- Any change to arguments, resources, resolved target identity, principal/session, operation registration, policy/registry version, or security-relevant preconditions requires a new proposal and fresh policy evaluation.

## 3. Required sequence

1. **Trusted ingress:** The local/remote adapter establishes principal, origin, session/device and peer context from authenticated transport. Caller JSON, model output, `caller.component`, and `caller.instance_id` are never identity evidence.
2. **Proposal:** Core creates the AEGIS-owned proposal envelope using `action_id`, `proposal_id`, `task_id`, `step_id`, validated `arguments`, canonical `resources`, `requested_at`, and a non-empty `idempotency_key` for every mutation. Trusted principal/session context is conveyed out-of-band through the AEGIS-approved transport, not asserted in the proposal body.
3. **Policy:** AEGIS evaluates the proposal and trusted context. Core checks the returned decision against the exact pending proposal, action digest, principal binding, policy version and expiry. Core does not calculate a competing policy decision or manufacture an authorization reference.
4. **Decision gate:**
   - `DENY`: record the decision/audit references; zero NEXUS executor or broker calls.
   - `REQUIRE_APPROVAL`: move the task to `awaiting_approval`; zero executor calls. UI acceptance is not authorization. Resume only through the AEGIS-defined approved/consumption flow and fresh binding checks.
   - `ALLOW`: proceed only when expiry is present and in the future, authorization_ref is non-empty, and proposal/action digest, trusted principal/session, operation/resource scope and policy version match. Any missing, stale, replayed, revoked or mismatched field fails closed with zero dispatch.
5. **Tool handoff:** Core passes the AEGIS-issued opaque authorization context/reference to NEXUS through the final AEGIS/NEXUS-approved adapter shape. It is not accepted from a client or model. NEXUS/broker independently authenticates its IPC peer, resolves the fixed operation, validates arguments and scope, and asks the AEGIS authority to atomically consume the authorization reference.
6. **Atomic consume:** The authority/broker contract must enforce one-time consumption with a durable atomic compare-and-set/transaction. Read-then-write and process-local flags are insufficient. The consumed grant is narrowly scoped to the fixed operation, exact resource scope and authenticated principal/session.
7. **Dispatch and result:** Only after successful consumption and immediate precondition checks may the fixed handler run. Preserve request/task/step/correlation identifiers, operation identity, idempotency reference, postcondition state and audit evidence in the result.
8. **Uncertain outcome:** A lost consume/dispatch response, timeout or disconnect is not proof that no side effect occurred. Preserve `unknown_outcome`; reconcile by consumption/execution identity and operation idempotency key before any retry. Never blindly replay an authorization reference.

## 4. Core state mapping

| Condition | Core behavior | Executor calls |
|---|---|---:|
| AEGIS DENY | Block step; expose safe denial reason and evidence | 0 |
| AEGIS REQUIRE_APPROVAL | Await AEGIS approval lifecycle; UI decision alone cannot resume execution | 0 |
| AEGIS unavailable, malformed decision, missing identity/audit, or invalid ALLOW | Fail closed; retain typed reason; do not dispatch | 0 |
| ALLOW expired, revoked, replayed, or binding mismatch | Reject authorization; obtain a fresh evaluation only after revalidating proposal/context | 0 |
| Atomic consume says already consumed | Do not dispatch again; reconcile the original execution | 0 new calls |
| Dispatch timeout/disconnect after possible side effect | Mark outcome unknown and reconcile | No blind retry |
| Verified success and required postconditions | Complete the step with evidence | As authorized |

A cancellation request, broker stop acknowledgement, compensation, rollback and verified postcondition are distinct facts. Cancellation does not revoke or roll back a side effect by itself.

## 5. Contract gaps requiring owner decisions

### NEXUS-07
1. Publish the exact strict invocation `authorization_context` shape and explain how it carries the AEGIS opaque reference without accepting caller-supplied identity/decision fields.
2. Confirm the NEXUS-to-AEGIS consume operation: fields sent (fixed broker operation ID, canonical resource scope, request/correlation IDs, authenticated peer context), response/grant shape, and error taxonomy.
3. Define the atomic consume boundary, durable consume/execution IDs, concurrent replay behavior, and lost-response reconciliation protocol.
4. Confirm whether tool invocation itself is strictly post-consumption or whether the broker performs consumption internally immediately before handler dispatch. The latter is preferred for privileged operations.
5. Confirm operation mapping and idempotency key scope for mutations, including persistence/reconciliation across restart.

### AEGIS-06
1. Confirm the trusted principal/session context transport and exact binding verification interface; Core will not invent its shape.
2. Confirm the approval-to-consumption path: whether approval transitions to a newly issued ALLOW/reference or an approved reference is consumed directly by the broker, and how Core observes that state.
3. Define typed outcomes for unavailable authority, invalid/replayed reference, already-consumed reference, expiry, revocation, invalidation, and audit failure.
4. Confirm whether audit availability is a hard precondition for each risk class and how audit references are returned without exposing bearer material.

### TUSKER-04 commitments
- Never dispatch on DENY or REQUIRE_APPROVAL.
- Never accept caller/model-supplied principal, origin, risk, policy decision, or authorization reference.
- Never treat descriptor metadata or a NEXUS `needs_approval` result as AEGIS permission.
- Never persist/log raw authorization bearer material or secret arguments.
- Never blindly retry an uncertain mutation.
- Keep the task lifecycle authoritative in Core; authorization and broker lifecycle remain AEGIS/NEXUS-owned.

## 6. Evidence and status

Reviewed owner-authored drafts:
- `security/schemas/action-proposal.schema.json` and `security/schemas/policy-decision.schema.json` (AEGIS-06, draft v0.1.0).
- `security/AUTHORIZATION_LIFECYCLE.md` and `security/BROKER_CONTRACT.md` (AEGIS-06 requirements; runtime/persistence implementation pending NEXUS-07).
- `system-integration/contracts/tool-invocation.schema.json`, `tool-result.schema.json`, `tool-descriptor.schema.json`, and `system-integration/INTERFACE_CONTRACTS.md` (NEXUS-07, provisional draft v0.2).

This is a design reconciliation only. No transport adapter, policy client, broker consume call, executor, integration test, or CI pass is claimed.


## 7. AEGIS-06 approval and consume semantics — owner-confirmed

AEGIS-06 answered the approval-handoff and typed-outcome questions in issue #16 (comment [6533203333](https://github.com/otta-komban/TuskerOS/issues/16#issuecomment-6533203333)). The following are now confirmed semantic requirements; they do not define a transport or wire schema:

1. Initial policy evaluation that requires approval returns `REQUIRE_APPROVAL`, a non-null `approval_request_id`, and null `authorization_ref`. This state is non-authorizing.
2. An authenticated eligible approver may transition the request from `PENDING` to `APPROVED`. AEGIS then re-evaluates the exact proposal against current principal/session, operation, canonical arguments/resources, policy and registry versions, preconditions, expiry and relevant security posture.
3. If all bindings remain valid, AEGIS issues a fresh `ALLOW` with a new opaque `authorization_ref` and short expiry. If a material binding changed, the request is `INVALIDATED` and no ALLOW is issued.
4. The broker MUST NOT consume `approval_request_id`; it is a correlation/lookup identifier, not a bearer capability. It consumes only the fresh `authorization_ref`. Issuing the fresh reference invalidates any earlier unconsumed reference for that request; consumed references are never reissued and terminal approval requests are not reopened.
5. The consume result taxonomy is: `CONSUMED` (unique `consumption_id` plus narrow grant), `NOT_APPROVED`, `DENIED`, `EXPIRED`, `REVOKED`, `INVALIDATED`, `ALREADY_CONSUMED`, `BINDING_MISMATCH`, `CALLER_UNAUTHORIZED`, `AUTHORITY_UNAVAILABLE`, `IDENTITY_UNAVAILABLE`, `CLOCK_UNCERTAIN`, `AUDIT_UNAVAILABLE`, and `CONSUME_OUTCOME_UNKNOWN`.
6. Every outcome except `CONSUMED` returns no grant and permits zero new handler calls. `ALREADY_CONSUMED` and `CONSUME_OUTCOME_UNKNOWN` require reconciliation, never blind retry.
7. Required pre-dispatch audit evidence and one-time consume state must be durably committed before the authority returns `CONSUMED`/grant. If required audit cannot be committed, return `AUDIT_UNAVAILABLE`, do not commit consumption, and issue no grant. The broker must also persist dispatch intent and required dispatch-start audit before invoking a handler. A disconnect after possible dispatch remains UNKNOWN and is reconciled using the same consumption/execution identity and operation idempotency key.

### Updated Core handling

| Owner outcome | Core adapter behavior | New handler calls |
|---|---|---:|
| Fresh ALLOW after approved request | Validate exact original proposal and current trusted bindings; pass only the new opaque authorization reference to the approved NEXUS/broker boundary | Still blocked until broker consume succeeds |
| NOT_APPROVED / DENIED / EXPIRED / REVOKED / INVALIDATED / BINDING_MISMATCH / CALLER_UNAUTHORIZED / IDENTITY_UNAVAILABLE / CLOCK_UNCERTAIN / AUTHORITY_UNAVAILABLE / AUDIT_UNAVAILABLE | Fail closed; retain safe typed outcome; do not dispatch | 0 |
| ALREADY_CONSUMED | Reconcile the original consumption/execution; never replay the reference | 0 new calls |
| CONSUME_OUTCOME_UNKNOWN | Query/reconcile by the original consumption/execution identity and idempotency key; do not infer unused | 0 new calls until resolved |
| CONSUMED | Continue only with the narrow grant and the broker's persisted dispatch-intent/audit gate | At most the single authorized execution |

**Still open:** NEXUS-07 must publish the strict authorization context, trusted peer injection, atomic consume request/response, typed transport errors, durable consumption/execution identity, and restart-safe reconciliation contract. No runtime implementation or executable conformance test is claimed.
