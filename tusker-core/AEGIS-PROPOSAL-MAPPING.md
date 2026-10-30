# Core-to-AEGIS Action Proposal Mapping

**Owner:** TUSKER-04  
**Branch:** `04-tusker-core`  
**Status:** Provisional adapter mapping against AEGIS schema package draft v0.1.0  
**Reviewed:** 2026-10-31

## Purpose

Define how Core's planned operation becomes an AEGIS action proposal without making Core a policy engine. AEGIS owns policy evaluation, canonicalization, principal binding, approval state, authorization references and audit. NEXUS/broker owns independent peer authentication and execution-time authorization consumption. This document maps known fields only; it does not define an unapproved transport API.

## Field mapping

| AEGIS proposal field | Core source / construction | Adapter rule |
|---|---|---|
| `schema_version` | Pinned AEGIS proposal schema version | Emit exactly the negotiated schema version; current reviewed package is draft `0.1.0`. |
| `action_id` | Registered operation's AEGIS action mapping | Resolve from reviewed immutable operation registration; never accept model-supplied action IDs. |
| `proposal_id` | New UUID for each policy evaluation proposal | Generate once per immutable proposal; a changed proposal or retry requires a new proposal/evaluation. |
| `task_id`, `step_id` | Core Task/Step IDs | Preserve UUID producer rule; treat values as opaque strings at adapters. |
| `arguments` | Validated operation arguments | Validate against registered input schema; bind exact canonical values. Do not include secrets unless operation schema explicitly requires them. |
| `resources` | Resource set resolved from validated arguments and trusted system state | Canonical resource identifiers and access modes; never trust planner-supplied resource claims without resolution. |
| `idempotency_key` | Core invocation idempotency scope/key | Required for every mutation; may be omitted only for registered non-mutating operations. Reuse same key only for reconciliation of the same logical execution. |
| `requested_at` | Trusted Core wall-clock timestamp | RFC 3339 date-time; not used as proof of identity or authorization. |

## Trust and canonicalization

- Principal, authenticated session/device binding and origin are trusted transport/evaluation context, not fields in the proposal body.
- Core must not compute or substitute a policy decision. AEGIS canonicalizes the proposal using RFC 8785 JSON Canonicalization Scheme (JCS) and SHA-256, then returns the action digest and principal binding as decision evidence.
- Core retains the returned `decision_id`, `proposal_id`, `action_digest`, `principal_binding`, `policy_version`, `evaluated_at`, `expires_at`, `approval_request_id`, opaque `authorization_ref` and audit references as step evidence where provided.
- All registered actions, including reads, pass through AEGIS policy. A read-only auto-ALLOW is still an explicit AEGIS decision.
- Descriptor risk/privilege labels, planner confidence and model-generated explanations are inputs for review only; none grant permission.

## Decision handling

| AEGIS decision | Core behavior | Executor dispatch |
|---|---|---|
| `DENY` | Record terminal denial reason and evidence; do not retry the same proposal | Zero calls |
| `REQUIRE_APPROVAL` | Pause at approval-required state; wait for authenticated AEGIS approval workflow; do not infer permission from UI action | Zero calls |
| `ALLOW` | Validate non-null unexpired expiry and opaque authorization reference; require exact proposal/digest/principal/session/operation/resource binding | Still blocked until NEXUS/broker independently validates and atomically consumes authorization |

An ALLOW is not a reusable bearer permission. It is rejected if missing, expired, mismatched, revoked, replayed or otherwise indeterminate. Policy or authorization authority outage fails closed.

## Execution and recovery boundary

AEGIS broker requirements state that the broker authenticates the IPC peer independently, validates fixed operation and canonical resources, and asks the authorization authority to atomically transition an APPROVED request to CONSUMED using a linearizable compare-and-set. The authority records a unique consumption ID before returning a narrowly scoped grant. Concurrent/replayed attempts must not both succeed. If a consume response is lost, the broker reconciles by consumption ID and operation idempotency key; it must not assume the reference was unused.

Core therefore treats these as separate milestones:

1. Policy proposal evaluated.
2. Decision recorded.
3. Approval completed, if required.
4. Authorization consumed by trusted broker.
5. Handler dispatched and execution durably recorded.
6. Result/postcondition reconciled.

A timeout or disconnect after a possible consume/dispatch is `unknown_outcome`, not failure or cancellation. Core must query/reconcile existing execution state before retrying. Mutation idempotency is scoped to the registered operation and key and must survive broker restart.

## Decisions still required before implementation

- AEGIS + NEXUS: exact versioned consume API request/response, including authorization reference, operation/audience, canonical resource binding, peer/session binding, proposal/decision correlation, consumption ID and typed rejection/outage outcomes.
- NEXUS: trusted IPC peer identity injection into the broker boundary; durable execution ID and idempotency record schema; exact lost-response reconciliation API and typed result mapping.

## Evidence and implementation gate

Reviewed AEGIS artifacts: `security/schemas/action-proposal.schema.json`, `security/schemas/policy-decision.schema.json`, `security/AUTHORIZATION_LIFECYCLE.md`, and `security/BROKER_CONTRACT.md` on `06-security-gatekeeper`.

This mapping is design evidence only. No transport adapter, broker call, durable execution store or integration test is implemented or claimed by this document.


## Owner decision update — AEGIS issue #16

AEGIS-06 closed the approval-handoff and consume-outcome semantics in [issue comment 6533203333](https://github.com/otta-komban/TuskerOS/issues/16#issuecomment-6533203333):

- `REQUIRE_APPROVAL` carries an `approval_request_id` and null `authorization_ref`; it never authorizes dispatch.
- After authenticated approval, AEGIS re-evaluates the exact proposal and current security bindings. Only a still-valid proposal receives a fresh `ALLOW` and new opaque `authorization_ref`; changed bindings invalidate the request.
- The broker consumes only that fresh `authorization_ref`, never `approval_request_id`. Earlier unconsumed references are invalidated on re-issue.
- Typed consume outcomes are `CONSUMED`, `NOT_APPROVED`, `DENIED`, `EXPIRED`, `REVOKED`, `INVALIDATED`, `ALREADY_CONSUMED`, `BINDING_MISMATCH`, `CALLER_UNAUTHORIZED`, `AUTHORITY_UNAVAILABLE`, `IDENTITY_UNAVAILABLE`, `CLOCK_UNCERTAIN`, `AUDIT_UNAVAILABLE`, and `CONSUME_OUTCOME_UNKNOWN`.
- Only `CONSUMED` returns a narrow grant. All other outcomes mean zero new handler calls; already-consumed and unknown outcomes require reconciliation.
- Required pre-dispatch audit and consume state are durably committed before grant. Required audit failure returns `AUDIT_UNAVAILABLE` with no grant or dispatch.

The approval handoff and semantic outcome taxonomy are therefore no longer open AEGIS questions. NEXUS still owns the missing strict transport/context shape, peer authentication injection, atomic consume API, durable execution identity and restart-safe reconciliation. The above does not freeze a wire protocol or imply implementation.
