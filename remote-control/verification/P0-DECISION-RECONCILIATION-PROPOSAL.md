# PILOT-08 P0 Decision Reconciliation Proposal

**Status:** Proposal / implementation-readiness input only. This document does not freeze shared contracts, grant security acceptance, or authorize runtime behavior.
**Owner:** PILOT-08
**Target branch:** `agent/08-remote-control`
**Baseline:** `main` at `8bf66079f9e021244eda432fa8455e83b59e2165`
**Prepared:** 2026-10-31T07:34:59Z
**Task:** PILOT-08-P0-RECON-01

## 1. Executive disposition

The cross-agent decision state has materially changed since the historical C0014 readiness record:

- AEGIS-06 has published owner-authored decisions for DEC-AEG-001..008: seven ACCEPT and DEC-AEG-008 DEFER / disabled for MVP.
- TUSKER-04 has published DEC-TUS-001..004 and DEC-TUS-006..007 as REVISE, and DEC-TUS-005 as DEFER (pause/resume excluded from MVP). Its source remains draft v0.1 and explicitly says it is not a frozen API.
- NOVA-02 has not supplied owner-authored decisions for DEC-NOV-001..004.
- NEXUS-07 has published provisional system-integration schemas and later implementation-intake notes, but its broker consume, authorization-context and dispatch-reconciliation boundary remains unresolved.
- The current OpenAPI file remains v0.1.0-draft and contains stale authentication placeholder text that conflicts with AEGIS-06's accepted request-proof requirements.

**Disposition: NO-GO for remote runtime implementation and release acceptance.** Continue only with proposals, local validation tooling that does not assume the unresolved contracts, and owner coordination until the reauthorization and P0 gates are satisfied.

## 2. AEGIS-06 decisions incorporated as requirements

Source: AEGIS-06 owner decision on issue #13, comment
https://github.com/otta-komban/TuskerOS/issues/13#issuecomment-6534005612
Durable contract: `security/REMOTE_DEVICE_SECURITY_CONTRACT.md`, branch `06-security-gatekeeper`, commit `9fbb284fefc2afa2144b691b49aeb551ba55ec68`.

| Decision | Disposition | Required remote-control behavior |
|---|---|---|
| DEC-AEG-001 | ACCEPT | Per-device Ed25519 key pair; client-generated; private key in OS-protected secure storage; no plaintext fallback; identity is public-key thumbprint. |
| DEC-AEG-002 | ACCEPT | Local authenticated initiation; 32-byte CSPRNG challenge; 5-minute expiry; single atomic consume; max 5 proof attempts; local confirmation of device label and matching 10-hex transcript fingerprint. |
| DEC-AEG-003 | ACCEPT | Opaque 256-bit session secret, hash-only server storage, 8-hour absolute and 15-minute idle expiry, no refresh token; every HTTP request uses RFC 9421 Ed25519 signature covering method, target URI, Authorization and RFC 9530 Content-Digest; <=60-second signature lifetime, <=60-second timestamp skew, unique nonce replay cache >=2 minutes. |
| DEC-AEG-004 | ACCEPT | Every protected read and mutation is evaluated by AEGIS; trusted principal/origin/device/session/resource context is server-derived; ALLOW <=30 seconds and revalidated at broker consume; DENY, REQUIRE_APPROVAL or dependency failure means zero new handler calls; task operations enter TUSKER Core only. |
| DEC-AEG-005 | ACCEPT | Durable revoke/disable commit before success; new requests fail immediately; active WSS closes within 1 second; in-flight operations revalidate before consume; dispatched uncertainty is UNKNOWN and reconciled, never blindly retried. |
| DEC-AEG-006 | ACCEPT | Remote policy audit events carry device/session SHA-256 binding digests; transport-only lifecycle events use a separate typed PILOT-owned event contract; no secrets or private task bodies in logs. |
| DEC-AEG-007 | ACCEPT | TLS 1.2 minimum / 1.3 preferred; validated chain or owner-pinned certificate; loopback default; explicit private-network opt-in; exact Origin allowlist and Host validation; body/frame/connection limits; no plaintext, public relay, UPnP or automatic forwarding. |
| DEC-AEG-008 | DEFER / DISABLED FOR MVP | No remote approve/deny endpoint, button or relay. Approval remains local-only. |

These are security requirements. They are not evidence that the device registry, key storage, signature verifier, AEGIS adapter, broker consume, audit persistence, listener or WSS behavior exists or passes tests.

## 3. TUSKER-04 decisions and exact closure needed

Source: `tusker-core/REMOTE-DECISIONS.md`, branch `04-tusker-core`, draft v0.1; issue #14 comment
https://github.com/otta-komban/TuskerOS/issues/14#issuecomment-6531700289

| Decision | Current owner disposition | Remaining P0 closure evidence |
|---|---|---|
| DEC-TUS-001 submission | REVISE | Final bounded request/response schema, canonical Core entry point and context-reference validation. |
| DEC-TUS-002 projections | REVISE | Final task state enum, authorization-scoped projection schema and field-level redaction rules. |
| DEC-TUS-003 idempotency | REVISE | Durable storage, key scope/format, retention, canonical payload comparison and restart/unknown-dispatch reconciliation contract. |
| DEC-TUS-004 cancellation | REVISE | Exact cancellation request/response states, accepted-vs-stopped semantics, race behavior and side-effect reporting. |
| DEC-TUS-005 pause/resume | DEFER | Exclude from MVP; no pause/resume routes or UI affordances. |
| DEC-TUS-006 events/replay | REVISE | Final event registry/schema, per-task sequence, cursor scope/format/retention, snapshot watermark and stale-cursor behavior. |
| DEC-TUS-007 trusted context | REVISE | Final trusted principal/origin/device/session/correlation shape and AEGIS audit mapping; reject client-supplied authority. |

The draft's accepted invariants remain mandatory: PILOT is an adapter, not a second planner/executor; all registered operations including reads pass AEGIS policy; DENY and REQUIRE_APPROVAL yield zero executor calls; uncertain outcomes are reconciled; remote approval remains disabled.

## 4. NOVA-02 product/UX decisions still blocking

Issue #15 currently contains PILOT-08's request but no owner-authored NOVA-02 response.

| Decision | Priority | Owner decision required |
|---|---|---|
| DEC-NOV-001 | P0 | Pairing flow: local initiation, challenge presentation, device identity/fingerprint, explicit confirm/cancel, retry and error states. |
| DEC-NOV-002 | P0 | Device inventory and single-device revocation: identity, last-seen/connection state, confirmation and result/error states. |
| DEC-NOV-003 | P0 | Visible remote-access status and local global disable/re-enable behavior; confirm disable revokes all active sessions and re-enable never silently re-pairs. |
| DEC-NOV-004 | P1 | Lost-device recovery and private-network opt-in warnings/fallback to loopback. |

No pairing UI, device-management UI, global-disable UI or recovery UX should be implemented by inferring these product decisions.

## 5. NEXUS-07 integration boundary

Remote-control must not call NEXUS provider APIs or a privileged broker directly. The only permitted task path is:

`remote client → PILOT authenticated gateway → AEGIS policy → TUSKER Core lifecycle → registered NEXUS operation → AEGIS broker consume (where required)`.

NEXUS-07's issue #5 follow-up says the public invocation schema still has an open-ended caller-reachable `authorization_context` field and that it will not change this shared schema without Chief Architect approval. Its later implementation-intake comment identifies unresolved questions about strict authorization-context shape, atomic consume sequencing, binding of principal/operation/resources/session, durable consume/execution identity, and restart-safe duplicate-dispatch reconciliation.

Required closure before any end-to-end remote mutation:
1. Chief Architect approves the shared authorization-context and broker-consume contract.
2. AEGIS defines the authoritative principal/decision reference and exact fail-closed error semantics.
3. NEXUS defines and tests atomic consume, replay prevention, execution identity and uncertain-consume reconciliation.
4. TUSKER confirms the adapter passes only trusted context and reconciles unknown outcomes.
5. PILOT verifies zero Core dispatch / zero handler calls for non-ALLOW policy outcomes.

## 6. Existing proposal artifacts that are stale or incomplete

The current mainline proposal artifacts must be reconciled only after owner/Chief Architect review; do not treat this list as permission to alter shared schemas.

- `remote-control/ARCHITECTURE.md` still proposes 12-hour sessions and 30-minute idle expiry. AEGIS requires 8-hour absolute and 15-minute idle expiry.
- The architecture mentions a generic session rotation endpoint. AEGIS explicitly says no refresh token; renewal requires a fresh signed device-authentication challenge and a new session.
- `remote-control/contracts/v1/openapi.yaml` still describes `deviceSession` as a bearer-only placeholder and says the token/proof design is pending AEGIS. It does not express RFC 9421 signature parameters/coverage or the nonce replay cache.
- The OpenAPI draft does not express AEGIS's numeric pairing limits, 10-hex transcript fingerprint confirmation, secure-storage fail-closed rule, WSS server-to-client-only behavior, <=1-second revocation closure, or the accepted request/frame/connection limits.
- The OpenAPI draft has an Approvals tag but no approval route. Keep that omission and remove the unused tag in a later approved contract cleanup; remote approvals are disabled for MVP.
- The OpenAPI task/event schemas still contain permissive placeholders such as `additionalProperties: true` and owner-pending state/event descriptions. Do not freeze them while TUSKER-04 is REVISE.
- The current proposal does not yet define the separate typed PILOT transport-lifecycle audit event schema required by AEGIS-06.
- Global disable/re-enable, device key rotation and lost-device recovery need explicit local-owner UX/API boundaries before implementation.

## 7. Scope safe to prepare without crossing P0 boundaries

Permitted proposal/analysis work:
- Maintain this decision delta and link exact owner sources.
- Draft an implementation-neutral mapping from accepted AEGIS values to future tests.
- Prepare validator/test-harness design that consumes finalized schemas rather than inventing them.
- Inventory the stale contract fields and propose a versioned migration plan for Chief Architect review.
- Continue asking owners for the exact outstanding artifacts.

Not permitted before the gates close:
- Pairing/session/authentication runtime, network listener or remote API handlers.
- Remote task dispatch, cancellation, event streaming or broker calls.
- Local pairing/device-management/global-disable UI.
- Any alternate path around AEGIS or TUSKER, or any test-only production bypass.
- Declaring protocol, threat model or release acceptance complete based on schema/static checks.

## 8. Repository reauthorization gate

PR #49 states that branch existence is not implementation authorization. It requires:
1. Administrator-enabled and verified main branch protection / required checks.
2. Coordinator verification through an authorized GitHub permission context.
3. Owner/coordinator publication of task assignments and confirmation of the shared contract baseline.

The active `protect-main` ruleset is visible and requires PRs, but its required-status-check list is empty. The GitHub branch-protection detail endpoint is not accessible to this connection. Therefore the repository/coordinator gate is **not independently verified here**. Owner authorization for this task is acknowledged, but it does not let PILOT-08 claim the missing administrator/coordinator evidence.

## 9. Decision

**NO-GO for runtime implementation and release.** AEGIS requirements are accepted, but TUSKER remains REVISE, NOVA remains unanswered, NEXUS broker consume remains unresolved, the OpenAPI/architecture artifacts are stale, and the repository/coordinator reauthorization evidence is incomplete.

Next actions:
- NOVA-02: post explicit DEC-NOV-001..004 dispositions and UX flow.
- TUSKER-04: publish final versioned remote task/event/idempotency/cancellation/context contract and mark each decision ACCEPT/DEFER with evidence.
- NEXUS-07 + AEGIS-06 + Chief Architect: resolve the authorization-context and atomic broker-consume contract.
- Repository administrator/coordinator: configure required checks and verify the reauthorization gate.
- PILOT-08: after these closures, update the decision register/OpenAPI/traceability as one reviewed contract change set, then request a new implementation-readiness decision.
