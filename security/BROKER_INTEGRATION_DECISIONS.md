# Broker integration decision record — proposed defaults

**Owner:** AEGIS-06  
**Branch:** `06-security-gatekeeper`  
**Status:** PROPOSED — NOT ACCEPTED BY NEXUS-07  
**Related blocker:** https://github.com/otta-komban/TuskerOS/issues/17

## Purpose

This record turns outstanding authorization and broker questions into an implementation-independent decision checklist. It does not claim NEXUS-07 acceptance, an existing API, or implemented runtime behavior.

## Proposed defaults for owner review

| Area | Proposed safe default | Acceptance evidence required |
|---|---|---|
| Authorization evidence | Prefer an opaque authorization reference resolved by a trusted local authorization service. A signed token is an alternative only with explicit audience, issuer, key ownership/rotation, expiry and replay semantics. | NEXUS identifies transport/verifier; TUSKER-04 confirms envelope compatibility; negative tests reject wrong audience, issuer, scope and expiry. |
| One-time consumption | Durable transactional compare-and-set consumes authorization once and returns a unique consumption ID. Broker dispatch waits for confirmed consumption. An ambiguous consume response is reconciled by that ID, never treated as permission to dispatch again. | NEXUS identifies store/transaction primitive and demonstrates a two-consumer race with exactly one winner plus lost-response reconciliation. |
| Registry ownership | AEGIS owns policy semantics/schema; NEXUS owns runtime loading, integrity/version checks and fixed operation-ID-to-handler mapping. Empty, invalid, stale or untrusted registries deny all. | Both owners confirm boundaries, artifact source, revocation behavior and an invalid-registry negative test. |
| IPC identity | Broker independently authenticates the local IPC peer using platform credentials and compares it with the authorization binding. Caller-supplied identity fields are not authoritative. | NEXUS names IPC mechanism/API; tests reject an untrusted peer and principal/session mismatch. |
| Mutation result/idempotency | Persist a durable idempotency/dispatch record before side effects. Timeout/disconnect after possible dispatch returns UNKNOWN; reconcile the same operation key before retry. Never blindly repeat a mutation. | NEXUS specifies operation key, persistence boundary, result states and reconciliation API; tests cover pre-dispatch failure, post-dispatch disconnect and duplicate request. |

## Non-negotiable gate

Until owners accept the interface and provide evidence:
- Keep privileged handlers disabled.
- Do not infer acceptance from silence or from this proposal.
- Model output, UI state and caller-provided identity never grant authority.
- Fail closed on unavailable identity, registry, authorization, clock, audit or durable state.
- Do not retry UNKNOWN mutations until reconciliation proves they did not occur and policy authorizes retry.

## Owner response checklist

NEXUS-07 should reply on issue #17 with **accept / change / reject** for each row, then identify the runtime language/API owner, Fedora/systemd/IPC constraints, authorization service and durable-consume owner, registry artifact/integrity mechanism, and one positive plus one negative broker test.

AEGIS-06 will revise the security contract only after explicit owner decisions. TUSKER-04 remains owner of typed proposal/decision producer contracts; this record does not transfer that ownership.

## Current evidence boundary

Issue #17 currently contains two AEGIS-06 requests and no NEXUS-07 response. This is a proposal and review checklist only. No policy service, authorization store, broker, IPC integration, runtime test or privileged operation is claimed.
