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


## Finding SEC-SCHEMA-005 — registry-version requirement is underspecified for pre-evaluation and registry-failure audit events

**Severity:** Medium — audit completeness / fail-closed semantics ambiguity  
**Evidence:** `security/AUTHORIZATION_LIFECYCLE.md` requires request-created, presented, approval, denial, expiry, invalidation, consume and reconciliation events, and says to include policy/registry version. `security/OPERATION_REGISTRY.md` requires deny-all when the registry is missing, corrupt, unverifiable, stale or unavailable. The candidate audit-event 0.2.0 proposal currently makes `registry_version` a required non-empty string for every event.

**Gap:** The documents do not define how a producer records a request-created or denial event when no trustworthy registry snapshot/version can be loaded. Requiring a concrete version in that case risks either fabricating a value or suppressing the audit event; allowing null without an explicit semantic rule risks making a successful authorization indistinguishable from a pre-evaluation failure. The stable reason-code list also does not name a dedicated registry-unavailable code.

**Required owner decision before freezing 0.2.0:**
1. Confirm whether `registry_version` is required non-null only after a trusted snapshot is resolved, while pre-evaluation/registry-failure events carry an explicit null.
2. If null is allowed, define a separate typed registry-resolution state (or another unambiguous discriminator) and stable reason code for missing/corrupt/unverifiable/unavailable registry.
3. Require a concrete immutable `registry_version` on every ALLOW, CONSUMED, dispatch-start and terminal execution event; no grant or handler dispatch is possible without it.
4. Specify which component owns the registry resolution evidence and how its value is correlated across decision, consume and audit records.

**Status:** Identified in C0024. No schema or producer change made. This is an unresolved design decision, not an accepted change to the v0.2.0 proposal. NEXUS-07 must define runtime registry failure/evidence behavior; TUSKER-04 must confirm event timing and correlation.

**Required conformance cases (not yet executable):** request-created event before registry resolution; registry unavailable/corrupt denial with explicit non-fabricated state; successful ALLOW/CONSUMED event with concrete registry version; reject any successful/dispatch event with null or absent registry version; preserve correlated registry evidence across decision and execution.


## SEC-SCHEMA-005 — Candidate registry-resolution semantics (C0025)

The separate audit-event v0.2.0 candidate now requires `registry_status` and `registry_version` together. A trusted registry authority must supply the status; callers cannot assert it.

- `resolved` requires a concrete non-empty immutable `registry_version`.
- `unavailable` requires explicit null `registry_version` and is restricted to a request-received event (`requested`/`accepted`, null reason) or a fail-closed registry denial (`policy_denied`/`denied`, `POLICY_REGISTRY_UNAVAILABLE`).
- Authorization, consume, dispatch and execution events cannot validate with unavailable registry status.

Added Draft 2020-12 tests for both allowed unavailable-registry records and rejection of resolved/null, unavailable/versioned, unavailable/authorized and wrong-reason cases. The active v0.1.0 schema remains unchanged. This is an AEGIS-proposed schema rule; NEXUS-07/TUSKER-04 acceptance and producer integration remain open.


## SEC-SCHEMA-005 candidate test result — C0025

The v0.2.0 candidate was refined with required `registry_status` (`resolved`/`unavailable`) and explicit `registry_version` string/null semantics. Unavailable status permits only request receipt or a dedicated fail-closed registry denial; all authorization/consume/dispatch/execution events require a resolved concrete version.

- Initial CI runs 41128733954, 41128742563, 41128747002, 41128751266, 41128838747, 41128848970 and 41128855681 failed two tests: the edit had dropped the existing denial/failure reason-code conditional.
- Corrected schema retained three independent conditionals (resolved version, unavailable event restriction, and non-empty denial/failure reason).
- GitHub Actions run 41128922282 succeeded: **54 passed in 0.60s**, Python 3.12.

This validates the candidate schema and JSON fixtures only. Trusted registry provenance, producer behavior, durable audit storage and runtime fail-closed behavior remain untested and owner-dependent.


## Finding SEC-SCHEMA-006 — candidate audit schema omits required authorization lifecycle event types

**Severity:** Medium — audit completeness / lifecycle traceability gap  
**Evidence:** `security/AUTHORIZATION_LIFECYCLE.md` § Required audit events requires records for request-created, presented, approved/denied/dismissed, expired, invalidated, revoked, consume-accepted/rejected, and reconciliation outcomes. The candidate `security/schemas/audit-event-0.2.0.schema.json` currently enumerates `requested`, `authorized`, `started`, `succeeded`, `failed`, `cancellation_requested`, `cancelled`, `outcome_unknown`, compensation events, `approval_granted`, `approval_denied`, `approval_expired`, and `policy_denied`; it has no explicit event types for presentation, dismissal, invalidation, revocation, consume acceptance/rejection, or reconciliation.

**Risk:** Producers cannot emit several normative lifecycle events using the candidate schema without overloading unrelated event types or losing the distinction between approval state transitions, authorization consumption and reconciliation. This weakens audit reconstruction and incident review.

**Required owner decision:** NEXUS-07/TUSKER-04 must agree stable event names and result-status mappings for the missing lifecycle transitions, including whether reconciliation is one event with a typed outcome or distinct success/failure events. Preserve existing names where they already represent the same semantic transition (for example `approval_granted`, `approval_denied`, and `approval_expired`) rather than creating duplicates.

**Proposed additions for owner review (not applied):** explicit presentation, approval dismissal, approval invalidation, approval revocation, authorization-consume accepted/rejected, and reconciliation outcome event types. Define which trusted producer emits each event, required correlation/consumption IDs, and permitted result/reason values before updating the candidate schema.

**Required validation:** positive and negative schema fixtures for each lifecycle event; producer tests proving each transition emits exactly one correlated event; replay/concurrency and lost-consume-response tests proving consume and reconciliation records cannot be confused with dispatch or terminal execution results.

**Status:** Identified in C0026. No candidate or active schema change made pending producer-owner agreement. Active audit-event v0.1.0 remains unchanged; candidate v0.2.0 is not approved for producer migration or runtime conformance.


## C0030 — package transaction audit correlation

The C0030 review of FORGE-09's transaction helper found two integration constraints:

1. Its `canonical_digest` uses Python sorted-key JSON serialization and returns an unprefixed SHA-256 hex string. This is not the AEGIS normative RFC 8785 JCS action digest and must not be accepted as `action_digest` or authorization evidence.
2. The AEGIS candidate audit schema did not permit package `transaction_id` and installed-state `snapshot_digest` correlation fields requested in the C0027 package boundary decision.

The candidate audit-event v0.2.0 schema now allows `transaction_id` and `snapshot_digest` together or neither; the digest is `sha256:` + 64 lowercase hex. Tests cover the valid pair, each missing counterpart and malformed digest. `action_digest` remains the independently recomputed AEGIS canonical action binding.

The extension is candidate-only. Active v0.1.0 is unchanged; no producer, audit persistence, token verification, broker or package-manager execution is implemented or validated.

## C0044 — FORGE-09 transaction validator re-review

The current `09-ecosystem` branch was re-fetched after the C0036 finding and the mismatch remains:

- `marketplace/schemas/package-transaction-state.schema.json` requires a non-empty `reason_code` for legal `rejected` and `cancelled` history entries.
- `marketplace/tools/transaction_state.py` permits `reason_code` in `EVIDENCE_KEYS` and rejects blank values when supplied, but it does not require the key for either newly created transitions or persisted history entries.
- `marketplace/tests/test_transaction_state.py` still contains `transition_transaction(self.tx, "cancelled")` without reason evidence as an accepted setup path; no missing/blank reason negative cases are present in the fetched test module.

This means the Python helper can accept/produce a state record rejected by the published JSON Schema. AEGIS re-posted the source-level finding to FORGE-09 issue #29 (comment 6534092148), requesting enforcement in both new-transition and history-validation paths plus direct and persisted-history regression tests.

**Verification limit:** source inspection only. No FORGE code was modified and no FORGE tests were executed. The package execution security gate remains unchanged: approval authentication, exact snapshot revalidation, native locking, durable audit, broker consume and recovery guarantees are still required independently.


## C0049 — NEXUS-07 public invocation authorization-boundary re-review

Re-reviewed NEXUS-07 branch `07-system-integration` at `a0cc0a74242070135b6b7937bd7605c7861fe7d8`, including `system-integration/contracts/tool-invocation.schema.json`, `INTERFACE_CONTRACTS.md` and `system-integration/tests/test_contracts.py`.

**Positive change:** the current public invocation schema no longer declares `authorization_context`; top-level `additionalProperties: false` and the closed `caller` object reject undeclared caller-supplied authority claims. This closes the earlier schema-level arbitrary-object allowance for the public v1 envelope.

**Remaining gaps:** the public invocation example in `INTERFACE_CONTRACTS.md` still contains `authorization_context: {}`, conflicting with the machine schema. Neither contract defines a separate typed broker-internal envelope or the trusted injection/consume API. The fetched test module has no explicit negative regression cases for caller-supplied `authorization_context`, `principal`, `decision` or `authorization_ref`, nor a positive test proving authenticated broker context alone reaches AEGIS consume. No implementation/test evidence demonstrates kernel-authenticated IPC identity bound to principal/session or consume-before-mutating-dispatch.

AEGIS posted the focused re-review on NEXUS-07 issue #17 (comment 6534567960), requesting removal of the stale public example field, explicit smuggling-negative tests, a positive trusted-context adapter test, and a typed peer-authentication/atomic-consume integration contract. No NEXUS-owned files were changed and no NEXUS tests were executed. Public-schema rejection is a useful contract improvement, not proof of runtime identity or authorization enforcement; mutating operations remain fail-closed/disabled until those runtime gates are implemented and tested.


## C0053 — Remote audit data-minimization regression coverage

The candidate audit-event v0.2.0 schema already uses `additionalProperties: false` and requires hashed `device_binding`/`session_binding` for `origin=remote`. C0052 had added direct negative cases for raw `device_id` and `session_id`. This follow-up broadens the regression guard to explicitly reject eleven classes of sensitive fields in the general audit envelope: raw device/session identifiers, device public key, session token, authorization material, signature, pairing secret, private key, task payload, prompt and completion.

Updated `security/tests/test_security_schemas.py` with parametrized `test_audit_event_v020_rejects_raw_remote_identity_credentials_and_payloads` (11 cases), and updated AUD-REMOTE-006 in `security/SECURITY_TEST_MATRIX.md`. The test commit `98aff2c0b4393e40e3661946d8fd16b59a1a8b1d` triggered GitHub Actions run [41165765657](https://github.com/otta-komban/TuskerOS/actions/runs/41165765657), which completed successfully; its validation job and all steps report success.

**Scope limit:** this demonstrates schema rejection of these fields, not that a live remote adapter redacts them, that audit producers persist only approved data, or that the audit store enforces access control/integrity. Candidate v0.2.0 remains unapproved for producer migration pending NEXUS-07/TUSKER-04 agreement; remote approval remains disabled for MVP.


## SEC-SCHEMA-007 — Policy-decision constraints object is underspecified

Reviewed `security/schemas/policy-decision.schema.json` against `security/SECURITY_CONTRACTS.md` section 4. The original finding was that `constraints` accepted arbitrary nested objects. The current v0.1.0 schema now requires an empty object with `maxProperties: 0` and `additionalProperties: false`; regression tests accept `{}` and reject non-empty objects. This is a conservative interim restriction, not the final bounded constraint vocabulary.

**Risk / ambiguity:** a producer can serialize an unknown constraint that a consumer silently ignores, or different consumers can interpret the same untyped object differently. The current sources do not define a canonical constraint vocabulary, so AEGIS must not invent one in a compatibility-sensitive schema change.

**Required resolution:** define the bounded constraint vocabulary and semantics with policy-engine and broker owners; then type each property, bound values, set `additionalProperties: false`, and add positive/negative schema and consumer tests. Until then, consumers must not treat an unrecognized constraint as permission to broaden execution. Tracked in [issue #31](https://github.com/otta-komban/TuskerOS/issues/31). No schema change was made and no runtime consumer behavior was tested.


## SEC-SCHEMA-007 — interim constraints schema enforcement

The policy-decision contract now states that producers emit an empty `constraints` object only and consumers reject non-empty or unsupported constraints until policy-engine and broker owners approve a bounded vocabulary. The v0.1.0 schema now requires `constraints` and caps it at zero properties, matching that interim fail-closed rule. Regression tests accept the empty object and reject omission plus representative non-empty/nested values. This closes the schema-level permissiveness without inventing a future constraint vocabulary. It does not establish runtime producer or consumer enforcement; owner agreement on the eventual typed vocabulary remains tracked in issue #31.
