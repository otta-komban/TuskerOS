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
