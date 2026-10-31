# AEGIS-06 Security Policy Test Matrix

**Status:** Test specification only. No test has been executed by this document.  
**Contract:** security/SECURITY_CONTRACTS.md v0.1.0-draft    
**Machine-readable fixtures:** `security/POLICY_TEST_VECTORS.json`    
**Operation registry schema:** `security/schemas/operation-registration.schema.json`

## Test conventions

- Each test uses an isolated fixture and a fake executor/broker; no host mutation.
- Assert both policy decision and executor invocation count.
- For every denial case, assert executor/broker invocation count is exactly zero.
- Capture correlated audit events and assert secrets are absent.
- Validate all schemas with a Draft 2020-12 validator configured for format assertion.  
- Map every `POLICY_TEST_VECTORS.json` case to an executable test.  
- Mark tests PASS only after an executable test runs and evidence is recorded.

## Policy decision tests

| ID | Scenario | Expected result | Executor calls |
|---|---|---|---:|
| POL-001 | Registered R0 read within granted scope | ALLOW | 1 |
| POL-002 | Registered R1 low-risk action in allowlist | ALLOW | 1 |
| POL-003 | R2 sensitive read without approval | REQUIRE_APPROVAL; no execution | 0 |
| POL-004 | R3 privileged package operation without approval | REQUIRE_APPROVAL; no execution | 0 |
| POL-005 | R4 destructive operation without strong confirmation | DENY or REQUIRE_APPROVAL per registered workflow; no execution | 0 |
| POL-006 | R5 security-critical operation requested by AI | DENY | 0 |
| POL-007 | Unknown action ID | DENY | 0 |
| POL-008 | Missing or malformed required argument | DENY | 0 |
| POL-009 | Unknown extra argument field | DENY | 0 |
| POL-010 | Caller attempts to set risk_class=R0 for registered R3 action | Policy assigns R3; approval required | 0 |
| POL-011 | Unknown principal | DENY | 0 |
| POL-012 | Resource outside granted scope | DENY | 0 |
| POL-013 | Policy service unavailable or evaluation exception | DENY / fail closed | 0 |
| POL-014 | Expired ALLOW decision | DENY at executor | 0 |
| POL-015 | Policy version changed after decision | DENY | 0 |

## Approval integrity tests

| ID | Scenario | Expected result | Executor calls |
|---|---|---|---:|
| APR-001 | Exact action approved once, still valid | ALLOW once | 1 |
| APR-002 | Reuse same approval | DENY replay | 0 |
| APR-003 | Change one argument after approval | DENY digest mismatch | 0 |
| APR-004 | Change target resource after approval | DENY digest mismatch | 0 |
| APR-005 | Approval belongs to another principal | DENY | 0 |
| APR-006 | Approval belongs to another remote device/session | DENY | 0 |
| APR-007 | Approval expired | DENY | 0 |
| APR-008 | User denied or dismissed prompt | DENY | 0 |
| APR-009 | UI sends approval for a different displayed action | DENY | 0 |
| APR-010 | Preconditions materially changed after approval | Re-evaluate; require new approval or deny | 0 |
| APR-011 | Session/device revoked before execution | DENY | 0 |

## Broker and OS boundary tests

| ID | Scenario | Expected result |
|---|---|---|
| BRK-001 | Authorized caller invokes registered narrow operation | Execute bounded operation |
| BRK-002 | Unprivileged unrelated process connects | Reject caller |
| BRK-003 | Request contains shell command string | Reject schema |
| BRK-004 | Request contains arbitrary executable path | Reject schema |
| BRK-005 | Request attempts path traversal | Reject target |
| BRK-006 | Symlink target changes between validation and use | Safe descriptor-relative operation or reject |
| BRK-007 | Request exceeds input/time/resource quota | Reject/terminate safely |
| BRK-008 | Caller supplies privilege escalation flag | Ignore/reject; never elevate |
| BRK-009 | Broker receives malformed or expired authorization | Reject |
| BRK-010 | Required pre-execution audit persistence fails | Do not execute high-risk action |

## Remote and extension tests

| ID | Scenario | Expected result |
|---|---|---|
| REM-001 | Authenticated remote low-risk request | Same policy path as local request |
| REM-002 | Remote client claims local origin | Reject claim; use authenticated transport identity |
| REM-003 | Replayed remote request | Reject replay/idempotency duplicate |
| REM-004 | Remote privileged request without local approval | No execution |
| REM-005 | Revoked device submits request | Reject |
| EXT-001 | Extension requests undeclared capability | Deny |
| EXT-002 | Extension accesses host path outside grant | Sandbox denies |
| EXT-003 | Extension requests host network without grant | Sandbox denies |
| EXT-004 | Extension package signature/provenance invalid | Quarantine/reject |
| EXT-005 | Extension permission revoked while idle | Subsequent capability call denied |

## Cancellation, recovery and audit tests

| ID | Scenario | Expected result |
|---|---|---|
| REC-001 | Cancel before execution starts | No executor call; terminal cancelled |
| REC-002 | Cancel during interruptible operation | Stop confirmed; cancelled |
| REC-003 | Cancel during uninterruptible operation | Report cancellation_requested/outcome_unknown, not cancelled |
| REC-004 | Compensation succeeds and postcondition verified | compensation_verified |
| REC-005 | Compensation fails | compensation_failed; preserve evidence |
| AUD-001 | Successful sensitive operation | Correlated decision, approval, start and result events |
| AUD-002 | Denied operation | Denial event; no execution event |
| AUD-003 | Secret included in arguments | Redacted from all audit output |
| AUD-004 | Audit store unavailable for high-risk preflight | Fail closed |
| AUD-005 | Attempt to alter prior audit event | Integrity check detects alteration |

## Evidence template

For each executed test, record: test ID, test code path, command, environment, timestamp, result, assertions, artifact/CI URL, commit SHA, and reviewer. Never mark an unexecuted case as passing.


## Authorization lifecycle and atomic-consumption tests

| ID | Scenario | Expected result | Handler calls |
|---|---|---|---:|
| AUTH-001 | Eligible approver approves exact pending request | APPROVED; no grant until consume | 0 |
| AUTH-002 | Approver denies | DENIED terminal | 0 |
| AUTH-003 | Pending request expires | EXPIRED terminal | 0 |
| AUTH-004 | Exact valid authorization consumed | CONSUMED; one scoped grant | 1 |
| AUTH-005 | Replay consumed reference | Reject replay | 0 |
| AUTH-006 | Wrong principal or session/device | Reject binding | 0 |
| AUTH-007 | Wrong operation or resource/digest | Reject and invalidate changed request | 0 |
| AUTH-008 | Policy/registry version changed | Invalidate and re-evaluate | 0 |
| AUTH-009 | Revoked or expired authorization | Reject | 0 |
| AUTH-010 | Two concurrent consume attempts | Exactly one wins and dispatches | 1 total |
| AUTH-011 | Authorization store, clock or identity unavailable | Fail closed | 0 |
| AUTH-012 | Consume committed but response lost | Reconcile same consumption; no duplicate | At most 1 |
| BRK-011 | Untrusted IPC peer or unknown operation ID | Reject before handler | 0 |
| BRK-012 | Broker-side schema/bounds validation fails | Reject before handler | 0 |
| BRK-013 | Precondition changes before dispatch | Invalidate/reject | 0 |
| BRK-014 | Disconnect after dispatch before result | Return UNKNOWN; reconcile before retry | No blind retry |

The machine-readable expected outcomes are in `security/AUTHORIZATION_TEST_VECTORS.json`. These remain specifications; no executable tests have been run.


## Approval-to-authorization handoff and typed consume outcomes

| ID | Scenario | Expected result | Handler calls |
|---|---|---|---:|
| AUTH-015 | Approve pending request; current bindings still match | Fresh ALLOW + new opaque authorization_ref; approval_request_id remains correlation only | 0 until broker consume |
| AUTH-016 | Approve pending request; policy/resource/session/registry/precondition changed | INVALIDATED; no ALLOW or grant | 0 |
| AUTH-017 | Broker submits approval_request_id instead of authorization_ref | BINDING_MISMATCH | 0 |
| AUTH-018 | Consume commits state and required pre-dispatch audit atomically | CONSUMED + unique consumption_id + narrow grant | At most 1 |
| AUTH-019 | Required audit commit fails before consume grant | AUDIT_UNAVAILABLE; transaction does not consume | 0 |
| AUTH-020 | Consume response lost / outcome cannot be confirmed | CONSUME_OUTCOME_UNKNOWN; reconcile, no blind dispatch/retry | 0 until reconciled |
| AUTH-021 | Replayed reference after successful consume | ALREADY_CONSUMED; reconcile existing execution | 0 additional |

Canonical typed outcomes are defined in `security/AUTHORIZATION_LIFECYCLE.md`. These are specifications only; no executable tests have been run.


## Audit-event required executor/reason keys (candidate v0.2.0; specified only)

| ID | Scenario | Expected result |
|---|---|---|
| AUD-SCHEMA-019 | Event includes executor_id and reason_code strings | Accept |
| AUD-SCHEMA-020 | Pre-execution event includes executor_id: null | Accept |
| AUD-SCHEMA-021 | Event with no applicable reason includes reason_code: null | Accept |
| AUD-SCHEMA-022 | Event omits executor_id | Reject |
| AUD-SCHEMA-023 | Event omits reason_code | Reject |
| AUD-SCHEMA-024 | Event supplies invalid non-string/non-null executor_id or reason_code | Reject |
| AUD-SCHEMA-025 | Denial/failure producer emits no stable reason_code | Producer rejects event |

These are proposed cases for the separately versioned audit-event v0.2.0 contract. They are not implemented or executed; the current v0.1.0 schema still permits omission.


## Audit-event v0.2.0 registry-resolution cases (candidate; schema tests)

| ID | Scenario | Expected result |
|---|---|---|
| AUD-SCHEMA-026 | Request received before registry resolution | Accept `requested`/`accepted`, `registry_status=unavailable`, explicit null version and reason |
| AUD-SCHEMA-027 | Registry missing/corrupt/unverifiable | Accept only `policy_denied`/`denied` with `POLICY_REGISTRY_UNAVAILABLE`, null version; no grant |
| AUD-SCHEMA-028 | Registry status resolved | Require concrete non-empty immutable registry_version |
| AUD-SCHEMA-029 | Authorization/dispatch event with unavailable registry | Reject; zero authorization/handler dispatch |
| AUD-SCHEMA-030 | Unavailable registry paired with unrelated denial reason | Reject; use the dedicated stable reason code |

These candidate cases are exercised by the v0.2.0 schema test suite. They do not establish runtime producer behavior or trusted provenance.

C0026 schema-registry regression coverage: the v0.2.0 candidate test suite now rejects every post-request lifecycle event (authorization, execution, cancellation, UNKNOWN, compensation and approval outcomes) when registry status is unavailable. The 13 parametrized negative cases run as part of the schema suite; they do not test a live producer, broker, audit store or runtime.


### AUD-SCHEMA-037 — event lifecycle/status consistency

- Positive: each of the 15 defined `event_type`/`result_status` pairs validates under audit-event v0.2.0.
- Negative: each event type rejects a deliberately inconsistent result status.
- The schema candidate defines the pair mapping; producer/runtime acceptance remains pending.


## Audit lifecycle event coverage — AUD-SCHEMA-031–036 (proposed; not executed)

| ID | Scenario | Expected result |
|---|---|---|
| AUD-SCHEMA-031 | Approval request is presented to an authenticated approver | Distinct correlated presentation event is schema-valid |
| AUD-SCHEMA-032 | Approver dismisses a request without approving | Distinct dismissal/terminal-denial event; no authorization grant |
| AUD-SCHEMA-033 | Approved request is invalidated or revoked before consume | Distinct invalidation/revocation event; consume is rejected |
| AUD-SCHEMA-034 | Authorization consume succeeds or is rejected | Distinct consume-accepted/consume-rejected event with request and consumption correlation |
| AUD-SCHEMA-035 | Consume response is lost and authority is queried | Reconciliation outcome is distinguishable from consume and execution result |
| AUD-SCHEMA-036 | Candidate schema receives an unsupported lifecycle event type | Reject until owner-approved event name and semantics are added |

These cases are proposed from SEC-SCHEMA-006. They are not implemented or executed. Do not count them as passing schema or producer tests.


## Policy-decision authorization-field schema tests

| Test | Decision | Required invariant | Coverage |
|---|---|---|---|
| POL-DEC-001 | ALLOW | Non-empty authorization reference and expiry | Positive and missing/null negative |
| POL-DEC-002 | REQUIRE_APPROVAL | Approval request ID present; no authorization grant | Positive, missing request ID and grant-reference negative |
| POL-DEC-003 | DENY | No expiry, approval request ID or authorization reference | Positive and authority-field negative cases |
| POL-DEC-004 | Any | Reject unknown top-level caller authority claims | Negative |

Automated schema tests added in `security/tests/test_security_schemas.py`. These validate the policy-decision JSON Schema only; they do not prove that a trusted policy engine minted the reference, that a broker validates it, or that one-time consumption is atomic. CI run 41136304088 is the current validation run; its result is pending at the time of this entry.

## Remote audit identity-binding cases — candidate audit-event v0.2.0

| ID | Scenario | Expected result | Coverage |
|---|---|---|---|
| AUD-REMOTE-001 | Remote policy event omits both device/session bindings | Reject | `test_audit_event_v020_remote_origin_requires_device_and_session_bindings` |
| AUD-REMOTE-002 | Remote event includes both correctly formatted SHA-256 bindings | Accept | `test_audit_event_v020_remote_origin_accepts_both_binding_digests` |
| AUD-REMOTE-003 | Remote event omits either binding independently | Reject | `test_audit_event_v020_remote_origin_requires_each_binding` |
| AUD-REMOTE-004 | Either binding is empty, null, non-string, uppercase, malformed or wrong-length | Reject | `test_audit_event_v020_remote_binding_digest_format_is_strict` |
| AUD-REMOTE-005 | Local/extension/system event supplies either remote binding | Reject | `test_audit_event_v020_non_remote_origin_rejects_remote_bindings` |
| AUD-REMOTE-006 | Remote event includes raw device/session identifiers, key material, session credentials, signatures, pairing secrets, or task/prompt/completion payloads | Reject | `test_audit_event_v020_rejects_raw_remote_identity_credentials_and_payloads` (11 parameter cases) |

These cases validate the candidate envelope only. They do not prove that a trusted remote adapter derives the digests correctly, that a producer persists them, or that a live policy/broker path enforces the binding. The active v0.1.0 schema remains unchanged; v0.2.0 producer migration remains gated on NEXUS-07/TUSKER-04 agreement.


C0053 expands AUD-REMOTE-006 with 11 explicit forbidden-field regression cases. This validates the candidate schema's strict envelope only; it does not prove runtime redaction or audit-store behavior.

## Policy-decision constraints fail-closed acceptance cases — SEC-SCHEMA-007 (pending owner vocabulary and runtime implementation)

| ID | Scenario | Expected result | Status |
|---|---|---|---|
| POL-CON-001 | Decision contains an empty `constraints: {}` object | Accept as carrying no additional execution permission | Schema test passed; consumer test pending |
| POL-CON-002 | Decision contains any non-empty constraint before a vocabulary is ratified | Reject / DENY; zero broker handler calls | Schema test passed; consumer test pending |
| POL-CON-003 | Decision contains an unknown top-level constraint key after vocabulary versioning | Reject / DENY; zero broker handler calls | Interim empty-only schema rejects it; future vocabulary tests pending |
| POL-CON-004 | A supported constraint has the wrong type or exceeds its agreed bound | Reject / DENY; zero broker handler calls | No non-empty vocabulary ratified; future typed-bound tests pending |
| POL-CON-005 | Consumer encounters missing, malformed, or unsupported constraint data | Fail closed; do not ignore, drop, reinterpret, or broaden scope | Pending consumer test |
| POL-CON-006 | Constraint attempts to relax registered operation bounds or expand canonical resource scope | Reject / DENY; zero broker handler calls | Pending consumer test |

POL-CON-001/002 have schema-level regression coverage: `constraints` is required, `{}` validates, and non-empty objects (including unknown keys and nested scope/timeout examples) are rejected by the v0.1.0 schema. This does not prove a live policy producer emits only `{}` or that a broker/policy consumer independently rejects unsupported data if schema validation is bypassed. POL-CON-003/004 remain pending any future non-empty vocabulary; POL-CON-005/006 consumer tests remain pending. SEC-SCHEMA-007 remains open until owners approve a versioned vocabulary and runtime fail-closed evidence.



## Policy-decision interim constraints coverage — SEC-SCHEMA-007

| ID | Scenario | Expected result | Coverage |
|---|---|---|---|
| POL-DEC-005a | Decision omits `constraints` | Reject | `test_policy_decision_constraints_must_be_present_and_empty` |
| POL-DEC-005b | Decision includes an empty `constraints` object | Accept | `test_policy_decision_constraints_must_be_present_and_empty` |
| POL-DEC-005c | Decision includes any non-empty or nested constraint object | Reject | `test_policy_decision_rejects_non_empty_or_non_object_constraints` |

This is an interim fail-closed contract, not the final constraint vocabulary. The v0.1.0 schema requires an empty object and rejects non-empty/non-object values. GitHub Actions run 41166079444 passed 163 security tests in 2.72s on Python 3.12. This does not prove policy-engine producer or broker-consumer enforcement at runtime.


| POL-CON-007 | Schema declares constraints as object, maxProperties=0 and additionalProperties=false | Pass | `test_policy_decision_constraints_schema_is_explicitly_closed_and_empty_only` |
| POL-CON-008 | Decision supplies a non-object constraints value | Reject | `test_policy_decision_rejects_non_empty_constraints` (expanded type cases) |
