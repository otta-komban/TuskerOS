# Remote-Control Security Assurance Case

**Status:** Draft v0.2 — structured assurance argument; AEGIS requirements accepted, runtime claims remain unproven  
**Owner:** PILOT-08 | **Branch:** `08-remote-control`  
**Decision:** **NO-GO** — this register is not security approval, implementation authorization, or evidence that controls work.

## 1. Purpose and assurance method

This document organizes the proposed remote-control security posture as claims, subclaims, supporting evidence obligations, assumptions, defeaters and accountable reviewers. It complements (does not replace) the threat model, requirements traceability matrix, abuse-case test matrix, protocol scenarios, and test evidence protocol.

Evidence labels:
- **SPECIFIED:** written requirement or test intent only.
- **IMPLEMENTED:** code exists at a pinned source revision.
- **EXECUTED:** a reproducible run produced machine-readable output.
- **REVIEWED:** an authorized reviewer accepted the evidence and its scope.

At creation, the branch has design artifacts only. No remote runtime feature, executable security test, validated OpenAPI contract, or owner sign-off is established. A written control or mapped test is not proof of enforcement.

## 2. Top-level assurance claim

**G0 — The remote-control service does not permit an unauthenticated, unauthorized, stale, revoked, or otherwise out-of-policy remote actor to cause a protected local action or obtain data outside the actor's authorized scope.**

**Argument:** G0 is defensible only if all claims G1–G8 below are supported by implementation-specific, reproducible evidence and accepted by the designated owners. Failure of any mandatory claim blocks release.

| Claim | Required subclaim / assurance obligation | Primary evidence sources | Owner / reviewer | Current status |
|---|---|---|---|---|
| **G1 Identity and pairing** | Pairing requires an authenticated local user, explicit local confirmation, proof of device-key possession, bounded enrollment, and safe key lifecycle. | PAIR-001..010; AB-01..AB-04; DEC-AEG-001..002; pairing race SCT-X01. Require negative tests for unsolicited pairing, replay, wrong/expired code, key substitution and concurrent approval. | AEGIS-06; NOVA-02 for consent UX; PILOT-08 integration | AEGIS requirements ACCEPTED; NOVA UX and runtime evidence pending |
| **G2 Session and revocation** | Session credentials are protected, scoped, bounded, rotated/revoked, and rejected after expiry or device/user/global revocation; active WSS is terminated. | SESS-001..014; AB-05..AB-07; DEC-AEG-003..004; revocation/stream tests in SCT matrix. Require HTTP and WSS evidence, restart behavior and race coverage. | AEGIS-06; PILOT-08 | AEGIS requirements ACCEPTED; runtime expiry/revocation/WSS evidence pending |
| **G3 Authorization and policy enforcement** | Every protected operation and retry receives fresh authoritative AEGIS authorization; client-supplied role/outcome is ignored; all non-ALLOW or indeterminate results cause zero Core dispatch and zero executor calls. | AUTH-001..010; AB-08..AB-12; SCT policy-failure and zero-dispatch assertions; DEC-AEG-005. Require instrumentation proving the enforcement point and no downstream call. | AEGIS-06 (policy authority); TUSKER-04 (Core boundary); PILOT-08 | AEGIS contract ACCEPTED; NEXUS/TUSKER integration and zero-dispatch evidence pending |
| **G4 Core task boundary and mutation safety** | Remote is an authenticated adapter to the normal Core lifecycle; trusted principal/device/origin are injected server-side; idempotency is durable and scoped; uncertain outcomes are reconciled rather than blindly retried. | TASK-001..016; AB-13..AB-16; TUSKER-04 task contract review and draft REMOTE-DECISIONS; SCT crash/idempotency cases. Require crash-consistency and dispatch-count evidence. | TUSKER-04; PILOT-08 | BLOCKED; TUSKER-04 draft REVISE/DEFER, exact schemas and persistence semantics open |
| **G5 Data projection and event integrity** | Snapshots/events are authorization-scoped and redacted; sequence/cursor semantics support gap recovery without leaking other principals' tasks or secrets. | EVT-001..012; AB-17..AB-18; SCT snapshot/event race, audit/privacy checks; DEC-TUS-006..007. Require cross-principal negative tests and reconnect/replay evidence. | TUSKER-04; AEGIS-06 audit/privacy; PILOT-08 | SPECIFIED; event/replay and redaction contract not frozen |
| **G6 Transport and deployment containment** | Listener defaults to loopback; remote exposure is explicit; TLS/origin/host/proxy handling, rate limits and message bounds resist network abuse; no public relay, silent port-forwarding, shell, D-Bus, Polkit or privileged broker surface exists. | NET-001..010; AB-19..AB-20; transport research; SCT rate-limit/proxy-trust tests; DEC-AEG-006. Require deployment configuration review and network-level tests. | AEGIS-06; PILOT-08; PHOENIX-10 for release packaging | AEGIS transport profile ACCEPTED; ATLAS deployment and runtime evidence pending |
| **G7 Local user control and recovery** | Local user can see connection/security state, revoke devices, disable remote access globally, and recover from a lost device without weakening local authorization. | NOVA decisions DEC-NOV-001..004; threat model; pairing/revocation/global-disable scenarios; SCT emergency shutdown. Require approved UX state flow and end-to-end disable test. | NOVA-02; AEGIS-06; PILOT-08 | BLOCKED; NOVA-02 has no owner-authored response |
| **G8 Auditability and evidence integrity** | Security-relevant events bind principal, device, session, action, policy decision, correlation ID and outcome; secrets are excluded; test artifacts are reproducible, immutable and reviewed. | Threat-model CTRL controls; security test evidence protocol; audit assertions in SCT matrix; DEC-AEG-005. Require schema/retention approval, log-redaction tests, pinned build/fixture hashes and reviewer disposition. | AEGIS-06; PILOT-08; PHOENIX-10 | AEGIS binding-digest requirement ACCEPTED; candidate schema producer agreement, retention and runtime evidence pending |

## 3. Cross-cutting assumptions

The argument currently assumes, but does not establish, that:

1. AEGIS-06 is the authoritative policy decision point and can provide a fresh, authenticated, fail-closed decision for each protected mutation.
2. TUSKER-04 Core exposes a supported adapter boundary with trusted context propagation, durable idempotency and authoritative reconciliation.
3. The local OS account/session and local confirmation UI cannot be silently impersonated by the remote client.
4. The chosen platform keystore, cryptographic primitives, TLS stack and deployment environment meet their eventual approved threat assumptions.
5. Owners will define a supported platform matrix and release/update lifecycle before implementation.

Each assumption must be converted into an approved interface, platform requirement or testable invariant. If an assumption is false or unsupported on a target platform, narrow the supported scope or reject that platform.

## 4. Defeaters and mandatory stop conditions

Any of the following defeats G0 and forces **NO-GO**:

- A protected request reaches Core/executor when policy returns DENY, REQUIRE_APPROVAL, timeout, unavailable, malformed, unknown, expired or stale.
- Client-controlled principal, role, device reference, risk level, policy result or audit identity influences authorization.
- A revoked/expired device can continue HTTP access or an active WebSocket session.
- Pairing can be completed without explicit local confirmation or with replayed/substituted proof.
- A retry after timeout can duplicate a non-idempotent side effect or report success without reconciliation.
- Snapshot/event replay leaks another principal's task data, private prompts, paths, outputs, evidence or secrets.
- Proxy headers, Origin/Host confusion, listener binding, rate-limit bypass or oversized messages permit unauthorized access or denial of service beyond the approved risk.
- Global remote disable does not prevent new and in-flight protected mutations according to an owner-approved shutdown contract.
- Audit logs omit the identity/action/decision correlation needed to investigate a security event, or contain credentials/secrets.
- Evidence is not tied to exact source/build, test definition, fixture and environment; test results are unreviewed or irreproducible.
- A required owner approval is missing, draft-only, ambiguous, or outside the approver's authority.

## 5. Minimum evidence package required to close G0

For every mandatory security test in `SECURITY-CONTROL-TO-TEST-MATRIX.md` and `PROTOCOL-ACCEPTANCE-AND-NEGATIVE-TESTS.md`, provide:

1. Exact source commit, build artifact digest, test-code commit and harness version.
2. Synthetic fixture IDs and hashes; no production credentials or user task data.
3. Exact setup, request/action, expected result and observed machine-readable result.
4. Instrumented policy, Core-dispatch and executor-call counts; explicit zero counts for all fail-closed cases.
5. Audit correlation evidence with sensitive values redacted.
6. Environment/platform/configuration, clocks and relevant network topology.
7. Reproducible logs/artifacts with integrity hashes and retention location.
8. Independent reviewer identity, review date, accepted scope, exceptions and residual-risk disposition.

Required review sequence: AEGIS-06 approves identity/session/policy/revocation/audit/transport; TUSKER-04 freezes Core task/event/idempotency/cancellation contracts; NOVA-02 approves consent/device-management/global-disable UX; PILOT-08 demonstrates integration; PHOENIX-10 and ATLAS-01 complete applicable release/platform reviews. No role may self-approve another owner's authority boundary.

## 6. Current assurance disposition

- Top-level claim G0: **UNPROVEN**.
- G1–G8: **SPECIFIED / BLOCKED**, not implemented or demonstrated.
- Protocol acceptance scenarios: 72 specified; 0 executed.
- Security abuse cases: 20 mapped; cross-cutting cases SCT-X01..X10 specified; 0 executed.
- Runtime security controls implemented: 0 established by this work.
- OpenAPI validation: not run.
- AEGIS-06: DEC-AEG-001..007 accepted; DEC-AEG-008 deferred/disabled for MVP. Runtime enforcement remains unproven.
- TUSKER-04: draft REVISE/DEFER input only; not final contract approval.
- NOVA-02 sign-off: absent; local consent/device/global-disable UX remains open.
- Implementation and release decision: **NO-GO**.

## 7. Owner disposition record

Do not mark a claim ACCEPTED based on this document or on a proposed safe default. Each owner must provide a durable response referencing the exact claim, contract version, evidence, accepted limitations and any residual risk. Record REVISE/DEFER explicitly and update the decision register and readiness review. Reassess G0 after each contract or threat-model change.


## C0012 — assurance decision refresh (2026-10-31)

AEGIS-06 has accepted the normative identity, pairing, session, authorization, revocation, audit-binding and transport requirements in contract v0.1.0; remote approvals are disabled for MVP. This advances the *requirements approval* evidence for G1, G2, G3, G6 and G8 only. It does not prove implementation or any control operation.

Still unproven:
- Ed25519 key handling and OS-protected storage in a running client/service.
- Pairing challenge atomic consume and local confirmation UX.
- RFC 9421 request verification, nonce replay rejection and expiry enforcement.
- AEGIS policy integration through NEXUS final consume with zero-dispatch evidence.
- Durable revocation and active WSS closure within 1 second.
- Audit producer integration, approved retention and secret-redaction execution.
- TLS deployment, Host/Origin enforcement, listener exposure defaults and measured resource bounds.
- TUSKER final task/event contract and NOVA local-control UX.

The 104 PAIR/SESS/NET conformance cases and 72 protocol scenarios are specifications only. Runtime tests executed: **0**. G0 remains **UNPROVEN** and overall disposition remains **NO-GO**.
