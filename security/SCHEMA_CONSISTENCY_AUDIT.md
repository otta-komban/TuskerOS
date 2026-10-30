# Security contract/schema consistency audit

**Owner:** AEGIS-06  
**Status:** Draft findings; no runtime or standards-validation claim  
**Scope:** Compare draft normative prose with approval-request and audit-event JSON Schemas on `06-security-gatekeeper`.

## Result

Two actionable schema/prose coverage gaps were found. The existing schemas remain draft artifacts; this review does not claim full JSON Schema 2020-12 validation or implementation conformance.

## Finding SEC-SCHEMA-001 — approval binding is not represented in the approval-request envelope

**Severity:** High — contract completeness blocker  
**Evidence:** `security/SECURITY_CONTRACTS.md` section 5 and `security/AUTHORIZATION_LIFECYCLE.md` state that approval is bound to the authenticated session/device, exact resource scope, registry version and relevant preconditions. The current `security/schemas/approval-request.schema.json` requires only proposal/action digest, principal binding, policy version, risk, presentation fields and timestamps. It has no fields for session/device binding, registry version, canonical resources or precondition snapshot.

**Risk:** An implementation could validate the current envelope while omitting context that the prose says approval must bind. That creates ambiguity about what the approver is actually approving and what must be rechecked at consumption.

**Recommended resolution:** Add explicit, typed fields (or define a separate trusted server-side binding record with a stable reference) for session/device binding, registry version, canonical resource scope and precondition snapshot/digest. Specify which values are displayed, which are internal-only, and how every value is compared again before consume. Require strict schema validation and negative tests for changed/missing bindings. Do not accept a client-provided field as proof of identity.

## Finding SEC-SCHEMA-002 — audit schema does not require all documented minimum correlation fields

**Severity:** Medium — audit completeness blocker  
**Evidence:** `security/SECURITY_CONTRACTS.md` section 7 lists `task_id` and `step_id` among minimum audit fields. The current `security/schemas/audit-event.schema.json` defines both properties as nullable but omits them from its top-level `required` array.

**Risk:** A schema-valid event can omit task/step correlation entirely, weakening reconstruction of multi-step actions and incident timelines relative to the written contract.

**Recommended resolution:** Either add `task_id` and `step_id` to `required` while retaining explicit nullability for events where correlation genuinely does not exist, or amend the normative contract to state precisely which event classes may omit them. Add schema and event-producer tests for both correlated and intentionally uncorrelated events.

## Checks performed

- Retrieved and compared the current security contract, lifecycle document, approval-request schema and audit-event schema from the assigned branch.
- Confirmed both missing-field cases directly against the prose and schema declarations.
- Kept findings scoped to draft contract completeness; no claim of complete meta-schema validation, format assertion, fixture validation, runtime behavior or executable tests.
- No schema changed in this audit: proposed wire-format changes require explicit review because they may affect other agents' consumers.

## Required follow-up

1. AEGIS-06 to propose exact schema fields and versioning for SEC-SCHEMA-001.
2. NEXUS-07 and TUSKER-04 to review the approval binding representation at their runtime/producer boundaries.
3. AEGIS-06 to reconcile audit-event required fields for SEC-SCHEMA-002.
4. Add positive and negative schema fixtures, then run Draft 2020-12 validation with format assertion enabled in CI.

**Release implication:** Keep privileged execution blocked until approval binding is fully represented and enforced, and the audit event contract is made consistent with its schema.
