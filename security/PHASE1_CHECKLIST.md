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
- [ ] Record remaining accepted architecture decisions and unresolved contract blockers.

## Exit evidence

- [ ] Threat model reviewed and accepted.
- [ ] Trust-boundary diagram finalized.
- [ ] Risk/action matrix reviewed by dependent agents.
- [ ] Policy, approval, broker and audit contracts versioned.
- [ ] Fedora mechanism compatibility evidence captured.
- [ ] P1 design review complete; no implementation claim until tests exist.
