# TuskerOS Deterministic Policy Engine Specification

**Owner:** AEGIS-06  
**Version:** 0.1.0-draft  
**Status:** Design specification; not an executable implementation

## 1. Authority and inputs

The policy engine is the sole authorization authority. Model output, caller-supplied risk labels, UI state, extension manifests, and remote request fields are untrusted. Authenticated principal and origin are injected by the trusted transport adapter from OS/session credentials and passed as a separate evaluation context; they are not accepted from the proposal body.

Every action, including reads, MUST pass through the registered-operation gateway and policy evaluation. Read-only actions may receive automatic ALLOW when their registered scope and caller capability match. An unregistered action, missing identity, unavailable policy service, malformed proposal, unsupported schema, or unavailable required audit sink yields DENY.

## 2. Operation registry

Each operation registration MUST conform to `security/schemas/operation-registration.schema.json` and declare:
- stable action_id and schema version;
- strict argument schema and canonicalization version;
- allowed principal classes and origins;
- resource kinds and permitted access modes;
- minimum risk class and risk escalation predicates;
- approval requirement and eligible approver class;
- execution timeout, resource limits and idempotency behavior;
- preconditions and postcondition verifier;
- broker implementation identifier (never a caller-selected executable).

Registry changes are security-sensitive, reviewed, versioned, and audited. No wildcard operation registration is permitted for privileged actions. The initial registry MUST be empty until each operation has an owner, argument schema, risk rationale, broker implementation, preconditions and tests; an empty registry means all action IDs are denied.

## 3. Deterministic risk classification

Risk is derived from the operation registry, validated arguments, resolved resources, principal capabilities, and current system state. The caller cannot lower risk. Classification takes the maximum of the registered minimum and all matching escalation rules.

| Class | Meaning | Default treatment |
|---|---|---|
| R0 | Public/local read with no sensitive data exposure | ALLOW only for explicitly registered scope |
| R1 | Low-impact, reversible user-level change | ALLOW only for registered action and bounded scope |
| R2 | Sensitive data access, external disclosure, or consequential user setting | REQUIRE_APPROVAL unless a narrowly reviewed policy says otherwise |
| R3 | Privileged OS, package, device, account, or network mutation | REQUIRE_APPROVAL plus broker-specific constraints |
| R4 | Destructive, bulk, irreversible, or recovery-impacting operation | REQUIRE_APPROVAL with explicit target/impact; default DENY if safe bounds cannot be proven |
| R5 | Security control, trust root, policy engine, audit integrity, or authorization bypass change | DENY by default; exceptional human-admin maintenance path must be out-of-band and separately reviewed |

Risk escalation predicates MUST be deterministic and testable. Unknown resource sensitivity or ambiguous impact escalates to the higher class; if the class cannot be resolved, DENY.

## 4. Evaluation algorithm

1. Authenticate transport peer; derive principal and origin from trusted context.
2. Validate proposal against the exact supported JSON Schema and operation-specific argument schema. Validators MUST enable JSON Schema format assertion for UUID and date-time fields; annotation-only format handling is insufficient.
3. Resolve action_id in the immutable registry snapshot; unknown action => DENY.
4. Resolve resource identifiers to canonical objects; reject traversal, aliases escaping scope, symlinks where prohibited, and unresolved targets.
5. Canonicalize the validated action, arguments, resolved resources, principal binding, operation schema version, and registry/policy version using RFC 8785 JSON Canonicalization Scheme (JCS); hash with SHA-256. Encode digest as sha256:<lowercase hex>.
6. Derive risk class from registry minimum plus deterministic escalation rules.
7. Check principal capability, origin, resource scope, preconditions, rate/resource limits, revocation state, and current policy.
8. Determine DENY / REQUIRE_APPROVAL / ALLOW. Any failed or indeterminate security check => DENY.
9. Persist pre-execution audit event before returning an ALLOW for R2+ and before any privileged or destructive operation. If required durable audit fails, DENY.
10. For approval, create an expiring request bound to digest, principal binding, session/device binding, policy/registry versions and preconditions. The approval presentation is descriptive only; only the server-side approval state transition can authorize. Approval UI returns only a decision; it does not mint authorization.
11. On user approval, re-authenticate principal/session, re-resolve resources, recheck preconditions and current policy, then atomically consume approval once and issue a short-lived authorization reference.
12. Executor and broker verify authorization immediately before execution, including exact digest, principal, operation, resource scope, expiry, policy version and one-time state. Any mismatch => reject and audit.

## 4.1 Interim policy-constraint handling (SEC-SCHEMA-007)

The v0.1.0 policy-decision schema now enforces the conservative interim shape: `constraints` is required and must be an empty object (`maxProperties: 0`, `additionalProperties: false`). The repository has not ratified a canonical non-empty vocabulary. Until policy-engine and broker owners agree a bounded, versioned vocabulary:

- A policy producer MUST emit `constraints: {}` only. The JSON Schema rejects missing, non-object, or non-empty values before a decision is accepted.
- A consumer MUST reject a decision with a non-empty `constraints` object rather than silently ignore or drop unknown keys.
- A consumer MUST NOT infer additional permission, broaden operation/resource scope, or relax broker-side limits from an unrecognized constraint.
- Missing, malformed, or unsupported constraint data MUST result in DENY and zero executor/broker handler calls.
- An empty object conveys no additional execution permission; the operation's registered schema and broker-enforced bounds remain authoritative.

This is a conservative interim contract, not a claim that any current policy consumer implements it. Do not close SEC-SCHEMA-007 or promote the schema until the vocabulary, schema validation, and consumer fail-closed behavior have owner-approved tests.

## 5. Canonicalization and digest

Use RFC 8785 JCS over a normalized envelope with explicit field names and no undefined values. Normalize resource ordering by (kind, canonical_id, access) before canonicalization. Reject duplicate resource tuples. Strings are Unicode-normalized to NFC before schema validation; reject invalid Unicode and ambiguous path encodings. Do not normalize case unless the resource provider defines case-insensitive identity. Include principal binding and policy/registry version in the authorization digest domain. Digest comparison is constant-time where secret-derived values are compared. Never hash raw JSON bytes or model-authored display strings as a substitute for canonical semantics.

## 6. Approval and anti-replay

Approval is one-time and bound to a single action digest, principal/session, operation, exact resources, policy version, preconditions and expiry. Store approval state server-side; do not treat a client-provided approval UUID as proof. Consume with an atomic compare-and-set transition from pending to consumed. Denial, expiry, revocation, changed digest, policy update, changed principal/session or failed precondition invalidates the request. Retries create a new evaluation; no replay.

## 7. Authorization evidence

The ALLOW response's authorization_ref is an opaque lookup/reference, not a self-authenticating bearer token. The broker resolves it through a trusted authorization service or verifies a cryptographically authenticated, audience-bound, short-lived token with one-time nonce tracking. The exact transport and signing format remain an integration decision with NEXUS-07. Never accept an unsigned boolean, caller-selected policy version, or decision object supplied by the planner.

## 8. Failure and availability behavior

Policy service unavailable, schema mismatch, clock uncertainty beyond configured tolerance, registry unavailable, identity unavailable, audit failure where required, approval store unavailable, or authorization-state uncertainty => DENY. No offline cache may authorize R2–R5. Any cache for R0/R1 must be bounded, version-pinned, revocable and explicitly reviewed. Failures must not trigger fallback shell execution or direct broker access.

## 9. Testable invariants

- For every DENY and REQUIRE_APPROVAL result, executor invocation count is exactly zero.
- A changed argument/resource/principal/policy version produces a different digest and invalidates approval.
- Expired, replayed, revoked or consumed authorization is rejected.
- Unknown actions, unknown schema fields, malformed inputs and unavailable dependencies fail closed.
- Remote and extension origins use the same policy and broker gates as local actions.
- Cancellation and compensation are separately authorized operations.
- Audit records contain correlation and decision references but no secret material.

## 10. Conformance fixtures

`security/POLICY_TEST_VECTORS.json` contains language-neutral positive and negative fixtures. These are expected outcomes, not executed test evidence. Implementations MUST map each vector to an automated test and assert zero executor calls for every DENY and REQUIRE_APPROVAL result. The schema validator MUST run with format assertion enabled.

## 11. Open integration decisions

- Confirm JCS + SHA-256 implementation/library and Unicode normalization behavior with runtime owners.
- Confirm how authenticated local IPC peer credentials and remote session/device claims reach the policy service.
- Confirm authorization reference lookup vs signed token and one-time nonce storage with NEXUS-07.
- Confirm whether the selected OS stack provides durable audit guarantees required for privileged execution.
- Confirm schema packaging/version negotiation and generated typed bindings with TUSKER-04.
- Confirm operation registry ownership, registration review and rollout procedure with NEXUS-07.
