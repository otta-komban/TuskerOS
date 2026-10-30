# PILOT-08 Cross-Agent Decision Register

**Status:** Open decision register v0.1 — no approval is implied by this document.  
**Owner:** PILOT-08 | **Branch:** `08-remote-control`  
**Baseline:** Remote API OpenAPI 0.1.0-draft; requirements traceability matrix v0.1; 72 protocol scenarios specified.  
**Implementation gate:** CLOSED. Do not begin remote-control runtime implementation until the blocking decisions below have durable owner-authored resolutions.

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
| DEC-AEG-001 | P0 | AEGIS-06 | Approve device identity model: key type/algorithm, key generation, proof-of-possession protocol, key rotation, device identity binding, and supported-platform secure storage/fallback. | Per-device asymmetric key; server verifies possession; private key stays in OS secure storage where available; no shared reusable pairing secret. Exact algorithm/storage must be chosen by AEGIS. | AEGIS-authored review specifying algorithm, key lifecycle, threat assumptions and platform fallback; referenced by approved pairing/session contract. | **OPEN / BLOCKED** | No pairing/session implementation or bearer-token assumption. |
| DEC-AEG-002 | P0 | AEGIS-06 | Approve pairing ceremony: local authentication requirement, challenge entropy/expiry, one-use semantics, retry/rate limits, device display/verification, confirmation and cancellation behavior. | Pairing initiated locally by authenticated owner; short-lived single-use challenge; explicit local confirmation; bounded attempts; replay rejected. | AEGIS-authored security decision with concrete parameter bounds and negative cases; NOVA-02 confirms UX implements the ceremony. | **OPEN / BLOCKED** | No enrollment implementation. |
| DEC-AEG-003 | P0 | AEGIS-06 | Define session credential/proof format, audience/device binding, lifetime and idle timeout, renewal/rotation, storage, logout and clock-skew behavior. | Short-lived device-bound session with least privilege and server-side revocation; avoid long-lived bearer secrets where sender-constrained proof is feasible. | Approved session contract and threat rationale; credential lifecycle cases mapped to SESS tests. | **OPEN / BLOCKED** | OpenAPI bearer scheme remains placeholder; no auth middleware implementation. |
| DEC-AEG-004 | P0 | AEGIS-06 | Define the authoritative authorization interface for each remote read/mutation: policy inputs, principal/device/session context, action/resource binding, decision schema, timeout and unavailable/invalid policy behavior. | Re-evaluate authorization on every request and retry; fail closed; no client role or policy outcome accepted. | AEGIS-approved interface/schema and explicit fail-closed error mapping; negative tests linked to AUTH/SESS/TASK. | **OPEN / BLOCKED** | No protected route implementation. |
| DEC-AEG-005 | P0 | AEGIS-06 | Specify device/session revocation semantics, propagation bound, active WSS termination, race behavior for in-flight requests and recovery after restart. | Revocation immediately blocks new requests; active streams are terminated/rejected; in-flight mutations are reconciled, not assumed rolled back. | Approved revocation contract with measurable propagation target and testable race semantics; SESS/EVT evidence. | **OPEN / BLOCKED** | No device revoke/session lifecycle implementation. |
| DEC-AEG-006 | P0 | AEGIS-06 | Approve audit event schema and required events/fields, retention/access controls, redaction, correlation propagation, and treatment of failed/denied attempts. | Record actor/device/session/action/outcome/correlation metadata; never log credentials, private prompts or sensitive task payloads by default. | AEGIS-approved schema, retention/privacy policy and sample redacted events; TUSKER-04 confirms Core context propagation. | **OPEN / BLOCKED** | No audit integration or claim of audit completeness. |
| DEC-AEG-007 | P0 | AEGIS-06 | Approve transport threat profile: TLS termination/certificate trust, Host/Origin validation, trusted proxy boundaries, listener exposure, rate/size/concurrency limits and secret-safe diagnostics. | Loopback default; explicit private-network opt-in; TLS and app-level auth remain required; no UPnP/port-forwarding/public relay. | Written security profile and deployment assumptions; NET/EVT test requirements approved. | **OPEN / BLOCKED** | No network listener or WSS server implementation. |
| DEC-AEG-008 | P0 | AEGIS-06 | Explicitly decide whether remote approval is prohibited for MVP or define the allowed categories and exact approval binding/expiry/revalidation/audit contract. | Remote approval stays disabled and no endpoint is exposed. | Explicit AEGIS decision. If enabled, a separate narrowly scoped contract and threat review plus test plan are mandatory. | **OPEN / BLOCKED; disabled by default** | No approval endpoint, UI action or approval relay. |
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
