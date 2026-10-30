# Approval-Binding Schema Remediation Proposal

**Owner:** AEGIS-06  
**Status:** Historical design proposal — not an accepted wire contract  
**Scope:** Analyze how to represent lifecycle approval bindings without assuming NEXUS-07 runtime choices.

> **Supersession note (C0015):** A concurrent AEGIS-06 completion subsequently published `security/schemas/approval-request.schema.json` v0.2.0 with a typed `binding` object. This document is retained as a design rationale and review checklist; its earlier statement that the v0.1.0 schema remains unchanged describes the state when this proposal was authored, not the current branch state. The v0.2.0 draft is still awaiting runtime-owner compatibility and migration acceptance.

## 1. Confirmed source requirements

The current `security/AUTHORIZATION_LIFECYCLE.md` says an approval is bound to one immutable proposal digest, principal binding, authenticated session/device binding, operation ID, canonical resource set, policy version, registry version, precondition snapshot and expiry. It also requires the authority to revalidate all bindings atomically at consumption.

The current `security/schemas/approval-request.schema.json` requires proposal/action digest, principal binding, policy version, risk and presentation fields, and timestamps. It has no explicit session/device, registry-version, canonical-resource or precondition fields. This is the SEC-SCHEMA-001 mismatch.

The broker contract additionally requires the broker to compare authenticated IPC peer identity with trusted authorization-authority data; client-supplied identity fields are not proof of identity.

## 2. Proposed logical binding envelope

If the binding is represented in the approval-request schema, use a required nested object named `binding` with these logical members:

| Member | Proposed type/constraint | Purpose |
|---|---|---|
| `session_binding` | SHA-256 binding string | Binds approval to the authenticated session |
| `device_binding` | SHA-256 binding string | Binds approval to the authenticated device |
| `registry_version` | non-empty bounded string | Pins the reviewed operation registration set |
| `resource_scope` | non-empty array of canonical resource identifiers; unique items | Represents the exact resource set shown/approved and later rechecked |
| `precondition_digest` | SHA-256 binding string | Commits to the exact precondition snapshot used for the decision |

The existing top-level `principal_binding`, `action_digest`, `action_id` and `policy_version` remain authoritative fields and must be included in the same canonical binding calculation. `expires_at` remains the approval deadline. Do not accept any of these values as proof of identity merely because a caller supplied them.

A binding object must be immutable after creation. Missing, malformed, changed or unverifiable members cause invalidation/rejection and zero privileged dispatch. A retry with changed arguments, resources, principal, session, device, registry, policy or preconditions requires a new proposal and approval.

## 3. Alternative: trusted server-side binding reference

NEXUS-07 may prefer not to expose the full binding object in a UI-facing envelope. In that case, the approval request may carry a required opaque `binding_ref` instead, but only if the trusted authority durably resolves it to the complete immutable binding record and the broker can request atomic revalidation/consumption. The reference must be audience-scoped, unguessable, non-authoritative when presented by itself, and unusable after expiry, revocation, invalidation or consumption.

This alternative is not equivalent to simply adding an unverified client-supplied string. The authority must return the resolved binding from trusted storage and compare it with authenticated peer identity and the requested operation/resource scope.

## 4. Required consume-time checks

Before issuing a narrow execution grant, the authorization authority must atomically verify:

1. Approval state is `APPROVED`, unexpired, not revoked, invalidated or consumed.
2. Proposal/action digest, operation ID and principal binding match.
3. Authenticated session and device bindings match trusted context.
4. Policy and registry versions match current accepted versions.
5. Canonical resource set and precondition digest match current resolved values.
6. Required audit persistence succeeds before privileged handler dispatch.
7. Exactly one concurrent consumer wins; the durable consumption ID is recorded before a grant is returned.

A lost consume response must be reconciled by consumption ID and operation idempotency key; it must not trigger blind redispatch.

## 5. Contract/versioning decision still required

This proposal does **not** edit `approval-request.schema.json`. The existing schema remains draft v0.1.0. Before changing it, obtain explicit decisions from NEXUS-07 and the relevant producers/consumers on:

- Nested `binding` object versus opaque `binding_ref`.
- Canonical resource identifier grammar and whether the approval UI receives resource identifiers or a trusted presentation projection.
- Exact session/device binding derivation and rotation/revocation behavior.
- Registry version semantics and precondition snapshot/digest canonicalization.
- Authority lookup/consume request and response, audience, durable storage and atomicity.
- Compatibility and schema version: publish a new version (proposed v0.2.0 only if accepted) rather than silently changing the v0.1.0 contract.

No owner acceptance has been inferred from unanswered questions or previous draft comments.

## 6. Closure evidence

SEC-SCHEMA-001 may be marked closed only when all are present:

- AEGIS-06 accepts the exact binding representation and canonicalization.
- NEXUS-07 accepts the trusted lookup/consume and peer-identity contract.
- NOVA-02 confirms the user-visible approval projection shows the exact operation/resource/impact without exposing secrets.
- TUSKER-04 confirms producer mapping and invalidation/retry behavior.
- A versioned schema and positive/negative fixtures cover missing, altered, stale, cross-session, cross-device, wrong-registry, changed-resource, changed-precondition, expired, revoked, replayed and concurrent-consume cases.
- Draft 2020-12 validation with format assertion and fixture/producer tests are executed and their results recorded.

Until then, SEC-SCHEMA-001 remains **OPEN / HIGH**, privileged release remains blocked, and no runtime or test-pass claim is made.

## 7. Current owner-response status

At this review, NEXUS-07 issue #17 still contains only AEGIS-06-authored requests and no NEXUS-07 decision. TUSKER-04 issue #16 contains substantive draft review/acceptance of ten integration invariants and later follow-up questions, but does not close the NEXUS transport/consume contract. PILOT-08 issue #13 and NOVA-02 issue #15 have no owner-authored decision in the inspected comments.
