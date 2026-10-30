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
- [ ] Review remote identity/approval threats with PILOT-08.
- [ ] Review extension/marketplace threat surface with FORGE-09.
- [ ] Review OS security mechanisms and service packaging with ATLAS-01.
- [ ] Finalize risk owners, likelihood/impact ratings and acceptance criteria.

## P1 — Architecture and contracts

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
- [ ] Agree remote principal/session and approval binding with PILOT-08.
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
