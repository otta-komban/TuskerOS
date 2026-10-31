# AEGIS-06 Phase 1 Checklist

**Branch:** `06-security-gatekeeper`  
**Owner:** AEGIS-06  
**Status:** In progress

## P0 — Discovery and requirements

- [x] Read master execution blueprint and AEGIS-06 P0–P7 scope.
- [x] Confirm permanent branch exists and inspect branch against main.
- [x] Confirm initial repository baseline and identify missing planning/code structure.
- [x] Draft asset inventory and security objectives.
- [x] Draft threat actors, attack surfaces and trust boundaries.
- [x] Draft action risk taxonomy and default decision rules.
- [x] Draft initial security invariants and risk register.
- [ ] Review threat model with TUSKER-04.
- [ ] Review OS-tool threat surface with NEXUS-07.
- [x] Review remote identity/approval threats with PILOT-08; DEC-AEG-001–008 are recorded as owner decisions, with remote approval disabled for MVP and implementation still gated.
- [ ] Review extension/marketplace threat surface with FORGE-09.
- [ ] Review OS security mechanisms and service packaging with ATLAS-01.
- [ ] Finalize risk owners, likelihood/impact ratings and acceptance criteria.

## P1 — Architecture and contracts

- [x] Review ORBIT-05 provider and ModelStore security boundary; record AISEC-001–006 findings and executable acceptance tests in `security/AI_RUNTIME_SECURITY_REVIEW.md`. Review is complete; ORBIT remediation and runtime evidence remain pending.

- [x] Draft deterministic policy-service architecture.
- [x] Define DENY / ALLOW / REQUIRE_APPROVAL semantics.
- [x] Draft action-bound, one-time approval requirements.
- [x] Draft narrow privileged broker boundary.
- [x] Evaluate initial roles for Polkit, bubblewrap, Podman, systemd hardening and SELinux.
- [x] Draft audit event and failure semantics.
- [x] Draft cancellation, compensation, quarantine and recovery semantics.
- [x] Publish draft JSON Schema 2020-12 envelopes for action proposal, policy decision, approval request, audit event and operation registration.  
- [x] Publish language-neutral policy conformance vectors; execution remains pending.
- [x] Publish authorization lifecycle and broker conformance vectors; execution remains pending.
- [x] Publish deterministic risk classification, fail-closed evaluation and canonical digest specification.
- [x] Obtain TUSKER-04 acceptance of proposal/decision field semantics and RFC 8785 + SHA-256 binding as the integration baseline; transport remains open.
- [ ] Agree tool registration and execution contracts with NEXUS-07.
- [x] Expand security test matrix for atomic approval consumption, replay, concurrency and unknown broker outcomes.  
- [ ] Confirm operation registry schema, ownership, versioning and review process with NEXUS-07.
- [x] Record PILOT-08 remote principal/session and approval security decisions in `REMOTE_DEVICE_SECURITY_CONTRACT.md`; producer/runtime implementation and cross-agent contract migration remain pending.
- [ ] Agree extension capability and sandbox manifest with FORGE-09.
- [ ] Agree desktop approval UI trust boundary with NOVA-02.
- [ ] Agree system service/Polkit/SELinux packaging with ATLAS-01.
- [x] Record TUSKER-04 review: ten integration invariants accepted as baseline; schema/canonicalization remain draft pending compatibility review.
- [ ] Confirm authorization reference transport, token audience and one-time nonce semantics with NEXUS-07.
- [x] Record TUSKER-04 clarifications: UUID task/step producer IDs are compatible; mutation idempotency is mandatory at registry/policy boundary; malformed or mismatched ALLOW evidence fails closed; DENY null fields are intentional.
- [x] Publish authorization lifecycle, operation registry governance and privileged broker security contract drafts.
- [x] Specify post-approval fresh ALLOW + opaque authorization_ref handoff; approval_request_id remains correlation-only and cannot be consumed by broker.
- [x] Define typed authorization-consume outcomes and add approval-handoff/audit-failure/replay conformance fixtures; execution remains pending.
- [x] Publish privileged-operations release gate with cross-agent evidence owners and mandatory negative-test acceptance criteria.
- [x] Perform JSON syntax and fixture-internal structural audit; Draft 2020-12 validation and runtime execution remain pending.
- [x] Review all four main-only commits and document the net-zero revert sequence; no merge/rebase performed.
- [x] Record proposed broker integration defaults and explicit owner-response checklist; decisions remain unaccepted pending NEXUS-07.  
- [x] Audit approval-request and audit-event schema consistency against normative contract; document missing approval binding and correlation requirements.
- [x] Reconcile SEC-SCHEMA-002 by requiring `task_id` and `step_id` keys in audit events while preserving nullable values; producer/standards validation remains pending.  
- [ ] Record remaining accepted architecture decisions and unresolved contract blockers.  
- [x] Draft `security/AUDIT_EVENT_SCHEMA_PROPOSAL.md` for SEC-SCHEMA-003: require trusted `registry_version` in a separately versioned audit-event 0.2.0 envelope; producer-owner acceptance remains pending.
- [ ] Resolve SEC-SCHEMA-003 with NEXUS-07/TUSKER-04; implement producer migration and positive/negative 0.2.0 validation after owner agreement.

## Exit evidence

- [ ] Threat model reviewed and accepted.
- [ ] Trust-boundary diagram finalized.
- [ ] Risk/action matrix reviewed by dependent agents.
- [ ] Policy, approval, broker and audit contracts versioned.
- [ ] Fedora mechanism compatibility evidence captured.
- [ ] P1 design review complete; no implementation claim until tests exist.

## Integration tracking

- [x] Review `main`-only divergence commits and document findings in `security/MAIN_BRANCH_DIVERGENCE_REVIEW.md`.
- [ ] Obtain NEXUS-07 authorization/broker implementation decisions before freezing privileged runtime contracts.  
- [x] Publish `security/BROKER_INTEGRATION_DECISIONS.md` with proposed (not accepted) defaults for authorization evidence, atomic consume, registry ownership, IPC identity and UNKNOWN/idempotency.  
- [x] Publish draft approval-request schema v0.2.0 with required session/device, registry-version, resource-scope and precondition-digest bindings for SEC-SCHEMA-001; runtime-owner acceptance remains pending.
- [ ] Obtain NEXUS-07/TUSKER-04/PILOT-08/ATLAS-01 acceptance of binding provenance, v0.1.0-to-v0.2.0 migration and consume-time comparison.
- [x] Add automated Draft 2020-12 meta-schema checks and audit-event positive/negative envelope tests; CI run 41126223487 passed (17 tests).
- [x] Add positive/negative approval-request v0.2.0 binding-envelope cases, reject caller-supplied principal fields, and deduplicate schema loading in `security/tests/test_security_schemas.py`; branch CI run 41127219083 passed (33 tests).
- [ ] Confirm approval-binding producer/UI/authority semantics, including trusted digest derivation and canonical resource normalization; schema-only validation is insufficient.  


- [ ] Obtain producer-owner agreement on SEC-SCHEMA-004: require executor_id and reason_code keys with explicit-null semantics in the same candidate audit-event v0.2.0 revision as registry_version; add schema and producer tests.


- [x] Implement separate candidate `audit-event-0.2.0.schema.json` combining required trusted `registry_version`, required nullable `executor_id`/`reason_code`, and denial/failure reason-code condition; active v0.1.0 unchanged.
- [x] Add Draft 2020-12 positive/negative envelope tests for candidate v0.2.0 and cross-version rejection; first candidate run 41128179870 passed 47 tests.
- [ ] Obtain NEXUS-07/TUSKER-04 acceptance of registry-version provenance, executor/reason lifecycle semantics and audit producer migration before promoting candidate v0.2.0.


- [ ] Resolve SEC-SCHEMA-005: define truthful audit representation for request-created/registry-failure events when no trusted registry version exists; require concrete registry version for ALLOW/CONSUMED/dispatch.


- [x] Specify candidate registry-resolution state: resolved requires a concrete version; unavailable permits only pre-evaluation request receipt or explicit fail-closed registry denial; no authorization/dispatch with unavailable status.
- [x] Add schema tests for registry-unavailable request/denial, resolved-null, unavailable-with-version, unavailable authorization and wrong reason code; run 41128922282 passed 54 tests after correcting two conditional-rule regressions found by earlier CI.
- [x] Extend C0026 negative coverage to all 13 post-request event classes (authorization, execution, cancellation, UNKNOWN, compensation and approval); run 41130628432 passed 67 tests in 0.58s.
- [ ] Obtain NEXUS-07/TUSKER-04 acceptance of registry_status provenance and event lifecycle before promoting audit-event v0.2.0.


- **C0030 — Audit event lifecycle/status consistency:** candidate v0.2.0 constrains each of 15 event types to its defined result status; positive and negative schema tests added. Candidate remains unaccepted pending producer-owner review; no runtime behavior is claimed.

- [ ] Resolve SEC-SCHEMA-006 with NEXUS-07/TUSKER-04: agree candidate audit-event names and result mappings for presentation, dismissal, invalidation, revocation, consume acceptance/rejection and reconciliation; then add schema/producer tests. Active v0.1.0 and candidate v0.2.0 remain unapproved for producer migration.

- [ ] Obtain NEXUS-07/TUSKER-04 agreement on candidate v0.2.0 package `transaction_id` + `snapshot_digest` correlation fields and producer ownership; confirm AEGIS action digest is recomputed independently with RFC 8785 JCS, not copied from FORGE `plan_digest`.

- [ ] **C0044 — FORGE-09 re-review:** reason_code remains optional in Python transition/history validation despite schema requirement for rejected/cancelled events; follow-up posted on issue #29 (comment 6534092148). Await FORGE-owned fix and re-review; no cross-branch edits or test claims.

- [x] **C0049 — NEXUS-07 public invocation schema re-review:** verified the public schema now omits caller-reachable `authorization_context` and rejects undeclared fields; posted issue #17 comment 6534567960. Remaining: stale public example still includes the field; add explicit smuggling-negative and trusted-context positive tests, define typed broker-internal injection/consume API, and provide authenticated peer/principal binding plus consume-before-dispatch runtime evidence. Source review only; no NEXUS files changed or tests executed.


- [ ] **AISEC-007 — Model manifest path boundary:** constrain `files[].filename` to safe relative paths; reject traversal/absolute/drive/backslash forms, duplicate names and target-filesystem normalization collisions; add schema and runtime containment/race tests. Owner follow-up posted to ORBIT-05 issue #28 (comment 6534573189). Current finding is source-review only; no ModelStore runtime exploit or test is claimed.

- [x] **C0053 — Remote audit data-minimization regression:** expanded AUD-REMOTE-006 to 11 negative schema cases for raw device/session identifiers, key/credential/signature/pairing material and task/prompt/completion payload fields. CI run 41165765657 passed on test commit 98aff2c0b4393e40e3661946d8fd16b59a1a8b1d. Schema-only evidence; live adapter redaction, durable audit storage and access-control/integrity remain unverified. Candidate v0.2.0 producer migration remains pending NEXUS-07/TUSKER-04 agreement; remote approval disabled for MVP.


- [ ] **SEC-SCHEMA-007 — Policy-decision constraints vocabulary:** `policy-decision.schema.json` currently accepts any nested object under `constraints`; define the bounded typed vocabulary with policy-engine/broker owners, reject unknown keys, and add schema plus consumer fail-closed tests. Tracked in issue #31. No schema change or runtime behavior claimed.

- [x] **SEC-SCHEMA-007 interim fail-closed contract:** documented that producers emit only an empty `constraints` object and consumers reject non-empty/unsupported constraint data until policy-engine and broker owners ratify a bounded vocabulary; added POL-CON-001–006 acceptance criteria. This is documentation/contract hardening only. The active schema still permits arbitrary nested constraints, consumer enforcement is unverified, and SEC-SCHEMA-007 remains open pending owner agreement and executable tests.

