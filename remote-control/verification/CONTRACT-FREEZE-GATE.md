# Remote-Control Contract Freeze Gate

**Status:** Draft v0.1 — proposed acceptance checklist, not an approved contract  
**Owner:** PILOT-08 | **Branch:** `08-remote-control`  
**Decision:** **NO-GO** until every applicable owner gate is closed with durable evidence.

## 1. Purpose

This checklist defines the evidence required to freeze the remote-control v1 contract before runtime implementation. It complements:
- `IMPLEMENTATION-READINESS-REVIEW.md` (overall P0 readiness and API findings)
- `CROSS-AGENT-DECISION-REGISTER.md` (owned decisions and dispositions)
- `SECURITY-ASSURANCE-CASE.md` (claims and assurance evidence)
- `REQUIREMENTS-TRACEABILITY-MATRIX.md` (requirements-to-scenarios mapping)
- `CONTRACT-COVERAGE-AND-CHANGE-CONTROL.md` (scenario mapping and change governance)

A checklist item is not closed by a PILOT-08 proposal, an issue being opened, a draft comment, or a document existing. Closure requires an owner-authored ACCEPT/REVISE/DEFER disposition and the specified evidence. REVISE and DEFER remain open blockers.

## 2. Gate semantics

| State | Meaning | Permitted effect |
|---|---|---|
| `OPEN` | Evidence or owner decision missing | Blocks freeze |
| `REVISE` | Owner explicitly requires changes | Blocks freeze |
| `DEFER` | Owner explicitly excludes or postpones scope | Blocks freeze unless scope is formally removed from v1 and all dependent artifacts agree |
| `EVIDENCE_PENDING` | Owner acceptance exists but required artifact/validation is absent | Blocks freeze |
| `READY_FOR_REVIEW` | Required evidence is attached and awaiting authorized review | Blocks freeze |
| `ACCEPTED` | Authorized owner accepts exact version and evidence | May satisfy that gate |
| `NOT_APPLICABLE` | Explicitly excluded with rationale and approval by affected owners | Satisfies only the documented excluded scope |

No unknown, missing, malformed or contradictory state is treated as ACCEPTED. All mandatory gates must be ACCEPTED or validly NOT_APPLICABLE before freeze.

## 3. Mandatory contract-freeze gates

| Gate ID | Owner | Required decision and evidence | Acceptance condition | Current disposition |
|---|---|---|---|---|
| CF-AEG-01 | AEGIS-06 | Device identity, pairing proof, key storage/rotation and recovery contract; algorithm and protocol version; negative test plan | Explicit ACCEPT for exact pairing/session identity contract, including replay and race behavior | OPEN |
| CF-AEG-02 | AEGIS-06 | Session credential format, lifetime, refresh, revocation propagation, HTTP/WSS invalidation and restart semantics | Exact credential/session schema and revocation guarantees accepted | OPEN |
| CF-AEG-03 | AEGIS-06 | Authorization request/decision schema, decision freshness, timeout/error mapping, policy versioning and retry reauthorization | Fail-closed behavior and zero-Core-dispatch semantics accepted for every non-ALLOW/unknown result | OPEN |
| CF-AEG-04 | AEGIS-06 | Approval policy and MVP scope | Remote approval explicitly disabled for MVP or a separately approved policy is supplied; no implicit approval | OPEN |
| CF-AEG-05 | AEGIS-06 | Audit event identity, required fields, redaction, retention and correlation contract | Versioned audit schema and privacy/security requirements accepted | OPEN |
| CF-AEG-06 | AEGIS-06 | TLS/origin/host/proxy trust, listener exposure, message bounds, rate limits and network threat assumptions | Exact transport profile and deployment constraints accepted | OPEN |
| CF-TUS-01 | TUSKER-04 | Task submission schema, allowed task types, validation and server-derived principal/origin/device context | Frozen schema and explicit rejection of client-supplied security identity | REVISE — draft v0.1 |
| CF-TUS-02 | TUSKER-04 | Durable idempotency key scope, retention, payload conflict behavior, crash consistency and retry semantics | Persistence model and same-key/same-payload vs same-key/different-payload behavior accepted and testable | REVISE — draft v0.1 |
| CF-TUS-03 | TUSKER-04 | Task state model, accepted/queued/running/terminal transitions and response/error semantics | Versioned state enum, transition rules and error mapping accepted | REVISE — draft v0.1 |
| CF-TUS-04 | TUSKER-04 | Cancellation request/confirmation race, side-effect boundary and timeout/unknown-outcome behavior | Cancellation semantics distinguish request from confirmed stop; uncertain outcomes reconcile safely | REVISE — draft v0.1 |
| CF-TUS-05 | TUSKER-04 | Snapshot projection, event sequence/cursor, replay window, retention and gap recovery | Authoritative snapshot/replay contract and cross-principal isolation accepted | REVISE — draft v0.1 |
| CF-TUS-06 | TUSKER-04 | Trusted context and audit propagation into Core/AEGIS | Principal, device, session and correlation context are server-derived and consistently propagated | REVISE — draft v0.1 |
| CF-TUS-07 | TUSKER-04 | Pause/resume scope | Explicitly keep out of v1 unless safe checkpoint/recovery contract and tests are approved | DEFER — draft v0.1 |
| CF-NOV-01 | NOVA-02 | Pairing consent, device identity display, confirmation and cancellation UX | Approved user journey and threat-informed consent states | OPEN |
| CF-NOV-02 | NOVA-02 | Device list, trust status, per-device revoke and active session visibility | Approved device-management and revocation UX | OPEN |
| CF-NOV-03 | NOVA-02 | Global disable, in-flight action warning, recovery and lost-device UX | Approved emergency-disable and recovery journey with defined state feedback | OPEN |
| CF-NOV-04 | NOVA-02 | Accessibility, error/retry language and security-state communication | Reviewed interaction specification with accessible states and no misleading success claims | OPEN |
| CF-PIL-01 | PILOT-08 | Reconciled OpenAPI and complementary WebSocket message contract | All owner decisions reflected consistently; no unresolved schema contradictions | OPEN |
| CF-PIL-02 | PILOT-08 | Contract validation and traceability | OpenAPI/schema validators pass; every requirement and scenario maps to a versioned operation/message and negative case | EVIDENCE_PENDING |
| CF-REL-01 | PHOENIX-10 / ATLAS-01 | Supported platform, packaging, listener defaults, secret storage, upgrade/rollback and release threat review | Applicable platform/release owners accept deployment and rollback evidence | OPEN |

## 4. Cross-artifact consistency checks

Before requesting final freeze, verify all of the following against the same candidate contract version:

1. Every OpenAPI HTTP operation has an owner, authentication requirement, authorization requirement, request/response schema, error mapping, rate-limit class and audit event.
2. Every WebSocket message has a direction, schema version, size bound, authentication/session requirement, authorization scope, sequence/cursor semantics and failure behavior.
3. No API field allows the remote client to assert principal, role, policy decision, device trust, origin or audit actor.
4. Task submission, idempotency, cancellation, status projection, event replay and snapshot recovery use consistent identifiers and state definitions.
5. Every mutation retry performs fresh authorization and follows the approved idempotency/reconciliation contract.
6. DENY, REQUIRE_APPROVAL, timeout, unavailable, malformed, unknown, expired, stale, revoked and global-disable outcomes have explicit fail-closed behavior and zero-dispatch evidence requirements.
7. Remote approval, pause/resume, remote desktop, shell, D-Bus, Polkit, privileged broker and public relay are either explicitly excluded from v1 or separately approved through their own threat and contract gates.
8. Threat-model abuse cases and assurance claims map to concrete tests; specified tests are not represented as executed evidence.
9. The OpenAPI document, WebSocket contract, schemas, decision register, traceability matrix and test vectors carry one consistent version/revision identifier.
10. Breaking changes trigger the documented contract change process and re-review by every affected owner.

## 5. Machine-readable freeze manifest template

The following YAML is a blank evidence manifest template, not a declaration of current approvals. Keep unknown values null; do not replace them with guessed values. A future validator can reject any mandatory gate that is not `ACCEPTED` or an approved `NOT_APPLICABLE`.

```yaml
manifest_version: 1
contract:
  name: tusker-remote-control
  version: null
  source_commit: null
  openapi_sha256: null
  websocket_contract_sha256: null
  schema_bundle_sha256: null
freeze_decision: NO_GO
gates:
  CF-AEG-01: {state: OPEN, owner: AEGIS-06, decision_ref: null, evidence_refs: []}
  CF-AEG-02: {state: OPEN, owner: AEGIS-06, decision_ref: null, evidence_refs: []}
  CF-AEG-03: {state: OPEN, owner: AEGIS-06, decision_ref: null, evidence_refs: []}
  CF-AEG-04: {state: OPEN, owner: AEGIS-06, decision_ref: null, evidence_refs: []}
  CF-AEG-05: {state: OPEN, owner: AEGIS-06, decision_ref: null, evidence_refs: []}
  CF-AEG-06: {state: OPEN, owner: AEGIS-06, decision_ref: null, evidence_refs: []}
  CF-TUS-01: {state: REVISE, owner: TUSKER-04, decision_ref: null, evidence_refs: []}
  CF-TUS-02: {state: REVISE, owner: TUSKER-04, decision_ref: null, evidence_refs: []}
  CF-TUS-03: {state: REVISE, owner: TUSKER-04, decision_ref: null, evidence_refs: []}
  CF-TUS-04: {state: REVISE, owner: TUSKER-04, decision_ref: null, evidence_refs: []}
  CF-TUS-05: {state: REVISE, owner: TUSKER-04, decision_ref: null, evidence_refs: []}
  CF-TUS-06: {state: REVISE, owner: TUSKER-04, decision_ref: null, evidence_refs: []}
  CF-TUS-07: {state: DEFER, owner: TUSKER-04, decision_ref: null, evidence_refs: []}
  CF-NOV-01: {state: OPEN, owner: NOVA-02, decision_ref: null, evidence_refs: []}
  CF-NOV-02: {state: OPEN, owner: NOVA-02, decision_ref: null, evidence_refs: []}
  CF-NOV-03: {state: OPEN, owner: NOVA-02, decision_ref: null, evidence_refs: []}
  CF-NOV-04: {state: OPEN, owner: NOVA-02, decision_ref: null, evidence_refs: []}
  CF-PIL-01: {state: OPEN, owner: PILOT-08, decision_ref: null, evidence_refs: []}
  CF-PIL-02: {state: EVIDENCE_PENDING, owner: PILOT-08, decision_ref: null, evidence_refs: []}
  CF-REL-01: {state: OPEN, owner: PHOENIX-10/ATLAS-01, decision_ref: null, evidence_refs: []}
validation:
  openapi_validator: NOT_RUN
  websocket_schema_validator: NOT_RUN
  traceability_check: NOT_RUN
  contract_consistency_check: NOT_RUN
  reviewer_approvals: []
```

## 6. Freeze decision rule

The freeze decision is **GO** only when:
- Every mandatory gate has an authorized ACCEPTED disposition for the exact contract revision, or a justified NOT_APPLICABLE disposition approved by all affected owners.
- All required artifacts and machine-readable evidence references are present and immutable.
- Cross-artifact consistency checks pass.
- Contract/schema validators and traceability checks have reproducible passing outputs.
- Security, Core, UX and release reviewers sign the same revision.
- No unresolved P0 security or contract finding remains.

Otherwise the decision is **NO-GO**. A GO for contract freeze is not automatically authorization to deploy; implementation, security verification and release gates remain separate.

## 7. Current checkpoint

At authoring:
- AEGIS-06: no owner-authored response/sign-off on issue #13.
- TUSKER-04: draft v0.1 REVISE/DEFER decisions only; no frozen API.
- NOVA-02: no owner-authored response/sign-off on issue #15.
- Umbrella issue #1: no owner-authored response.
- OpenAPI validation: not run; WebSocket contract validator: not run.
- Contract freeze: **NO-GO**.
- Runtime implementation and test execution remain blocked.
