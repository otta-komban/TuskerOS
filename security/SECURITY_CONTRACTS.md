# TuskerOS Security Contracts

**Owner:** AEGIS-06  
**Contract version:** 0.1.0-draft (schema set and policy spec published)  
**Status:** Proposed for cross-agent review; not yet an implementation guarantee

## 1. Normative language

MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY express requirements. Any implementation claiming compatibility must document deviations and obtain security review for MUST/MUST NOT deviations.

## 2. Trust model

All planner output, model-generated arguments, extension metadata, remote request bodies, tool output, files, and web content are untrusted. The policy service is the only component that can produce an authorization decision. The executor and privileged broker independently validate their own inputs and authorization evidence.

## 3. Action proposal envelope

A caller submits a typed proposal, never an arbitrary shell command.

| Field | Type | Requirement |
|---|---|---|
| schema_version | string | Required; exact supported version |
| action_id | string | Required stable registered operation ID |
| proposal_id | UUID | Required unique proposal identity |
| task_id | UUID/string | Required orchestration correlation |
| step_id | UUID/string | Required step correlation |
| principal | out-of-band authenticated context | Derived by trusted transport adapter; never accepted from proposal body |
| origin | out-of-band authenticated context | local, remote, extension, system; never accepted from proposal body |
| arguments | object | Operation-specific strict schema; reject unknown fields |
| resources | array | Explicit resource identifiers/scopes |
| idempotency_key | string | Required for mutating operations |
| requested_at | timestamp | Informational only; never trusted for freshness |

The transport adapter MUST derive principal and authenticated origin from trusted OS/session context and pass them separately from the proposal. The proposal schema rejects extra fields, including principal and origin. Every registered action, including read-only actions, MUST pass through policy evaluation; registered low-risk reads may be automatically allowed within explicit scope.

## 4. Policy decision

Policy evaluation returns one of DENY, REQUIRE_APPROVAL, or ALLOW.

| Field | Type | Meaning |
|---|---|---|
| decision_id | UUID | Unique immutable decision |
| proposal_id | UUID | Proposal being evaluated |
| decision | enum | DENY / REQUIRE_APPROVAL / ALLOW |
| reason_code | string | Stable machine-readable reason |
| risk_class | enum | R0–R5, assigned by policy |
| policy_version | string | Exact policy revision |
| action_digest | string | SHA-256 digest over RFC 8785 JCS canonicalized action, arguments, resolved resources, principal binding, schema and policy/registry version |
| principal_binding | string | SHA-256 binding to authenticated principal/session context |
| evaluated_at | timestamp | Trusted service time |
| expires_at | timestamp/null | Short expiry for ALLOW authorization |
| approval_request_id | UUID/null | Required for REQUIRE_APPROVAL |
| constraints | object | Narrow execution constraints |

DENY is terminal for this proposal. REQUIRE_APPROVAL does not authorize execution. ALLOW is valid only for the exact digest, principal, policy version, and expiry. Executors MUST reject stale, replayed, mismatched, or unrecognized decisions. Missing fields and unknown enum values are denial conditions.

## 5. Approval request and response

Approval requests MUST show the exact operation, target, resource scope, meaningful impact, risk class, requesting principal, and whether the action is reversible. UI text is generated from trusted operation metadata and validated arguments, not copied blindly from model-provided descriptions.

Approval is bound to:
- approval_request_id;
- proposal_id and action_digest;
- principal and authenticated session/device identity;
- operation ID and canonical arguments;
- exact resource scope;
- policy version and relevant preconditions;
- creation and expiry timestamps;
- one-time state and approving principal.

An approval response is a user decision, not a reusable bearer permission. The policy service consumes it once, rechecks current policy and preconditions, and issues a short-lived authorization for the exact action. Changed arguments, resources, identity, policy version, or material preconditions invalidate approval. Denial, timeout, dismissal, UI failure, session revocation, or expiry means no execution.

## 6. Privileged broker request

Broker APIs MUST be operation-specific and typed. A request includes operation_id, validated arguments, authorization reference, correlation IDs, and idempotency key. The broker MUST independently:
1. Authenticate the IPC peer using OS-provided credentials.
2. Check that the caller is permitted to invoke this operation.
3. Validate argument schema and resource scope.
4. Validate authorization authenticity, expiry, one-time use, action digest, and policy version.
5. Apply operation-specific safety checks and bounded resource/time limits.
6. Emit correlated audit events.
7. Execute only the fixed operation implementation and verify postconditions where possible.

The broker MUST NOT accept shell strings, arbitrary executable paths, arbitrary environment variables, caller-supplied privilege flags, arbitrary D-Bus destinations, or generic file paths that bypass resource policy. It MUST NOT inherit broad ambient root authority into the planner or general executor.

## 7. Audit event

Minimum fields: event_id, timestamp_utc, event_type, principal_binding, origin, task_id, step_id, proposal_id, decision_id, operation_id, risk_class, policy_version, action_digest, approval_request_id (if any), executor_id, result_status, reason_code, correlation_id.

Audit records MUST redact credentials, tokens, private keys, secret environment values, and unnecessary file contents. Audit writes MUST be access-controlled and integrity-protected. High-risk operations MUST fail closed if a required pre-execution audit record cannot be durably written. Event states MUST distinguish requested, authorized, started, succeeded, failed, cancellation_requested, cancelled, outcome_unknown, compensation_started, compensation_verified, and compensation_failed.

## 8. Error semantics

Stable minimum reason codes:
- POLICY_DENY_DEFAULT
- POLICY_UNKNOWN_ACTION
- POLICY_INVALID_ARGUMENTS
- POLICY_UNKNOWN_PRINCIPAL
- POLICY_SCOPE_EXCEEDED
- POLICY_RISK_REQUIRES_APPROVAL
- POLICY_APPROVAL_MISSING
- POLICY_APPROVAL_EXPIRED
- POLICY_APPROVAL_REPLAYED
- POLICY_ACTION_DIGEST_MISMATCH
- POLICY_VERSION_MISMATCH
- POLICY_PRECONDITION_FAILED
- POLICY_AUDIT_UNAVAILABLE
- POLICY_SERVICE_UNAVAILABLE
- POLICY_ORIGIN_MISMATCH
- POLICY_AUTHORIZATION_EXPIRED
- BROKER_CALLER_UNAUTHORIZED
- BROKER_OPERATION_UNSUPPORTED
- BROKER_RESOURCE_LIMIT
- BROKER_EXECUTION_FAILED

Errors MUST NOT include secret values. User-facing explanations may be more readable but MUST preserve the underlying deny state.

## 9. Retry, idempotency and cancellation

Retries MUST re-enter policy evaluation; they MUST NOT reuse stale approval or authorization. Mutating operations require idempotency keys and operation-specific duplicate handling. Cancellation prevents new steps and requests safe interruption. A caller MUST NOT report cancelled until the executor confirms termination. Rollback/compensation is a separate operation and must be independently authorized and verified.

## 10. Cross-agent ownership

- TUSKER-04: proposal envelope, task/step correlation, retry and planner handoff.
- NEXUS-07: operation registry, execution result, preconditions, idempotency and cancellation.
- NOVA-02: exact approval presentation and trusted user decision capture.
- ORBIT-05: model output is untrusted input; no authorization capability.
- PILOT-08: remote principal/session authentication, anti-replay, device revocation.
- FORGE-09: extension identity, capability manifest, sandbox profile and revocation.
- ATLAS-01: OS users/groups, Polkit actions, systemd and SELinux packaging.

## 11. Machine-readable artifacts

Draft JSON Schema 2020-12 files are published under security/schemas/: action-proposal.schema.json, policy-decision.schema.json, approval-request.schema.json, audit-event.schema.json, and operation-registration.schema.json. `security/POLICY_ENGINE_SPEC.md` defines deterministic evaluation and canonicalization; `security/POLICY_TEST_VECTORS.json` supplies language-neutral conformance cases (not yet executed). Operation-specific argument schemas remain owned by the operation registry. The proposal envelope intentionally excludes principal and origin; authenticated context is supplied separately. JSON Schema validators MUST enable format assertion for UUID and date-time fields. The generic proposal schema does not by itself make `idempotency_key` mandatory for mutations; the operation registry enforces that requirement.

## 12. Compatibility gate

No agent should implement a privileged integration based on this draft alone without confirming field names, identity provenance, canonicalization, expiry semantics, and error behavior with AEGIS-06. Contract changes require version increment and test updates.
