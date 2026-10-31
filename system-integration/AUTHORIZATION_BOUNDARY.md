# NEXUS-07 Authorization Boundary

**Owner:** NEXUS-07 for provider-side enforcement and integration; AEGIS-06 owns authorization policy, principal semantics, broker and audit contract.
**Status:** Draft integration note; no AEGIS contract approval or policy schema is implied.

## Purpose
Define the NEXUS-side safety boundary without inventing AEGIS-owned principal, decision, policy, Polkit action or audit schemas. This document describes required sequencing and fail-closed behavior at the tool-provider boundary.

## Trust boundaries
1. **Transport identity:** the receiving IPC layer obtains caller identity from authenticated transport peer credentials. The caller component and instance fields in invocation JSON are descriptive routing metadata only; they cannot establish identity or authorization.
2. **Typed request validation:** resolve the requested canonical descriptor name, validate the descriptor and arguments against its declared input schema, and enforce the effective deadline before any provider is invoked.
3. **Authorization preflight:** obtain the AEGIS-owned policy decision for the registered action before provider execution. TUSKER-04's focused review states that AEGIS policy evaluates every registered action, including reads. Mutations additionally require mandatory preflight before invocation. NEXUS must not infer an allow decision from descriptor risk, privilege, capability availability, caller JSON, a prior task approval, or an earlier request's decision.
4. **Provider execution:** dispatch only after an explicit, current positive decision from the trusted AEGIS path. The provider receives only the operation and arguments it needs; it does not receive arbitrary caller claims as authority.
5. **Postcondition and audit:** report the operation result, observed side effects and postcondition evidence. AEGIS defines authoritative audit fields and retention semantics; NEXUS must not invent or duplicate them.

## Decision handling
| AEGIS outcome / condition | NEXUS provider behavior | Tool-facing behavior |
|---|---|---|
| Explicit positive authorization for this operation and trusted caller | Provider execution may proceed, subject to descriptor and precondition validation | Return normal operation lifecycle result |
| DENY | Do not call provider; do not perform the protected side effect | Return a stable permission-denied/rejected outcome |
| REQUIRE_APPROVAL | Do not call provider; do not perform the protected side effect | Return approval-required state to TUSKER orchestration |
| Missing, malformed, invalid, stale, unverifiable or unavailable authorization context/decision | Fail closed; do not call provider | Return a safe denied/unavailable error without leaking policy internals |
| Decision refers to a different operation, principal, resource or expired request context | Do not call provider | Reject and request a fresh policy evaluation |

The exact AEGIS decision vocabulary and mapping to stable NEXUS error codes must be confirmed by AEGIS-06. DENY and REQUIRE_APPROVAL above are the explicit stop conditions named in TUSKER-04's review, not a complete AEGIS enum proposal.

## Replay, scope and freshness
- A policy decision is bound to the specific authenticated principal, canonical operation, relevant resource/context and request lifetime as defined by AEGIS-06.
- Never treat an authorization_context blob as a bearer grant merely because it is present in JSON.
- Never reuse a previous decision for another request unless AEGIS explicitly defines a safe scoped/replayable decision token.
- Idempotency keys deduplicate operation execution; they are not authorization credentials.
- Task approval and user confirmation in the planner are not substitutes for AEGIS policy preflight.
- On timeout/disconnect after provider execution may have started, return unknown_outcome; authorization does not establish whether the side effect occurred. Reconcile state before retry.

## Schema status
The tool-invocation schema currently has an optional opaque authorization_context object because AEGIS-06 has not supplied the authoritative serialization and transport binding contract. This field is not an identity claim or grant. Do not make it required, define nested fields, or accept it from an untrusted caller until AEGIS-06 specifies whether the context is injected by the trusted broker, passed as an opaque reference, or conveyed out-of-band. Regardless of wire shape, the runtime MUST obtain and validate the authoritative decision through the AEGIS-owned path before provider execution.

## Review questions for AEGIS-06
1. What authenticated principal representation is authoritative, and which IPC credentials bind it to the request?
2. Is authorization context injected by the trusted broker, passed as an opaque reference, or conveyed out-of-band?
3. What decision states, freshness/expiry, resource binding and replay guarantees are authoritative?
4. How should DENY, approval-required, unavailable broker and invalid context map into NEXUS result/error states?
5. Which audit correlation fields must NEXUS propagate, and which audit records are written by AEGIS versus providers?
6. How are read-only registered actions evaluated, consistent with TUSKER-04's review that policy evaluates every registered action?

## Review record
- TUSKER-04 focused review comment 6531355859: AEGIS is authoritative for principal, decision and authorization evidence; authorization_context is opaque trusted context; policy evaluates every registered action including reads; no executor call after DENY or REQUIRE_APPROVAL.
- AEGIS-06: review pending. This note does not claim approval.
- ATLAS-01: system-bus and service-account boundary review pending.
