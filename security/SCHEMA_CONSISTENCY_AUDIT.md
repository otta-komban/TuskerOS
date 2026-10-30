# Security contract/schema consistency audit

**Owner:** AEGIS-06  
**Branch:** `06-security-gatekeeper`  
**Status:** Draft contract review; runtime-owner acceptance remains pending  
**Scope:** Compare normative security contracts, approval/audit schemas, lifecycle requirements and validation evidence.

## Executive result

Three schema/prose gaps have been tracked:

- **SEC-SCHEMA-001 — approval binding representation (High):** Remediated in draft approval-request schema v0.2.0 with a required nested `binding` object. Runtime-owner compatibility, trusted derivation and consume-time enforcement remain open.
- **SEC-SCHEMA-002 — audit correlation requiredness (Medium):** Reconciled in audit-event schema v0.1.0 by requiring both `task_id` and `step_id`, while preserving nullable values.
- **SEC-SCHEMA-003 — registry version absent from audit events (Medium):** Still open. The lifecycle requires policy and registry version evidence, but audit-event v0.1.0 contains only `policy_version`. A separately versioned v0.2.0 proposal exists in `security/AUDIT_EVENT_SCHEMA_PROPOSAL.md`; the active v0.1.0 schema was not silently changed.

## SEC-SCHEMA-001 — approval binding representation

**Original gap:** The lifecycle requires approval to bind authenticated principal/session/device, operation, canonical resource scope, policy version, registry version, precondition snapshot and expiry. The original approval-request v0.1.0 schema did not represent session/device, registry, resource or precondition bindings.

**Draft remediation:** `security/schemas/approval-request.schema.json` is now draft v0.2.0. It requires a `binding` object containing:

- `session_binding` and `device_binding`: SHA-256 binding strings, not raw identifiers or proof of identity;
- `registry_version`: exact immutable operation-registry revision;
- `resource_scope`: non-empty unique array of canonical resource identifier strings;
- `precondition_digest`: SHA-256 digest of the relevant precondition snapshot.

The top-level `action_digest` remains required. The schema shape does not prove that values came from trusted sources, that resource identifiers are canonically normalized, or that digests cover the complete action. The authority and broker must derive/recheck these values from trusted context.

**Compatibility:** v0.1.0 and v0.2.0 are distinct draft wire formats. Do not silently reinterpret v0.1.0 messages as v0.2.0. Producer, approval UI, authority and broker owners must accept the migration and semantic binding rules before contract freeze.

## SEC-SCHEMA-002 — audit correlation fields

**Original gap:** The normative security contract listed `task_id` and `step_id` as minimum audit fields, but the original audit schema did not require their presence.

**Resolution:** Both keys are members of the audit-event v0.1.0 top-level `required` array. Their value types remain `string` or `null`; producers must emit explicit `null` when correlation is unavailable rather than omit either key.

## SEC-SCHEMA-003 — registry version absent from audit events

**Gap:** `security/AUTHORIZATION_LIFECYCLE.md` requires audit records to include policy and registry version. Audit-event v0.1.0 requires `policy_version` but has no `registry_version` property.

**Risk:** An audit record cannot unambiguously identify the exact operation-registry snapshot that governed the authorization, weakening incident reconstruction and analysis of registry changes.

**Proposal:** `security/AUDIT_EVENT_SCHEMA_PROPOSAL.md` proposes a separate audit-event v0.2.0 schema with required non-empty `registry_version` (maximum 128 characters). The value must originate from the trusted immutable registry snapshot used during policy evaluation and match the version rechecked at authorization consumption. Policy and registry versions remain distinct.

**Status:** Proposal only. Do not change the active v0.1.0 schema until NEXUS-07/TUSKER-04 producer and consumer owners confirm the source, semantics and migration plan.

## Validation evidence

- GitHub Actions run [41126223487](https://github.com/otta-komban/TuskerOS/actions/runs/41126223487): **17 passed**; all five Draft 2020-12 schemas checked and audit-event correlated/null/negative envelope cases exercised.
- GitHub Actions run [41126585567](https://github.com/otta-komban/TuskerOS/actions/runs/41126585567): **32 passed**; added positive and negative approval-request v0.2.0 binding-envelope cases.
- Branch-head run [41126895122](https://github.com/otta-komban/TuskerOS/actions/runs/41126895122): **32 passed in 0.51s** on Python 3.12.

These tests validate schema structure and representative JSON envelopes. They do not test a live audit producer, durable audit persistence/integrity, trusted identity derivation, approval UI display, authorization-store atomicity, broker IPC, or privileged runtime execution.

## Required follow-up

1. Obtain NEXUS-07 acceptance of the authorization lookup/consume transport, durable atomicity, peer-identity injection and registry-version source.
2. Obtain TUSKER-04 producer acceptance of the v0.2.0 approval binding and audit correlation/version fields.
3. Obtain NOVA-02 approval UI confirmation that the exact operation and resource scope are presented from trusted metadata.
4. Obtain PILOT-08 confirmation of authoritative session/device binding derivation and revocation behavior.
5. Add producer/consumer tests for binding derivation, canonical resource normalization, consume-time revalidation, registry-version match, replay and concurrency.
6. Decide and version the audit-event v0.2.0 migration only after producer-owner review.

**Release implication:** Keep privileged execution blocked until approval bindings are enforced by trusted runtime components, audit correlation/version requirements are implemented by producers, and mandatory negative tests pass against the release candidate.
