# PILOT-08 Contract Coverage & Change-Control Package

**Status:** Draft v0.1 — traceability and governance only; not owner approval or test evidence  
**Owner:** PILOT-08 | **Branch:** `08-remote-control`  
**Baseline:** OpenAPI 3.1.0 / 0.1.0-draft; requirements matrix v0.1; protocol specification v0.1; readiness review v0.1  
**Implementation gate:** **CLOSED — NO-GO**

## 1. Coverage summary

The current protocol specification contains exactly 72 scenarios. This document maps every scenario ID to the existing product requirement IDs, proposed API/component surface and relevant C0007 finding IDs. A mapping is a traceability relationship, not proof that an endpoint/schema exists or that a test has run.

| Scenario family | IDs | Count | Current evidence state |
|---|---|---:|---|
| PAIR | PAIR-001..010 | 10 | Specified only; no execution evidence |
| SESS | SESS-001..014 | 14 | Specified only; no execution evidence |
| AUTH | AUTH-001..010 | 10 | Specified only; no execution evidence |
| TASK | TASK-001..016 | 16 | Specified only; no execution evidence |
| EVT | EVT-001..012 | 12 | Specified only; no execution evidence |
| NET | NET-001..010 | 10 | Specified only; no execution evidence |
| **Total** | **PAIR + SESS + AUTH + TASK + EVT + NET** | **72** | **0 executed; 0 passed claimed** |

Counts reconcile to the source specification: 10 + 14 + 10 + 16 + 12 + 10 = 72. Remote-approval future scenarios are conditional and excluded from the 72.

## 2. Scenario-level traceability

Columns:
- **Requirement IDs** refer to `REQUIREMENTS-TRACEABILITY-MATRIX.md`.
- **Surface** names the proposed route, local UI/service boundary, Core adapter or transport surface. Routes are proposals, not approved implementation instructions.
- **Finding IDs** refer to `IMPLEMENTATION-READINESS-REVIEW.md` API-01 through API-24.
- **Evidence state** deliberately says “Specified; not run” for every row because no tests have been executed.

| Scenario | Requirement IDs | Proposed route / component surface | Readiness findings | Evidence state |
|---|---|---|---|---|
| PAIR-001 | RC-PAIR-01; RC-PAIR-02; RC-AUDIT-01 | POST /pairing/challenges (local); POST /pairing/complete; local confirmation | API-02; API-20; API-24 | Specified; not run |
| PAIR-002 | RC-PAIR-01 | POST /pairing/challenges (local auth boundary) | API-02; API-20 | Specified; not run |
| PAIR-003 | RC-PAIR-02 | POST /pairing/complete; local confirmation | API-02; API-20 | Specified; not run |
| PAIR-004 | RC-PAIR-02 | POST /pairing/complete | API-02; API-18 | Specified; not run |
| PAIR-005 | RC-PAIR-01; RC-PAIR-02 | Pairing challenge state / POST /pairing/complete | API-02; API-18 | Specified; not run |
| PAIR-006 | RC-PAIR-02 | Pairing challenge atomic consume | API-02; API-18 | Specified; not run |
| PAIR-007 | RC-PAIR-02 | POST /pairing/complete | API-02; API-18 | Specified; not run |
| PAIR-008 | RC-PAIR-01; RC-TRANSPORT-02 | Pairing/auth rate-limit middleware | API-02; API-21 | Specified; not run |
| PAIR-009 | RC-PAIR-01; RC-AUDIT-01 | Local pairing display; secret-safe diagnostics | API-02; API-21 | Specified; not run |
| PAIR-010 | RC-RECOVERY-01; RC-REVOKE-01 | Local global-disable control; session/device service | API-07; API-20 | Specified; not run |
| SESS-001 | RC-DEVICE-01; RC-SESSION-01 | POST /sessions | API-01; API-02 | Specified; not run |
| SESS-002 | RC-DEVICE-01; RC-SESSION-01 | POST /sessions | API-01; API-02 | Specified; not run |
| SESS-003 | RC-DEVICE-01; RC-SESSION-01 | POST /sessions | API-01 | Specified; not run |
| SESS-004 | RC-DEVICE-01; RC-REVOKE-01 | POST /sessions; device registry | API-01; API-05 | Specified; not run |
| SESS-005 | RC-SESSION-01; RC-AUTH-01 | All protected /api/v1 operations | API-01; API-18 | Specified; not run |
| SESS-006 | RC-SESSION-01 | Session proof / protected HTTP and WSS | API-01; API-13 | Specified; not run |
| SESS-007 | RC-SESSION-01 | Session rotation (if approved) | API-03; API-01 | Specified; not run |
| SESS-008 | RC-SESSION-01; RC-REVOKE-01 | DELETE /sessions/current | API-01; API-05 | Specified; not run |
| SESS-009 | RC-REVOKE-01; RC-RECOVERY-01 | DELETE /devices/{device_id}; session registry | API-05; API-07 | Specified; not run |
| SESS-010 | RC-REVOKE-01; RC-EVENT-01 | DELETE /devices/{device_id}; WSS gateway | API-05; API-13; API-14 | Specified; not run |
| SESS-011 | RC-SESSION-01; RC-REVOKE-01 | Session persistence/restart lifecycle | API-01; API-03 | Specified; not run |
| SESS-012 | RC-SESSION-01 | Server-side session expiry | API-01 | Specified; not run |
| SESS-013 | RC-AUTH-01; RC-TASK-01 | AEGIS policy adapter before Core dispatch | API-18; API-19 | Specified; not run |
| SESS-014 | RC-SESSION-01; RC-AUDIT-01 | Credential storage, URL/log/trace/error surfaces | API-01; API-18; API-21 | Specified; not run |
| AUTH-001 | RC-DEVICE-01; RC-AUTH-01; RC-TASK-01 | POST /tasks; authenticated principal derivation | API-10; API-11 | Specified; not run |
| AUTH-002 | RC-AUTH-01; RC-PRIV-01 | All protected routes; reject client authority claims | API-10; API-18 | Specified; not run |
| AUTH-003 | RC-AUTH-01; RC-TASK-01; RC-AUDIT-01 | POST /tasks; server-derived origin/context | API-10; API-11 | Specified; not run |
| AUTH-004 | RC-AUTH-01; RC-TASK-03 | GET /tasks/{task_id}; owner-scoped Core projection | API-08; API-10; API-18 | Specified; not run |
| AUTH-005 | RC-AUTH-01; RC-TASK-04 | Proposed cancel operation through Core | API-05; API-18; API-19 | Specified; not run |
| AUTH-006 | RC-AUTH-01; RC-TASK-01 | AEGIS policy adapter before mutation | API-18; API-19 | Specified; not run |
| AUTH-007 | RC-AUTH-01; RC-STATUS-01 | Protected status/task routes; policy error mapping | API-08; API-18; API-19 | Specified; not run |
| AUTH-008 | RC-AUTH-01; RC-SESSION-01 | Protected routes; fresh policy evaluation | API-01; API-18 | Specified; not run |
| AUTH-009 | RC-AUTH-01; RC-TASK-02 | POST /tasks retry path; fresh authorization | API-12; API-19 | Specified; not run |
| AUTH-010 | RC-PRIV-01 | Remote route inventory / negative routing | API-16; API-17; intentional prohibition | Specified; not run |
| TASK-001 | RC-TASK-01; RC-AUTH-01 | POST /tasks | API-10; API-11; API-18 | Specified; not run |
| TASK-002 | RC-TASK-02 | POST /tasks; Idempotency-Key | API-12; API-18 | Specified; not run |
| TASK-003 | RC-TASK-02 | POST /tasks; idempotency store/Core | API-12 | Specified; not run |
| TASK-004 | RC-TASK-02 | POST /tasks; idempotency conflict | API-12; API-18 | Specified; not run |
| TASK-005 | RC-TASK-02; RC-PRIV-01 | POST /tasks; principal-scoped idempotency namespace | API-12 | Specified; not run |
| TASK-006 | RC-TASK-01; RC-PRIV-01 | POST /tasks; TaskSubmission additionalProperties:false | API-10 | Specified; not run |
| TASK-007 | RC-TASK-01; RC-TRANSPORT-02 | POST /tasks; body/text/context bounds | API-21; API-10 | Specified; not run |
| TASK-008 | RC-TASK-01; RC-TASK-03 | POST /tasks; Core context-ref authorization | API-10; API-18 | Specified; not run |
| TASK-009 | RC-TASK-04; RC-AUTH-01 | Proposed POST /tasks/{task_id}/cancel; Core cancel | API-05; API-18; API-19 | Specified; not run |
| TASK-010 | RC-TASK-04 | Proposed POST /tasks/{task_id}/cancel; terminal-state conflict | API-05; API-10; API-18 | Specified; not run |
| TASK-011 | RC-TASK-05 | No MVP endpoint; explicit unsupported capability | API-06 intentional omission | Specified; not run |
| TASK-012 | RC-TASK-02; RC-TASK-01 | POST /tasks; dispatch outcome mapping | API-12; API-19 | Specified; not run |
| TASK-013 | RC-TASK-02; RC-TASK-01 | POST /tasks; unknown outcome reconciliation | API-12; API-19 | Specified; not run |
| TASK-014 | RC-TASK-02 | Proposed idempotency/task reconciliation read | API-12; API-15; API-18 | Specified; not run |
| TASK-015 | RC-TASK-01; RC-AUTH-01 | POST /tasks; Core/policy availability handling | API-18; API-19 | Specified; not run |
| TASK-016 | RC-AUDIT-01; RC-TASK-01 | POST /tasks; trusted Core/audit context propagation | API-11; API-18 | Specified; not run |
| EVT-001 | RC-TASK-03; RC-EVENT-01 | GET /tasks/{task_id} | API-08; API-10 | Specified; not run |
| EVT-002 | RC-TASK-03; RC-AUDIT-01 | GET /tasks/{task_id}; redacted projection | API-08; API-10 | Specified; not run |
| EVT-003 | RC-EVENT-01 | WSS /events; TaskEvent envelope | API-13; API-14 | Specified; not run |
| EVT-004 | RC-EVENT-01 | WSS /events; stable event identity/deduplication | API-13; API-14 | Specified; not run |
| EVT-005 | RC-EVENT-02 | WSS /events; snapshot + cursor resync | API-14; API-15 | Specified; not run |
| EVT-006 | RC-EVENT-02 | WSS /events; cursor replay | API-13; API-14; API-15 | Specified; not run |
| EVT-007 | RC-EVENT-02 | WSS /events; stale cursor reset | API-14; API-15 | Specified; not run |
| EVT-008 | RC-AUTH-01; RC-TASK-03; RC-EVENT-01 | WSS /events; authorized resource subscription | API-08; API-13; API-14 | Specified; not run |
| EVT-009 | RC-REVOKE-01; RC-EVENT-01 | WSS /events; expiry/revocation enforcement | API-05; API-13; API-14 | Specified; not run |
| EVT-010 | RC-TRANSPORT-02 | WSS handshake Origin validation | API-13; API-21 | Specified; not run |
| EVT-011 | RC-TRANSPORT-02 | WSS connection/frame/concurrency limits | API-13; API-21 | Specified; not run |
| EVT-012 | RC-AUTH-01; RC-PRIV-01; RC-EVENT-01 | WSS event delivery; mutation requires fresh protected request | API-13; API-16 | Specified; not run |
| NET-001 | RC-TRANSPORT-01 | Listener configuration / deployment | API-21 | Specified; not run |
| NET-002 | RC-TRANSPORT-01; RC-RECOVERY-01 | Explicit private-network opt-in / local configuration | API-07; API-21 | Specified; not run |
| NET-003 | RC-TRANSPORT-01 | Deployment/firewall/router behavior | API-21 | Specified; not run |
| NET-004 | RC-TRANSPORT-02 | TLS listener/certificate validation | API-21 | Specified; not run |
| NET-005 | RC-TRANSPORT-02 | Host/forwarded-header validation | API-21 | Specified; not run |
| NET-006 | RC-TRANSPORT-02 | WSS Origin allowlist | API-13; API-21 | Specified; not run |
| NET-007 | RC-TRANSPORT-02; RC-PAIR-01 | Pairing/auth/task rate limits | API-21 | Specified; not run |
| NET-008 | RC-TRANSPORT-02; RC-TASK-01 | Header/body/frame limits | API-10; API-13; API-21 | Specified; not run |
| NET-009 | RC-TRANSPORT-02 | Protocol negotiation/version policy | API-22 | Specified; not run |
| NET-010 | RC-AUDIT-01; RC-TRANSPORT-02 | Secret-safe logs/diagnostics | API-21; API-18 | Specified; not run |

## 3. Requirement coverage roll-up

This roll-up shows which scenario families exercise each requirement. A requirement with no direct scenario in the existing 72 is called out rather than silently considered covered.

| Requirement | Scenario coverage | Coverage assessment / gap |
|---|---|---|
| RC-PAIR-01 | PAIR-001, 002, 005, 008, 009 | Pair initiation, local auth, replay, rate and display/log leakage covered by specification. |
| RC-PAIR-02 | PAIR-001, 003–008 | Proof, confirmation, expiry, replay, concurrency and binding specified. |
| RC-DEVICE-01 | SESS-001–004; AUTH-001–004 | Identity binding and client spoofing covered. Device inventory pagination/visibility needs additional cases. |
| RC-SESSION-01 | SESS-001–008, 011–014; AUTH-001–003, 008 | Credential, expiry, replay, logout, restart and policy boundary specified. Session rotation semantics need owner decision. |
| RC-REVOKE-01 | SESS-004, 008–010; EVT-009 | Device/session revoke and active stream termination specified; propagation target unresolved. |
| RC-AUTH-01 | SESS-005, 013; AUTH-001–009; TASK-009; EVT-008, 012 | Protected reads/mutations, spoofing, policy denial/failure and fresh authorization specified. Authorization pagination/list filtering needs explicit cases. |
| RC-STATUS-01 | AUTH-007, 008; NET-010 | Minimal status privacy is only indirectly exercised; add direct positive schema and field-redaction cases before implementation. |
| RC-TASK-01 | TASK-001, 006–008, 012, 015, 016; AUTH-003, 004 | Core submission boundary, untrusted input, bounds, references, failure and context propagation specified. |
| RC-TASK-02 | TASK-002–005, 012–014; AUTH-009 | Idempotency and uncertain dispatch specified; durable restart/retention needs stronger explicit fault-injection cases. |
| RC-TASK-03 | TASK-008; EVT-001, 002, 008; AUTH-004 | Authorized snapshots and redaction specified; list pagination and per-field policy matrix need direct cases. |
| RC-TASK-04 | TASK-009, 010, 013; AUTH-005 | Cancel behavior appears in scenarios but endpoint/Core contract is absent; blocked until owner approval. |
| RC-TASK-05 | TASK-011 | Explicit unsupported behavior only; no pause/resume implementation implied. |
| RC-EVENT-01 | EVT-003, 004, 008, 012; EVT-009; SESS-010 | Ordering, duplicates, authorization, event-as-authority and revocation specified. Event type registry/cursor contract open. |
| RC-EVENT-02 | EVT-005–007, 009 | Gap detection, replay, stale cursor and expiry specified; snapshot watermark/replay consistency unresolved. |
| RC-TRANSPORT-01 | NET-001–005, 009 | Listener and network exposure checks specified; deployment profile/certificate model open. |
| RC-TRANSPORT-02 | NET-004–010; EVT-010, 011; PAIR-008; TASK-007 | TLS, Host/Origin, limits, rate and downgrade controls specified; exact parameter bounds await AEGIS. |
| RC-AUDIT-01 | PAIR-001–010; SESS-014; TASK-016; NET-010 | Audit context/secret leakage touched, but exact event-by-event audit completeness and retention tests need AEGIS schema. |
| RC-APPROVAL-01 | No scenario in the 72; conditional future tests in protocol spec §9 | Correctly excluded while approval disabled. Do not add endpoint/tests as MVP until AEGIS approves scope. |
| RC-PRIV-01 | AUTH-010; TASK-006–008; EVT-012 | Privileged surfaces excluded and probed; ensure route inventory negative tests include all prohibited aliases. |
| RC-RECOVERY-01 | PAIR-010; SESS-009–011; NET-001–003 | Disable/revoke/network baseline touched; dedicated lost-device, re-enable and recovery walkthrough scenarios are missing. Add before release test plan. |
| RC-REMOTE-DESKTOP-01 | No scenario in the 72 | Intentional MVP exclusion; separate threat model/test plan required before future proposal. |

### Coverage gaps requiring scenario additions (proposed; not yet inserted into the canonical 72)

1. Device list: owner isolation, revoked-device visibility, pagination and last-seen freshness.
2. Status endpoint: exact allowed fields, unauthorized caller and sensitive host metadata omission.
3. Task list: cursor pagination, stable order, cross-owner filtering and empty/expired cursor.
4. Audit: required event coverage for success, denial, failure, revoke and disable; retention/redaction access.
5. Global disable: race with in-flight pairing/session/task mutation, re-enable behavior and service restart persistence.
6. Lost-device recovery: revoke, confirm all sessions invalid, replacement-device re-pair without implicit trust.
7. Idempotency: concurrent same-key submissions, persistence across restart, retention expiry and authorization change between retries.
8. Snapshot/event race: event emitted between snapshot watermark and replay subscription; no missed update.
9. Error contract: every protected route's 401/403/404/409/429/503 shape and resource non-disclosure.
10. API compatibility: old/new client negotiation, unknown event type, unsupported subprotocol and breaking-version rejection.

Do not renumber existing scenario IDs. New cases receive the next available suffix within a family or a separately versioned suite, and the 72 baseline remains identifiable for historical comparison.

## 4. Finding-to-requirement crosswalk

This crosswalk helps prioritize owner decisions and avoids treating every readiness finding as an endpoint defect.

| Finding IDs | Primary requirement(s) affected | Required owner(s) | Classification |
|---|---|---|---|
| API-01, API-02, API-20 | RC-PAIR-01/02, RC-DEVICE-01, RC-SESSION-01 | AEGIS-06; NOVA-02; PILOT-08 | P0 contract/security blocker |
| API-03, API-04 | RC-SESSION-01, RC-DEVICE-01 | AEGIS-06; PILOT-08 | Lifecycle scope decision |
| API-05, API-19 | RC-TASK-04, RC-AUTH-01 | TUSKER-04; AEGIS-06; PILOT-08 | P0 Core/API blocker |
| API-06 | RC-TASK-05 | TUSKER-04 | Intentional omission pending explicit disposition |
| API-07 | RC-RECOVERY-01, RC-REVOKE-01 | AEGIS-06; NOVA-02; PILOT-08 | P0 local-owner safety control |
| API-08, API-09 | RC-STATUS-01, RC-TASK-03, RC-AUTH-01 | AEGIS-06; TUSKER-04; NOVA-02 | Projection/pagination contract gap |
| API-10, API-11, API-12 | RC-TASK-01/02/03; RC-AUDIT-01 | TUSKER-04; AEGIS-06; PILOT-08 | P0 Core schema/idempotency blocker |
| API-13, API-14, API-15 | RC-EVENT-01/02; RC-REVOKE-01 | TUSKER-04; AEGIS-06; PILOT-08 | P0 WebSocket/replay blocker |
| API-16 | RC-APPROVAL-01 | AEGIS-06 | Intentional omission; disabled by default |
| API-17 | RC-AUDIT-01 | AEGIS-06 | Intentional omission pending privacy decision |
| API-18 | RC-AUTH-01; all mutation/read requirements | AEGIS-06; TUSKER-04; PILOT-08 | Shared error contract gap |
| API-21 | RC-TRANSPORT-01/02 | AEGIS-06; PHOENIX-10; ATLAS-01 as needed | P0 deployment/security blocker |
| API-22 | All versioned API/event requirements | PILOT-08; TUSKER-04; AEGIS-06 | Contract governance gap |
| API-23, API-24 | All requirements | PILOT-08 | Mechanical validation/coverage tasks |

## 5. Contract change-control policy

### 5.1 Change classes

- **Editorial:** spelling, formatting or clarifying prose with no behavioral, security, schema or generated-client effect. PILOT-08 may prepare; one peer review required; no owner decision status changes.
- **Additive non-security:** optional field, new read-only projection or backward-compatible event addition. Requires owning domain engineer review, traceability/test update, schema validation and compatibility review.
- **Behavioral/breaking:** required field, enum/state change, changed response/error semantics, route removal/meaning change, cursor/idempotency/cancellation change, client-visible workflow change. Requires affected domain owner ACCEPT, version impact decision and migration/deprecation plan.
- **Security-sensitive:** authentication, key/proof, pairing, session, authorization, revocation, audit, TLS/Origin/Host, rate/size limits, remote approval, secret/redaction or listener exposure. Requires AEGIS-06 explicit review and ACCEPT regardless of whether the change appears additive.
- **Cross-boundary:** task lifecycle/context/events/Core adapter changes require TUSKER-04; desktop consent/recovery changes require NOVA-02; deployment/service lifecycle changes require PHOENIX-10/ATLAS-01 as applicable; shared integration requires NEXUS-07 only if that boundary is actually used.

### 5.2 Required change record

Every contract change proposal must include:

1. Change ID and author; date; affected contract version and base commit SHA.
2. Motivation and user-visible behavior; scope and explicit non-goals.
3. Change class (editorial/additive/behavioral/security-sensitive/cross-boundary).
4. Exact files, routes, schemas, fields, event types and decision IDs affected.
5. Compatibility analysis: old client/new server and new client/old server behavior.
6. Security/privacy impact, trust-boundary changes, authorization and audit impact.
7. Requirement and scenario coverage delta; added/retired tests with rationale.
8. Rollout, migration, deprecation, rollback and recovery behavior.
9. Required owner reviewers and their explicit ACCEPT/REVISE/DEFER response URLs.
10. Validator/linter/test output and exact tool versions.
11. Final merge commit SHA and superseded contract references.

### 5.3 Review and merge sequence

1. Open a change proposal against the dedicated branch; do not edit an approved contract in place without a reviewable diff.
2. Assign the domain owner(s) from the decision register. Security-sensitive changes always include AEGIS-06.
3. Update, in the same change set, the OpenAPI/schema, WebSocket contract if applicable, requirements matrix, scenario coverage, negative tests and decision register.
4. Run deterministic syntax/schema/lint/compatibility checks. Attach output; do not report a check as passed if it was not run.
5. Obtain explicit ACCEPT from every required owner against the exact commit SHA. Silence or draft comments do not count.
6. Re-run checks on the final candidate commit; resolve all findings or record a formally approved exception with scope/expiry.
7. Merge only through the repository's approved review process; preserve immutable release tags and changelog entry.
8. If a security-sensitive change is discovered after release, follow the security incident/rollback path; do not rely solely on ordinary semantic versioning.

### 5.4 Versioning rules (proposal, pending owner review)

- Keep `0.x.y` while the API is draft; do not call the current draft stable v1.
- Patch: documentation/editorial or non-behavioral correction only.
- Minor: backward-compatible optional fields, new optional capabilities or new event types that old clients can safely ignore.
- Major: breaking request/response/schema changes, state machine changes, changed authorization semantics, incompatible event protocol/cursor semantics, or removal/meaning change of an operation.
- Security fixes may require an urgent patch/minor release, but still require AEGIS review and a recorded compatibility/security rationale.
- Version HTTP API and WebSocket subprotocol/event envelope independently if their compatibility lifecycles differ; publish a compatibility table.
- Never reuse an event type or enum value with a different meaning. Unknown event types must be safely ignored only when explicitly marked optional; otherwise client must negotiate/reject.
- Deprecation requires a published notice, supported overlap window, telemetry/privacy review, migration instructions and removal approval by domain owners.
- Pin generated client/schema artifacts to a contract commit; avoid floating schema downloads in builds.

### 5.5 Decision and release gates

- Draft change: no implementation permission.
- Accepted contract change: permission to update contract artifacts only, unless a separate implementation GO record exists.
- Implementation GO: separate signed P0 decision record, exact approved contract SHA, named owners, passing required tests, no unresolved critical/high finding, rollback plan.
- Release GO: all applicable release security/deployment checks pass on the candidate build and the approved scope is unchanged.
- A later material change to a security-sensitive contract automatically reopens its approval gate.

## 6. Change proposal template

```markdown
# Contract Change Proposal — <CHANGE-ID>

- Base contract version / commit:
- Proposed contract version:
- Author / date:
- Change class:
- Affected decision IDs:
- Required owners:
- Motivation / user-visible behavior:
- Scope / explicit non-goals:
- Affected routes, schemas, event types and fields:
- Security, privacy, authorization and audit impact:
- Requirement coverage delta:
- Scenario coverage delta:
- Compatibility: old client/new server; new client/old server:
- Migration / deprecation:
- Rollback / recovery:
- Validation tools and exact versions:
- Test evidence and build SHA:
- Owner decisions (ACCEPT / REVISE / DEFER + links):
- Final reviewed commit SHA:
- Decision: DRAFT / ACCEPTED-CONTRACT / IMPLEMENTATION-GO / RELEASE-GO
```

## 7. Current coverage and governance decision

**Coverage status:** 72/72 scenario IDs mapped to requirement IDs, proposed surfaces and C0007 readiness findings. This is static traceability coverage only. It does not mean every requirement is adequately tested or that routes/contracts are complete.

**Execution status:** 0 tests executed; 0 passed; 0 failed; 0 blocked-by-runner. The last two categories are zero because no execution was attempted; contract blockers are recorded separately.

**Approval status at C0012:** AEGIS-06 accepted DEC-AEG-001..007 and deferred/disabled DEC-AEG-008 for MVP. TUSKER-04 remains REVISE on DEC-TUS-001..004 and 006..007 and DEFER on 005; NOVA-02 decisions DEC-NOV-001..004 remain open. This supersedes the earlier owner-response snapshot.

**Implementation status:** 0 runtime features; no implementation authorization. Remote approval remains intentionally absent; pause/resume remains excluded unless Core explicitly supports safe checkpoints. No shell, D-Bus, Polkit, privileged broker or direct provider access is permitted.

## 8. Sources and maintenance

- Protocol scenario baseline: `remote-control/verification/PROTOCOL-ACCEPTANCE-AND-NEGATIVE-TESTS.md`.
- Requirement IDs and owners: `remote-control/verification/REQUIREMENTS-TRACEABILITY-MATRIX.md`.
- Finding IDs and P0 criteria: `remote-control/verification/IMPLEMENTATION-READINESS-REVIEW.md`.
- Decision IDs and approval states: `remote-control/verification/CROSS-AGENT-DECISION-REGISTER.md`.
- Draft API baseline: `remote-control/contracts/v1/openapi.yaml`.

Update this package whenever any referenced ID, route, requirement, schema, owner decision or scenario changes. Keep IDs stable; record supersession rather than silently deleting history. Do not claim test execution from a static mapping.


## C0012 — owner-decision refresh (2026-10-31)

The earlier approval snapshot is historical. Current durable evidence is:
- AEGIS-06 accepted DEC-AEG-001..007 and disabled remote approval for MVP (DEC-AEG-008): [issue #13](https://github.com/otta-komban/TuskerOS/issues/13#issuecomment-6534005612).
- TUSKER-04 has not frozen the Core API: DEC-TUS-001..004 and 006..007 remain REVISE; 005 is DEFERRED: [issue #14](https://github.com/otta-komban/TuskerOS/issues/14#issuecomment-6531700289).
- NOVA-02 UX decisions remain open: [issue #15](https://github.com/otta-komban/TuskerOS/issues/15).
- NEXUS final consume integration remains unverified.

The existing 72-scenario mapping and 104 PAIR/SESS/NET conformance cases remain static specifications. No test execution or runtime behavior is claimed. **Contract freeze and implementation remain NO-GO.**
