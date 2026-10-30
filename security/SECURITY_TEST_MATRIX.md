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
