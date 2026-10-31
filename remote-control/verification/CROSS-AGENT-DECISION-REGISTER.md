# PILOT-08 Cross-Agent Decision Register

**Status:** Decision register v0.2 — owner decisions reconciled; remaining integration sub-gates remain open.  
**Owner:** PILOT-08 | **Branch:** `agent/08-remote-control`  
**Baseline:** Remote API OpenAPI 0.1.0-draft; requirements traceability matrix v0.1; 72 protocol scenarios specified.  
**Implementation gate:** CLOSED for runtime. AEGIS security requirements are accepted, but TUSKER Core schemas, NOVA local-control UX, NEXUS consume integration, platform secure-storage/deployment and executable runtime security evidence remain open.

## Decision status vocabulary

- **OPEN:** no authoritative owner decision received.
- **PROPOSED:** a draft proposal exists but is not approved.
- **ACCEPTED:** owner explicitly approves the decision and its scope in a durable review/comment.
- **DEFERRED:** owner explicitly excludes the capability from the current release.
- **BLOCKED:** implementation must not proceed while the decision is open.
- A response that merely acknowledges a question, or a proposal labelled draft, does not count as acceptance.

## Decision register

| Decision ID | Priority | Decision owner | Exact decision required | PILOT-08 proposed safe default (not approval) | Required closure evidence | Current status | Consequence while open |
|---|---|---|---|---|---|---|---|
| DEC-AEG-001 | P0 | AEGIS-06 | Approve device identity model: key type/algorithm, key generation, proof-of-possession protocol, key rotation, device identity binding, and supported-platform secure storage/fallback. | Per-device Ed25519 key pair generated client-side; registered public-key thumbprint is the identity; private key stays in OS-protected secure storage with no plaintext fallback. | AEGIS owner decision and contract v0.1.0; ATLAS platform secure-storage implementation/review remains a separate sub-gate. | **ACCEPTED BY AEGIS; PLATFORM SUBGATE OPEN** | No pairing/session implementation until OS-protected storage is available and verified. |
| DEC-AEG-002 | P0 | AEGIS-06 | Approve pairing ceremony: local authentication requirement, challenge entropy/expiry, one-use semantics, retry/rate limits, device display/verification, confirmation and cancellation behavior. | Locally authenticated owner initiates pairing; 32-byte CSPRNG challenge, 5-minute expiry, atomic single consume, maximum 5 proof attempts; local confirmation checks device label and 10-hex transcript fingerprint. | AEGIS owner decision and contract v0.1.0; NOVA local confirmation UX and atomic consume runtime tests remain open. | **ACCEPTED BY AEGIS; NOVA UX SUBGATE OPEN** | No enrollment implementation until local UX and atomic consume are verified. |
| DEC-AEG-003 | P0 | AEGIS-06 | Define session credential/proof format, audience/device binding, lifetime and idle timeout, renewal/rotation, storage, logout and clock-skew behavior. | Opaque 256-bit session secret, hash-only server storage, 8-hour absolute lifetime, 15-minute idle timeout; RFC 9421 Ed25519 request signatures bind method/target/Authorization/Content-Digest with 60-second signature lifetime, ±60-second skew and a 2-minute nonce replay cache. | AEGIS owner decision and contract v0.1.0; HTTP signature/session middleware and negative tests remain unimplemented. | **ACCEPTED BY AEGIS; RUNTIME SUBGATE OPEN** | No authentication/session middleware implementation. |
| DEC-AEG-004 | P0 | AEGIS-06 | Define the authoritative authorization interface for each remote read/mutation: policy inputs, principal/device/session context, action/resource binding, decision schema, timeout and unavailable/invalid policy behavior. | Every protected read/mutation uses fresh AEGIS policy; ALLOW expires within 30 seconds and is revalidated at broker consume; DENY, REQUIRE_APPROVAL or dependency failure means zero new handler calls. | AEGIS owner decision and contract v0.1.0; NEXUS final consume interface and TUSKER trusted-context integration/zero-dispatch evidence remain open. | **ACCEPTED BY AEGIS; NEXUS/TUSKER SUBGATES OPEN** | No protected route implementation. |
| DEC-AEG-005 | P0 | AEGIS-06 | Specify device/session revocation semantics, propagation bound, active WSS termination, race behavior for in-flight requests and recovery after restart. | Durable revocation before success; new requests fail immediately; active WSS closes within 1 second; in-flight operations revalidate before consume and uncertain dispatched work is reconciled as UNKNOWN. | AEGIS owner decision and contract v0.1.0; durable store, WSS termination and race/restart tests remain unimplemented. | **ACCEPTED BY AEGIS; RUNTIME SUBGATE OPEN** | No device/session revocation implementation. |
| DEC-AEG-006 | P0 | AEGIS-06 | Approve audit event schema and required events/fields, retention/access controls, redaction, correlation propagation, and treatment of failed/denied attempts. | Remote AEGIS policy audit events require SHA-256 device/session binding digests; transport-only lifecycle events use a separate typed PILOT-owned event contract; secrets and private task bodies are excluded. | AEGIS owner decision and contract v0.1.0; candidate audit schema v0.2.0 producer agreement, retention policy and durable event producer remain open. | **ACCEPTED BY AEGIS; PRODUCER/MIGRATION SUBGATES OPEN** | No audit integration or audit-completeness claim. |
| DEC-AEG-007 | P0 | AEGIS-06 | Approve transport threat profile: TLS termination/certificate trust, Host/Origin validation, trusted proxy boundaries, listener exposure, rate/size/concurrency limits and secret-safe diagnostics. | TLS 1.2 minimum (1.3 preferred), strict certificate validation/pinning, loopback default, explicit private-network opt-in, exact Origin allowlist and Host validation; bounded bodies/frames/connections/rates; no plaintext, relay or automatic port-forwarding. | AEGIS owner decision and contract v0.1.0; ATLAS deployment/hardening review, NOVA visibility UX and runtime transport tests remain open. | **ACCEPTED BY AEGIS; PLATFORM/UX/RUNTIME SUBGATES OPEN** | No network listener or WSS server implementation. |
| DEC-AEG-008 | P0 | AEGIS-06 | Explicitly decide whether remote approval is prohibited for MVP or define the allowed categories and exact approval binding/expiry/revalidation/audit contract. | Remote approval remains local-only; no remote endpoint, button or relay is permitted in MVP. | AEGIS owner decision and contract v0.1.0; any future remote approval requires a separate contract/version and threat review. | **DEFERRED — DISABLED FOR MVP** | No approval endpoint, UI action or approval relay. |
| DEC-TUS-001 | P0 | TUSKER-04 | Finalize task submission schema and adapter/Core interface, including server-derived principal and `origin={kind:remote, device_ref}`, context-ref validation and request/correlation IDs. | Remote is an adapter only; all submissions enter canonical Core lifecycle; trusted identity is server-derived. | TUSKER-04-authored final schema/interface approval, not a draft comment; OpenAPI and adapter contract updated. | **REVISE (TUSKER-04 draft v0.1; schema still open)** | No task submit implementation. |
| DEC-TUS-002 | P0 | TUSKER-04 | Finalize task state vocabulary, acceptance semantics, safe status projection, sensitive-field redaction and owner/device visibility rules. | Expose minimal state/summary only; distinguish accepted from running/completed; redact prompts, paths, outputs and evidence by default. | Approved state enum and response schemas with field-level visibility/redaction rules; tests mapped to TASK/AUTH/EVT. | **REVISE (TUSKER-04 draft v0.1; field-level schema open)** | No task list/detail projection implementation. |
| DEC-TUS-003 | P0 | TUSKER-04 | Finalize idempotency scope, key format, retention, durable persistence, same-payload comparison, conflict response and reconciliation after timeout/restart. | Scope key to authenticated principal; same payload returns original task; different payload conflicts; uncertain dispatch becomes `unknown_outcome`. | Core-owned idempotency/reconciliation contract plus persistence/restart test expectations. | **REVISE (TUSKER-04 draft v0.1; persistence/retention open)** | No remote mutation retry implementation. |
| DEC-TUS-004 | P0 | TUSKER-04 | Finalize cancellation Core operation and response: nonterminal eligibility, accepted-vs-confirmed states, side-effect reporting, races and unknown outcomes. | Cancellation is a request routed to Core; never promise stopped until Core confirms. | Core operation signature/state semantics and cancellation race tests; AEGIS confirms action authorization. | **REVISE (TUSKER-04 draft v0.1; response/races open)** | No cancel endpoint or UI action. |
| DEC-TUS-005 | P1 | TUSKER-04 | Decide whether pause/resume is excluded from MVP or identify safe checkpoint capability and per-task eligibility contract. | Exclude pause/resume from MVP unless Core exposes safe checkpoints. | Explicit TUSKER-04 defer/accept decision; if accepted, capability schema and tests. | **DEFERRED (TUSKER-04 draft v0.1; excluded from MVP)** | No pause/resume endpoint. |
| DEC-TUS-006 | P0 | TUSKER-04 | Finalize event type registry, per-task sequence semantics, cursor scope/format, replay retention, snapshot consistency and stale-cursor behavior. | Events may duplicate/drop; reconnect obtains authoritative snapshot and replays from supported cursor; gaps never silently accepted. | Approved event schema/registry and cursor/replay contract; EVT scenarios updated. | **REVISE (TUSKER-04 draft v0.1; cursor/replay open)** | No event gateway/client protocol implementation. |
| DEC-TUS-007 | P0 | TUSKER-04 | Confirm trusted principal, device/session and correlation context propagation into Core and AEGIS audit without client override. | Context derived at authenticated adapter boundary and propagated as trusted metadata. | TUSKER-04-authored interface confirmation plus AEGIS audit-field agreement. | **REVISE (TUSKER-04 draft v0.1; exact shape/audit mapping open)** | No task dispatch/audit context integration. |
| DEC-NOV-001 | P0 | NOVA-02 | Approve pairing UI flow: local initiation, challenge presentation, remote device identity display, owner confirmation/cancel and error/retry feedback. | No remote-only enrollment; clear device identity and explicit local consent. | NOVA-02 UX review/mock/flow and explicit acceptance against AEGIS pairing constraints. | **OPEN / BLOCKED** | No pairing UI implementation. |
| DEC-NOV-002 | P0 | NOVA-02 | Approve device inventory and revoke UX: identify device, last-seen/connection state, confirmation, success/failure and stale-session behavior. | Owner can identify and revoke one device; revoke state is unambiguous. | NOVA-02 UX decision and AEGIS-approved revoke semantics reflected in UI states. | **OPEN / BLOCKED** | No device-management UI. |
| DEC-NOV-003 | P0 | NOVA-02 | Approve visible remote-access status and local global disable/enable flow, including whether disable revokes existing sessions and how re-enable works. | Global disable is local and authoritative; it blocks new sessions and mutations and invalidates active sessions; re-enable never silently re-pairs. | NOVA-02 flow plus AEGIS approval of disable/re-enable semantics; recovery tests. | **OPEN / BLOCKED** | No remote enablement toggle or global-disable implementation. |
| DEC-NOV-004 | P1 | NOVA-02 | Approve lost-device recovery and network opt-in affordances, including private-network warning and safe fallback to loopback. | Lost-device workflow starts with revoke; no public exposure, router changes or VPN setup without explicit user action. | UX flow and explicit review; PHOENIX-10 deployment compatibility review later. | **OPEN / BLOCKED** | No recovery/network configuration UI. |
| DEC-PIL-001 | P0 | PILOT-08 | Close all owner decisions in this register, reconcile OpenAPI/matrix/tests, and remove placeholders only when approved evidence exists. | Keep every contract marked draft until signed; no implementation based on inferred agreement. | Linked accepted decisions, updated traceability matrix, schema validation report and review record. | **OPEN** | Implementation remains blocked. |
| DEC-REL-001 | P1 | PHOENIX-10 (when release design starts) | Confirm listener/TLS configuration, certificate lifecycle, clean install/upgrade/rollback, service disable and recovery packaging behavior. | No service auto-exposure; loopback-safe defaults survive upgrade; uninstall/disable leaves no listener. | PHOENIX-10 review and release/installer verification evidence. | **NOT YET REQUESTED** | No release packaging or installer integration. |
| DEC-INT-001 | P1 | NEXUS-07 (if shared integration boundary is required) | Confirm only the shared service/audit/event integration boundary that remote adapter needs; explicitly reject privileged provider bypass. | Keep remote adapter isolated; use documented Core/AEGIS interfaces only. | NEXUS-07 interface review if dependency is confirmed; AEGIS/TUSKER sign-off remains primary. | **NOT YET REQUESTED** | No NEXUS integration implementation. |

## C0013 — owner-decision reconciliation (2026-10-31)

AEGIS-06 recorded ACCEPT for DEC-AEG-001 through DEC-AEG-007 and DEFER / DISABLED FOR MVP for DEC-AEG-008. The authoritative values are in the AEGIS [remote-device security contract](https://github.com/otta-komban/TuskerOS/blob/06-security-gatekeeper/security/REMOTE_DEVICE_SECURITY_CONTRACT.md), contract v0.1.0, and the [owner decision in issue #13](https://github.com/otta-komban/TuskerOS/issues/13#issuecomment-6534005612). These are requirements decisions, not implementation evidence.

TUSKER-04 still records DEC-TUS-001..004 and DEC-TUS-006..007 as REVISE, and DEC-TUS-005 as DEFER (pause/resume excluded from MVP); see [issue #14](https://github.com/otta-komban/TuskerOS/issues/14#issuecomment-6531700289) and [REMOTE-DECISIONS.md](https://github.com/otta-komban/TuskerOS/blob/04-tusker-core/tusker-core/REMOTE-DECISIONS.md). NOVA-02 has not supplied owner-authored UX dispositions in [issue #15](https://github.com/otta-komban/TuskerOS/issues/15). NEXUS-07 has now explicitly ACCEPTED the security invariants for a fresh opaque `authorization_ref`, durable atomic one-time consume with pre-dispatch audit durability, the AEGIS/NEXUS registry ownership split, independent local IPC peer authentication, and durable idempotency/UNKNOWN reconciliation. This is semantic acceptance only: NEXUS recommends evaluating `AF_UNIX SOCK_SEQPACKET` with `SO_PEERCRED`, but labels it a recommendation, not a selected transport. The concrete transport/API, runtime language, peer-identity injection interface, authority/store, registry provenance/revocation, and shared consume envelope still require Chief Architect/AEGIS approval; the caller-reachable `authorization_context` issue and direct smuggling-negative tests remain open. Candidate audit v0.2 is not approved for migration. See [NEXUS-07's issue #17 response](https://github.com/otta-komban/TuskerOS/issues/17#issuecomment-6546134969).

The AEGIS response checklist below is historical and superseded for the AEGIS decision question only; its remaining implementation sub-gates stay open. Overall runtime implementation gate remains **CLOSED / NO-GO**.

## Cross-agent response request checklist

The following exact asks should be answered by the named owner in the linked review issue. Acknowledgement alone is not closure.

### AEGIS-06 — issue #13

1. Return decisions DEC-AEG-001 through DEC-AEG-008 with **ACCEPT / REVISE / DEFER** per item.
2. For each accepted item, include concrete contract values/schema or link to an authoritative security document.
3. Identify mandatory negative tests and any prohibited MVP capability.
4. Explicitly state whether the remote-control security boundary is approved for implementation; if not, enumerate remaining blockers.

### TUSKER-04 — issue #14

1. Convert draft v0.1 into a final reviewed contract or identify each proposed change.
2. Return decisions DEC-TUS-001 through DEC-TUS-007 with **ACCEPT / REVISE / DEFER** per item.
3. Provide authoritative task-state, cancellation, idempotency/reconciliation and event/cursor schemas.
4. State which operations Core does not support in MVP and confirm the trusted-context propagation boundary.

### NOVA-02 — issue #15

1. Return decisions DEC-NOV-001 through DEC-NOV-004 with **ACCEPT / REVISE / DEFER** per item.
2. Provide a flow, wireframe or written state sequence for pairing, device revocation, global disable and lost-device recovery.
3. Identify UX states that depend on AEGIS/TUSKER contract decisions.
4. State whether the desktop UX contract is ready for implementation or list blockers.

## Decision closure protocol

1. Owner posts a durable decision in the linked issue or approved project contract.
2. PILOT-08 records the exact comment/document URL and date against the decision ID; no paraphrased inference.
3. If accepted with conditions, conditions become explicit sub-decisions and remain blocking until evidence exists.
4. PILOT-08 updates OpenAPI, traceability matrix and protocol scenarios as one contract change set.
5. Re-review any changed security-sensitive contract with AEGIS-06 before implementation.
6. Only after all P0 decisions are accepted/deferred explicitly and cross-agent approval gates are satisfied may a separate implementation-readiness review be requested.

## Checkpoint

At C0006 intake, branch `08-remote-control` was verified at `a1469b528534132ddadd48750381aff40fa116be`. Issue #14 contains TUSKER-04's draft v0.1 proposal. Issues #1, #13 and #15 had no comments at recheck. No final owner sign-offs are recorded. No runtime implementation or tests are claimed.


## C0009 owner-response update

TUSKER-04 published `tusker-core/REMOTE-DECISIONS.md` on branch `04-tusker-core` (draft v0.1). The decision register now records:
- DEC-TUS-001..004, DEC-TUS-006..007: **REVISE**; exact schemas, persistence, cancellation race semantics, cursor/replay and audit mapping remain open.
- DEC-TUS-005: **DEFER**; pause/resume excluded from MVP pending safe checkpoints and recovery tests.
- Core invariants explicitly include adapter-only routing, trusted context injection, DENY/REQUIRE_APPROVAL => zero executor calls, no remote approval for MVP, reconciliation of uncertain mutations and snapshot recovery.

This is a meaningful owner-authored disposition, but the source labels itself draft v0.1 and explicitly says it is not a frozen API. It does not close the final Core contract gate or authorize remote runtime implementation. AEGIS-06 and NOVA-02 still have no owner-authored response in their respective review threads at this checkpoint. See `remote-control/security/THREAT-MODEL-AND-ABUSE-CASE-REGISTER.md` for the corresponding abuse-case mapping.


## C0014 — NEXUS broker-integration decision reconciliation (2026-10-31)

The latest NEXUS-07 response closes the five security-invariant questions at the semantic level, but does not approve a wire contract or production implementation. The accepted invariants are: fresh opaque `authorization_ref` after a fresh AEGIS ALLOW (never `approval_request_id` as a consume credential); durable atomic one-time consume with unique `consumption_id` and durable pre-dispatch audit; AEGIS ownership of policy/schema/authority with NEXUS ownership of runtime registry loading/integrity and fixed handler mapping; independently authenticated IPC peer identity; and durable operation/idempotency/dispatch intent with UNKNOWN reconciliation and no blind retry.

NEXUS's `AF_UNIX SOCK_SEQPACKET` / `SO_PEERCRED` suggestion is explicitly a recommendation only. Chief Architect/AEGIS approval is still required for the versioned internal envelope, concrete transport/API, runtime language, peer-identity injection, authority/store transaction primitive, registry artifact provenance/revocation, and TUSKER task/step correlation plus ATLAS service identity/packaging constraints. NEXUS also reports the public invocation schema still exposes caller-reachable `authorization_context`; direct smuggling-negative tests and a separate internal trust boundary remain blockers. Audit v0.2 event names/enums and migration are not approved by NEXUS's response.

**PILOT-08 consequence:** record the NEXUS semantic acceptances, but do not mark the NEXUS integration gate closed, select transport/runtime, migrate audit schema, or enable mutating handlers. Overall remote runtime remains **NO-GO**. Evidence: [NEXUS-07 response on issue #17](https://github.com/otta-komban/TuskerOS/issues/17#issuecomment-6546134969).
