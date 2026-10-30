# Security contract/schema consistency audit

**Owner:** AEGIS-06  
**Status:** Draft findings; no runtime or standards-validation claim  
**Scope:** Compare draft normative prose with approval-request and audit-event JSON Schemas on `06-security-gatekeeper`.

## Result

Two actionable schema/prose coverage gaps were found. SEC-SCHEMA-002 has now been reconciled in the draft schema; SEC-SCHEMA-001 remains open. The artifacts remain drafts; this review does not claim full JSON Schema 2020-12 validation or implementation conformance.

## Finding SEC-SCHEMA-001 — approval binding is not represented in the approval-request envelope

**Severity:** High — contract completeness blocker  
**Evidence:** `security/SECURITY_CONTRACTS.md` section 5 and `security/AUTHORIZATION_LIFECYCLE.md` state that approval is bound to the authenticated session/device, exact resource scope, registry version and relevant preconditions. The current `security/schemas/approval-request.schema.json` requires only proposal/action digest, principal binding, policy version, risk, presentation fields and timestamps. It has no fields for session/device binding, registry version, canonical resources or precondition snapshot.

**Risk:** An implementation could validate the current envelope while omitting context that the prose says approval must bind. That creates ambiguity about what the approver is actually approving and what must be rechecked at consumption.

**Recommended resolution:** Add explicit, typed fields (or define a separate trusted server-side binding record with a stable reference) for session/device binding, registry version, canonical resource scope and precondition snapshot/digest. Specify which values are displayed, which are internal-only, and how every value is compared again before consume. Require strict schema validation and negative tests for changed/missing bindings. Do not accept a client-provided field as proof of identity.

## Finding SEC-SCHEMA-002 — audit schema does not require all documented minimum correlation fields

**Severity:** Medium — audit completeness blocker  
**Evidence:** `security/SECURITY_CONTRACTS.md` section 7 lists `task_id` and `step_id` among minimum audit fields. The current `security/schemas/audit-event.schema.json` defines both properties as nullable but omits them from its top-level `required` array.

**Risk:** A schema-valid event can omit task/step correlation entirely, weakening reconstruction of multi-step actions and incident timelines relative to the written contract.

**Resolution in C0012:** Added `task_id` and `step_id` to the audit-event schema's top-level `required` array while preserving each property's `string`/`null` type. Every event must now carry both keys; an explicitly uncorrelated event uses `null`. This follows the existing minimum-field contract without inventing an event-class omission exception. Producer tests for correlated and null values remain required.

## Checks performed

- Retrieved and compared the current security contract, lifecycle document, approval-request schema and audit-event schema from the assigned branch.
- Confirmed both missing-field cases directly against the prose and schema declarations.
- Kept findings scoped to draft contract completeness; no claim of complete meta-schema validation, format assertion, fixture validation, runtime behavior or executable tests.
- C0011 made no schema changes. C0012 makes one narrowly scoped draft-schema correction: both nullable correlation properties are now required to be present.
- Parsed the updated schema as JSON and checked that both keys occur in `required` and retain nullable types. This is a structural check only, not Draft 2020-12 meta-schema validation, format assertion or producer validation.

## Required follow-up

1. AEGIS-06 to propose exact schema fields and versioning for SEC-SCHEMA-001.
2. NEXUS-07 and TUSKER-04 to review the approval binding representation at their runtime/producer boundaries.
3. Add positive and negative audit-event schema/producer fixtures for present UUIDs and explicit `null` correlation, then run Draft 2020-12 validation with format assertion enabled in CI.

**Release implication:** Keep privileged execution blocked until approval binding is fully represented and enforced, and the audit event contract is made consistent with its schema.


## C0012 update — SEC-SCHEMA-002 reconciled

- `task_id` and `step_id` are now members of the audit-event schema's top-level `required` array.
- Both properties remain nullable; producers must represent unavailable correlation explicitly as `null` rather than omit the keys.
- The schema `$id` and `schema_version` remain `0.1.0` because this is a draft contract correction, not a declared new published version. Runtime-owner compatibility review is still required before treating the draft as frozen.
- SEC-SCHEMA-001 remains unresolved and continues to block privileged release.


## C0013 update — automated schema validation added

- Added `security/tests/test_security_schemas.py` using Draft 2020-12 validation with format assertion enabled.
- The suite checks that every current security schema is a valid Draft 2020-12 schema and exercises audit-event examples with correlated IDs and explicit null correlation.
- Negative cases cover omitted `task_id`/`step_id`, invalid types, malformed UUID/date-time/digest values, invalid enums and unexpected properties.
- Added isolated test dependencies in `security/requirements-test.txt` and GitHub Actions workflow `.github/workflows/security-contracts.yml`.
- Workflow run [41126223487](https://github.com/otta-komban/TuskerOS/actions/runs/41126223487) completed successfully: 17 tests passed in 0.21s on Python 3.12.15. The job installed the isolated dependencies, checked all five security schemas with Draft 2020-12 meta-schema validation, and passed the audit-event positive/negative cases.
- This validates schemas and sample event envelopes only; it does not test a real audit producer, persistence integrity, or privileged runtime behavior.


## C0013 update — SEC-SCHEMA-001 draft remediation

The approval-request schema has been advanced to draft version `0.2.0` and now requires a `binding` object containing:

- `session_binding` and `device_binding`: SHA-256 bindings, not raw session/device identifiers or proof of identity;
- `registry_version`: the exact operation-registry revision;
- `resource_scope`: a non-empty set of unique canonical resource identifiers;
- `precondition_digest`: SHA-256 digest of the relevant precondition snapshot.

The top-level `action_digest` remains required and is still the integrity binding for the complete canonical action. The explicit fields make the critical approval context inspectable and independently re-checkable; they do not replace RFC 8785 canonicalization, trusted identity derivation, broker-side comparison, or atomic one-time consumption.

**Compatibility:** This is a draft wire-format version change from `0.1.0` to `0.2.0`, not a claim that any runtime producer/consumer has migrated. Existing 0.1.0 messages must not be silently treated as 0.2.0. Runtime owners must confirm the binding source, canonical resource representation, and migration strategy before contract freeze.

**Validation limits:** JSON structure and schema text were reviewed; no Draft 2020-12 meta-schema/format validator, producer fixture, UI presentation test, or runtime enforcement test is claimed. Schema constraints cannot prove that the hashes correspond to trusted values or that resource identifiers are canonical/sorted; those are semantic enforcement requirements.

## C0013 proposal — explicit approval binding envelope (candidate v0.2.0)

SEC-SCHEMA-001 remains **open**. To make the missing contract shape reviewable without silently changing the active v0.1.0 wire format, this proposal defines a candidate nested `approval_binding` object for a separately versioned v0.2.0 schema. The current `security/schemas/approval-request.schema.json` remains unchanged.

Candidate required members:

| Member | Proposed type | Source and enforcement |
|---|---|---|
| `session_binding` | `sha256:<64 lowercase hex>` | Trusted transport/authorization service derives this from the authenticated session; never accepted as caller identity. |
| `device_binding` | `sha256:<64 lowercase hex>` | Trusted OS/session integration derives this from authenticated device context; never accepted as caller identity. |
| `registry_version` | non-empty string, max 128 | Exact immutable operation-registry version used for evaluation. |
| `canonical_resources` | unique array of non-empty strings, each max 512 | Resolved canonical resource identifiers. Empty array explicitly means the operation has no resource scope. Canonicalization remains registry/operation-owner defined. |
| `precondition_digest` | `sha256:<64 lowercase hex>` | Digest of the relevant precondition snapshot. Sensitive snapshot contents may remain in trusted server-side state. |

### Required trust and consume behavior

1. The approval-request producer MUST obtain session/device bindings from authenticated transport/OS context. Caller JSON fields are not proof of identity.
2. The trusted resolver MUST populate registry version and canonical resources after resolving the registered operation and its target scope.
3. The authorization authority MUST bind the complete tuple above to the immutable approval record and compare it again at consume time. Any mismatch invalidates the approval and yields no grant.
4. The precondition digest MUST be recomputed from the current relevant snapshot before consume; a mismatch invalidates approval.
5. The approval presentation MUST show the operation, target and meaningful resource scope using trusted operation metadata and validated arguments. Raw internal digests need not be displayed.
6. If authenticated session/device context or a reliable precondition snapshot is unavailable, approval creation/consumption fails closed; a caller-supplied substitute is forbidden.

### Versioning and compatibility

- Candidate version: `0.2.0`; do not mutate the active v0.1.0 schema in place.
- The candidate is a design proposal only. It is not an active producer contract and does not authorize runtime implementation.
- Before adoption, NEXUS-07 must confirm how the broker receives and checks the binding tuple at atomic consume; TUSKER-04 must confirm proposal/approval producer compatibility; PILOT-08 and ATLAS-01 must confirm remote/local session and device provenance.
- On acceptance, publish a separate v0.2.0 schema and positive/negative fixtures, then update the contract's machine-readable artifact index. Keep v0.1.0 compatibility explicit rather than silently reinterpreting its envelope.

### Minimum conformance cases for the candidate

- Valid trusted binding tuple is accepted.
- Each missing member and each malformed digest is rejected.
- Duplicate canonical resource identifiers are rejected.
- Caller-supplied or mismatched session/device binding is rejected at the trusted boundary.
- Changed registry version, resource set or precondition digest invalidates approval.
- Every mismatch/unavailable-context case issues no authorization grant and produces zero broker handler calls.

This proposal narrows the field-shape question but does not resolve ownership or transport. **SEC-SCHEMA-001 remains a privileged-release blocker until runtime owners accept and implement the binding checks.**



## Finding SEC-SCHEMA-003 — audit event omits registry version required by lifecycle

**Severity:** Medium — audit evidence completeness gap  
**Evidence:** `security/AUTHORIZATION_LIFECYCLE.md` requires audit records to include policy/registry version. The current `security/schemas/audit-event.schema.json` requires `policy_version` but has no `registry_version` property. A schema-valid event therefore cannot explicitly record which operation-registry revision governed the authorization.

**Risk:** Incident reconstruction and registry-change analysis cannot reliably distinguish events evaluated under different registry revisions from the audit envelope alone.

**Recommended resolution:** Add a required, non-empty `registry_version` string (bounded to 128 characters to align with approval-request 0.2.0) to a separately versioned audit-event schema after producer-owner review. The value must come from the trusted immutable registry snapshot used for evaluation. Do not silently change the existing 0.1.0 draft.

**Status:** Identified in C0013; no audit schema change made. Confirm whether a version string or immutable registry-snapshot reference is the stable producer contract before freezing the next schema version.

## C0013 update — approval binding draft review

- Reviewed the branch's approval-request 0.2.0 draft and aligned `security/APPROVAL_BINDING_SCHEMA_PROPOSAL.md` to its actual nested `binding` shape: separate session/device digests, registry version, canonical resource identifiers and precondition digest.
- Documented trust-source, canonicalization, digest coverage, fail-closed and 0.1.0-to-0.2.0 migration requirements. Runtime-owner acceptance and producer/UI/broker tests remain pending.
- Identified SEC-SCHEMA-003: lifecycle requires registry version in audit evidence, but audit-event schema has no such property. No audit wire-format change made.
