# PILOT-08 Security Test Evidence and Execution Protocol

**Status:** Draft v0.1 — evidence contract proposal; no runtime tests executed  
**Owner:** PILOT-08 | **Branch:** `08-remote-control`  
**Depends on:** `SECURITY-CONTROL-TO-TEST-MATRIX.md`, `PROTOCOL-ACCEPTANCE-AND-NEGATIVE-TESTS.md`, `REQUIREMENTS-TRACEABILITY-MATRIX.md`, `IMPLEMENTATION-READINESS-REVIEW.md`  
**Current decision:** **NO-GO**. This document does not authorize implementation, select a test framework, or represent test results.

## 1. Purpose

Define the minimum evidence record and execution discipline required to turn a specified security test into an independently reviewable result. The objective is to prevent ambiguous claims such as “security tests passed” without a known build, exact test definition, reproducible fixture, observable enforcement point and reviewer disposition.

This protocol is deliberately tool- and language-neutral. Project owners must approve the implementation stack, harness and artifact retention location before execution.

## 2. Evidence state model

Each test ID from the security matrix and protocol specification must have exactly one current state:

| State | Meaning | Permitted evidence |
|---|---|---|
| SPECIFIED | Intent, setup, action and expected result are documented only. | Specification reference and owner. |
| IMPLEMENTED | Test code exists and is linked to a source commit, but has not produced a valid run. | Test path, test-code commit and harness version. |
| BLOCKED | Test cannot run because a prerequisite, owner contract, environment or fixture is unavailable. | Explicit blocker, responsible owner and unblock condition. |
| EXECUTED | Run completed and produced machine-readable output, not yet reviewed. | Run ID, build SHA, environment, raw output and artifact hashes. |
| PASS | Reviewer confirms all required assertions and evidence are present. | Reviewed run record, assertion results and reviewer identity/time. |
| FAIL | One or more required assertions failed. | Reproduction details, failure artifact and triage owner. |
| INCONCLUSIVE | Result cannot establish the expected security property, e.g. missing dispatch instrumentation or harness crash. | Reason and corrective action; never counted as pass. |
| WAIVED | Named risk owner approved a time-bounded exception for a stated scope. | Signed waiver, rationale, compensating control, expiry and tracking issue. |

Rules:
- A test cannot move directly from SPECIFIED to PASS.
- A skipped test is BLOCKED or INCONCLUSIVE, never PASS.
- A flaky test is not PASS until its cause is understood and a deterministic rerun is reviewed.
- A waiver does not change the underlying test result and does not silently satisfy a mandatory release gate.
- Report counts by state and by test ID; never report only a percentage that hides blocked or waived cases.

## 3. Required run manifest

Every execution batch must produce a manifest. The following is a schema example, not a checked-in result:

```json
{
  "manifest_version": "1.0",
  "run_id": "SCT-RUN-YYYYMMDD-NNN",
  "started_at": "RFC3339 timestamp with offset",
  "completed_at": "RFC3339 timestamp with offset",
  "branch": "branch name",
  "source_commit": "full immutable commit SHA",
  "build_artifact_digest": "sha256:...",
  "build_profile": "debug|release|instrumented",
  "test_suite_commit": "full immutable commit SHA",
  "test_ids": ["SCT-01A", "PAIR-001"],
  "fixture_set_version": "immutable fixture identifier",
  "harness": {
    "name": "owner-approved test harness",
    "version": "exact version",
    "configuration_digest": "sha256:..."
  },
  "environment": {
    "os_image": "exact image and version",
    "architecture": "exact architecture",
    "network_profile": "loopback|approved-private-network|isolated-test",
    "proxy_profile": "none|named-approved-profile",
    "clock_control": "real|deterministic-fixture"
  },
  "dependencies": [
    {"name": "service", "version": "exact version", "digest": "sha256:..."}
  ],
  "result_summary": {
    "pass": 0,
    "fail": 0,
    "blocked": 0,
    "inconclusive": 0,
    "waived": 0
  },
  "artifacts": [
    {"path": "relative/path", "sha256": "...", "classification": "sanitized-test-evidence"}
  ],
  "review": {
    "state": "pending",
    "reviewer": null,
    "reviewed_at": null,
    "reviewed_commit": null
  }
}
```

Manifest requirements:
- Commit SHAs must be full immutable identifiers; branch names alone are insufficient.
- Artifact digests must be calculated from exact bytes after sanitization.
- Use deterministic fixture identifiers; do not put secrets or personal data in fixture names.
- The run manifest must identify whether dispatch counters, policy decision spies, event-sequence observers and audit sinks are instrumented. Missing required instrumentation makes the affected result INCONCLUSIVE.
- Preserve raw machine output in restricted CI artifacts when safe; publish only sanitized summaries in the repository.
- Never store production credentials, real pairing proofs, private keys, live user prompts, personal paths, raw task outputs or unredacted logs in a public repository.

## 4. Per-test result record

Each test execution must emit one record per test ID, even when the test is blocked or skipped:

```json
{
  "record_version": "1.0",
  "run_id": "SCT-RUN-YYYYMMDD-NNN",
  "test_id": "SCT-16A",
  "specification_ref": "SECURITY-CONTROL-TO-TEST-MATRIX.md#...",
  "requirement_ids": ["RC-AUTH-01", "RC-APPROVAL-01"],
  "abuse_case_ids": ["AB-16"],
  "state": "PASS|FAIL|BLOCKED|INCONCLUSIVE|WAIVED",
  "preconditions": ["synthetic principal fixture", "policy fixture returns DENY"],
  "action": "exact request or controlled fault injection",
  "expected_assertions": [
    {"id": "A1", "description": "Core dispatch count is zero", "expected": 0, "actual": 0, "result": "PASS"},
    {"id": "A2", "description": "Executor invocation count is zero", "expected": 0, "actual": 0, "result": "PASS"}
  ],
  "observed_response": {
    "protocol_status": "sanitized status/code",
    "correlation_id": "synthetic correlation reference"
  },
  "audit_assertions": ["actor context present", "no secret canary in output"],
  "artifact_refs": ["sha256:..."],
  "failure_or_blocker": null,
  "reviewer": "pending"
}
```

The example values above illustrate a hypothetical shape only. They are not results from a real run.

## 5. Mandatory security instrumentation

### 5.1 Authorization and zero-dispatch

For every protected mutation, test harness must independently observe:
- policy request count and exact action/resource/context binding;
- policy decision and policy version/freshness;
- Core adapter dispatch count;
- executor invocation count;
- task creation/side-effect count;
- correlation ID propagation across adapter, policy, Core and audit.

Required zero-dispatch cases:
1. DENY.
2. REQUIRE_APPROVAL (remote approval is disabled in MVP).
3. Policy timeout, unavailable service or connection failure.
4. Malformed, unverifiable or unknown policy decision.
5. Stale ALLOW or decision bound to different principal/device/session/action/resource/context.
6. Expired or revoked session/device.
7. Global remote-access disable.
8. Authorization state changes before retry.
9. Missing trusted context or audit identity.
10. Any policy dependency exception or indeterminate outcome.

For each, assert both:
- Core dispatch count = 0.
- Executor invocation count = 0.

Also assert no task/side effect was created. An HTTP error alone is insufficient proof. If the harness cannot observe the Core/executor boundary, the test is INCONCLUSIVE.

### 5.2 Revocation and stream closure

Observe revocation commit time, active HTTP request behavior, active WSS termination, reconnect result and post-restart credential result. The approved contract must define the closure bound and atomicity/linearization semantics before any timing assertion can be marked PASS.

### 5.3 Idempotency and uncertain outcome

Instrument Core acceptance and side-effect identity. Inject process/transport failure at each documented boundary. Demonstrate that same-principal/same-key/same-payload retry returns or reconciles one logical operation, conflicting payload rejects, and uncertain dispatch remains `unknown_outcome` until authoritative reconciliation. Do not infer exactly-once side effects from a single HTTP response.

### 5.4 Privacy and audit

Seed synthetic canary strings in every sensitive field. Scan all output surfaces: application logs, traces, metrics labels, exception output, crash artifacts, support bundles, URLs and CI artifacts. Audit assertions must simultaneously prove required actor/action/outcome/correlation fields exist and prohibited secrets/private task content do not.

## 6. Execution sequence

1. **Contract freeze:** obtain owner-authored decisions for applicable AEGIS, TUSKER and NOVA requirements; record reviewed commit SHAs.
2. **Harness approval:** project owners select stack, test runner, instrumentation, environment images, artifact storage and retention.
3. **Fixture review:** use synthetic identities/data; document trust boundaries and expected policy decisions; verify fixture secrets are ephemeral.
4. **Test implementation:** link every test code path to SCT/PAIR/SESS/AUTH/TASK/EVT/NET IDs and requirements.
5. **Baseline run:** capture clean-build version, environment, harness version and all manifest fields.
6. **Negative/fault runs:** run deterministic attack/failure cases; collect policy, Core, executor, task, event and audit observations.
7. **Reproduction:** independently rerun each FAIL/INCONCLUSIVE and any security-critical PASS selected by reviewer.
8. **Review:** owners inspect the exact source/build/test commits, assertion output, artifact digests and residual risks.
9. **Disposition:** mark PASS only with complete evidence; assign FAIL; document BLOCKED/INCONCLUSIVE; manage WAIVED through signed, expiring risk acceptance.
10. **Release gate:** publish aggregate state counts, uncovered IDs, owner approvals and a signed GO/NO-GO record.

## 7. Reviewer responsibilities

| Reviewer | Evidence they must inspect | Cannot approve on behalf of |
|---|---|---|
| AEGIS-06 | Identity/key binding, policy decision/freshness, fail-closed behavior, zero-dispatch instrumentation, revocation, transport, audit/redaction and residual risks. | Core implementation semantics or desktop UX. |
| TUSKER-04 | Core lifecycle, trusted context, idempotency persistence/reconciliation, cancellation race, snapshot/event consistency, Core/executor counters. | AEGIS policy decisions or pairing UX. |
| NOVA-02 | Consent, fingerprint/scope display, revoke/global-disable visibility, recovery and user-facing security states. | Cryptographic or Core security correctness. |
| PHOENIX-10 | Listener/TLS/firewall defaults, upgrade/rollback, service lifecycle, emergency shutdown and deployment environment. | AEGIS policy contract. |
| ATLAS-01 | OS account isolation, key storage, permissions, firewall and platform fallback behavior. | Product-level authorization policy. |
| PILOT-08 | Test-to-requirement mapping, test determinism, manifests, evidence integrity, coverage accounting and release report completeness. | Other owners' formal approval. |

A reviewer may ACCEPT, REVISE or DEFER only within their authority. Review must cite exact commit SHAs and a timestamp. Silence, emoji, informal acknowledgement or review of a different commit is not sign-off.

## 8. Failure severity and triage

| Severity | Examples | Required handling |
|---|---|---|
| Critical | Unauthorized mutation/executor call; credential or private key disclosure; bypass of AEGIS/Core; revoked session remains usable; remote approval bypass. | Stop release and affected work; preserve sanitized evidence; notify AEGIS/TUSKER/release owners; no waiver through this protocol. |
| High | Cross-principal data/event leak; pairing takeover; global disable bypass; persistent credential resurrection; unbounded denial of service with service compromise. | Block affected scope/release until fixed and independently rerun; named owner and root-cause review. |
| Medium | Bounded privacy leak, incomplete audit, recoverable event inconsistency, weak throttling under noncritical conditions. | Risk owner and remediation date required; release disposition explicitly reviewed. |
| Low | Non-security usability/diagnostic defect without trust-boundary impact. | Track and fix under normal prioritization; document why no security invariant is affected. |

Severity classification is provisional until AEGIS-06 approves the threat/risk rubric. No test author may downgrade a finding solely to meet a release target.

## 9. Evidence integrity, retention and publication

- Store restricted raw output in an owner-approved CI/artifact system with access control and retention rules.
- Publish a sanitized evidence index containing run IDs, test IDs, source/build/test commits, artifact hashes, result states, reviewer and issue references.
- Hash artifacts after sanitization; never hash one version and publish another.
- Do not include secret values in hash manifests, filenames, command-line arguments or URLs.
- Keep waivers separate from test result records; include approver, scope, compensating control, expiry and linked risk.
- Re-run tests after any relevant change to auth, policy, session, task, event, transport, persistence, logging or deployment behavior.
- Retain a release evidence snapshot that cannot be silently rewritten; corrections create a new version linked to the prior run.
- Retention duration, storage provider and evidence signing mechanism remain owner decisions, not assumed here.

## 10. Coverage and release report format

Every release candidate report must publish:
- total applicable test IDs;
- counts by SPECIFIED / IMPLEMENTED / BLOCKED / EXECUTED / PASS / FAIL / INCONCLUSIVE / WAIVED;
- exact IDs not implemented, not executed, failed, inconclusive or waived;
- run manifest IDs and source/build/test commits;
- zero-dispatch assertion coverage and any instrumentation gaps;
- OpenAPI/schema/WebSocket validation status;
- cross-principal read/event tests and redaction scan status;
- revocation/global-disable and restart/race test status;
- outstanding findings, owners, due dates and accepted residual risks;
- owner sign-offs with exact reviewed SHAs;
- signed GO/NO-GO decision.

Do not merge states into a single “completion percentage”. A suite with 95% pass and 5% blocked is not equivalent to 100% pass.

## 11. Current status and blockers

| Item | Current state |
|---|---|
| Threat model and 20 abuse cases | Specified |
| Security control-to-test matrix | Specified; 20 abuse cases and 10 additive cross-cutting tests mapped |
| Existing protocol scenarios | 72 specified; no execution evidence |
| Test harness / implementation stack | Not selected |
| Runtime implementation | 0 features |
| Test execution | 0 |
| OpenAPI validation | Not run |
| AEGIS-06 final approval | Not received |
| TUSKER-04 final approval | Not received; draft REVISE/DEFER only |
| NOVA-02 final UX approval | Not received |
| Release/platform sign-off | Not received |
| Implementation/release decision | **NO-GO** |

## 12. Approval requests

- **AEGIS-06:** approve or revise the mandatory policy instrumentation and zero-dispatch proof, security severity rubric, audit evidence/redaction requirements and evidence retention constraints.
- **TUSKER-04:** approve or revise Core dispatch/executor observation points, task side-effect identity, idempotency/reconciliation test boundaries and event/snapshot consistency evidence.
- **NOVA-02:** approve user-visible evidence expectations for local confirmation, revoke, disable, reconnect and recovery flows.
- **PHOENIX-10 / ATLAS-01:** identify deployment/platform evidence required for clean install, listener exposure, key storage, upgrade/rollback and shutdown.
- **PILOT-08:** maintain the test-ID/state ledger and refuse PASS without reproducible evidence.

No duplicate issue comments are posted by this completion: existing owner decision requests remain unanswered, and this document does not create a new owner decision that supersedes them.

---
*This is a proposed evidence protocol, not a test report, security approval, implementation authorization or release decision.*
