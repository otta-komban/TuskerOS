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
- An intermediate run [41126754247](https://github.com/otta-komban/TuskerOS/actions/runs/41126754247) failed during pytest collection because a schema path was passed to `json.loads` without reading the file. The test loader was corrected and duplicate schema loading removed.
- Follow-up run [41126943598](https://github.com/otta-komban/TuskerOS/actions/runs/41126943598): **33 passed in 0.49s**; added a negative test rejecting caller-supplied top-level principal identity.
- Later branch run [41127219083](https://github.com/otta-komban/TuskerOS/actions/runs/41127219083): **33 passed in 0.52s** on Python 3.12.

These tests validate schema structure and representative JSON envelopes. They do not test a live audit producer, durable audit persistence/integrity, trusted identity derivation, approval UI display, authorization-store atomicity, broker IPC, or privileged runtime execution.

## Required follow-up

1. Obtain NEXUS-07 acceptance of the authorization lookup/consume transport, durable atomicity, peer-identity injection and registry-version source.
2. Obtain TUSKER-04 producer acceptance of the v0.2.0 approval binding and audit correlation/version fields.
3. Obtain NOVA-02 approval UI confirmation that the exact operation and resource scope are presented from trusted metadata.
4. Obtain PILOT-08 confirmation of authoritative session/device binding derivation and revocation behavior.
5. Add producer/consumer tests for binding derivation, canonical resource normalization, consume-time revalidation, registry-version match, replay and concurrency.
6. Decide and version the audit-event v0.2.0 migration only after producer-owner review.

**Release implication:** Keep privileged execution blocked until approval bindings are enforced by trusted runtime components, audit correlation/version requirements are implemented by producers, and mandatory negative tests pass against the release candidate.


## Finding SEC-SCHEMA-004 — executor and reason keys are not required

**Severity:** Medium — audit completeness gap  
**Evidence:** Section 7 of `security/SECURITY_CONTRACTS.md` lists `executor_id` and `reason_code` among the minimum audit-event fields. The current `security/schemas/audit-event.schema.json` defines both properties as nullable, but neither appears in the top-level `required` array. The current positive audit fixture supplies both keys, but the negative fixture suite does not test omission of either.

**Risk:** A schema-valid event may omit executor and reason keys entirely. Consumers cannot distinguish an explicitly unavailable value from a producer that failed to emit a minimum field.

**Proposed resolution (not applied):** Require both keys in the separately versioned audit-event v0.2.0 proposal, preserving nullable values: `executor_id: null` before executor assignment and `reason_code: null` when no reason applies. Denial/failure events should carry a stable non-null reason code. Producers must emit the keys rather than omit them.

**Combined schema plan:** Resolve SEC-SCHEMA-003 (`registry_version`) and SEC-SCHEMA-004 (`executor_id` and `reason_code`) together in `security/AUDIT_EVENT_SCHEMA_PROPOSAL.md`. No wire-format change has been applied to the active v0.1.0 schema.

**Required tests:** Accept concrete and explicit-null values; reject omitted keys and invalid types; require a stable reason for denial/failure events at producer level. Run Draft 2020-12 validation and producer tests against the approved v0.2.0 schema.

**Status:** Identified in C0022; no schema change made pending producer-owner review. Privileged release remains blocked.


## Candidate schema implementation — C0023

A separately versioned candidate, `security/schemas/audit-event-0.2.0.schema.json`, now implements the combined SEC-SCHEMA-003/004 proposal without changing the active v0.1.0 schema.

The candidate requires `registry_version`, `executor_id`, and `reason_code`; the latter two retain explicit-null support for applicable event states. A conditional rule requires non-empty `reason_code` for `denied` and `failure` result statuses. The test suite adds candidate positive/negative envelope cases and cross-version rejection. CI has not yet been observed for this change.

**Status:** Schema candidate and test code committed; owner approval, trusted producer provenance, audit event lifecycle, migration and persistence/integrity tests remain open. This is not producer or runtime conformance evidence.
