# TuskerOS Remote Control — Protocol Acceptance & Negative-Test Specification

**Owner:** PILOT-08  
**Branch:** `08-remote-control`  
**Status:** Draft v0.1 — test requirements only; not evidence of implementation or security approval  
**Related contracts:** `ARCHITECTURE.md`, `contracts/v1/openapi.yaml`, `contracts/v1/TUSKER-04-TASK-CONTRACT-REVIEW.md`

## 1. Purpose and test boundary

This document turns the current remote-control proposal into observable acceptance criteria. It is deliberately implementation-neutral: no language, framework, cryptographic library, persistence engine or test runner is selected here.

The tests are intended to prove that the remote adapter is a narrow authenticated boundary. They do not authorize remote privileged execution, define AEGIS-06 policy, or replace TUSKER-04's task lifecycle.

**Non-negotiable invariants**

1. An unpaired device cannot obtain an authenticated session.
2. Pairing requires a locally authenticated owner and explicit local confirmation.
3. A challenge is short-lived, scoped, single-use and resistant to replay/concurrent consumption.
4. Every request is bound to a registered device and currently valid session.
5. Device/session revocation invalidates HTTP access and terminates active event streams within the agreed revocation bound.
6. The server derives principal, role, device and origin context; client JSON cannot assert them.
7. Every remote mutation is authorized by AEGIS-06 before reaching Core. Policy failure/unavailability fails closed.
8. Task submission and lifecycle operations use TUSKER-04's normal task path; the remote adapter is not a second task engine.
9. Idempotent retries do not create duplicate tasks; conflicting payload reuse is rejected.
10. Task snapshots and events disclose only authorized, redacted projections.
11. Event delivery is treated as at-least-once/best-effort unless Core explicitly guarantees otherwise; clients reconcile from authoritative snapshots and supported cursors.
12. A timeout after dispatch is not proof of failure. Unknown outcomes are reconciled; non-idempotent operations are never blindly retried.
13. Remote approval is disabled unless and until AEGIS-06 approves exact approval classes and the binding contract.
14. No remote route exposes shell, D-Bus, Polkit, NEXUS provider APIs or privileged broker controls.
15. Default network binding is loopback; private-network exposure requires explicit owner opt-in.

## 2. Test levels and evidence

| Level | Purpose | Minimum evidence |
|---|---|---|
| Schema/contract | Validate request/response constraints and documented error mapping | Validator output and fixtures |
| Unit | Exercise pure validation, state transitions and idempotency decisions | Test report and coverage |
| Service integration | Exercise pairing/session/device registry, policy adapter and Core adapter boundaries | Test report with controlled fakes |
| End-to-end | Exercise a paired client over the configured transport | Reproducible scenario log |
| Security/abuse | Exercise replay, revocation, origin, rate and disclosure boundaries | Negative-test report and captured redacted traces |
| Deployment | Verify listener/network defaults and service lifecycle | Configuration inspection and VM evidence |

Test fixtures must use synthetic identities, tasks, keys and secrets. Never commit live tokens, private keys, pairing codes, personal task content or raw production audit logs.

## 3. Pairing and device enrollment

| ID | Scenario | Setup/action | Expected result |
|---|---|---|---|
| PAIR-001 | Authorized pairing | Owner authenticates locally, requests challenge, scans/submits proof, confirms device | Device enrolled only after explicit local confirmation; response contains no private key or reusable challenge secret |
| PAIR-002 | No local owner authentication | Attempt challenge creation without local owner session | Denied; no challenge is issued |
| PAIR-003 | No local confirmation | Submit valid proof but do not confirm locally | Enrollment remains pending and cannot authenticate |
| PAIR-004 | Expired challenge | Submit proof after challenge expiry | Rejected; no device/session created |
| PAIR-005 | Challenge replay | Submit the same successful challenge/proof twice | Second attempt rejected; no duplicate device or credential |
| PAIR-006 | Concurrent challenge consumption | Race two completions against one challenge | At most one completion succeeds; state transition is atomic |
| PAIR-007 | Wrong challenge/device binding | Use proof for another challenge or alter bound device key | Rejected without disclosing sensitive challenge state |
| PAIR-008 | Brute-force challenge guessing | Repeated invalid attempts | Rate limit/backoff applies; bounded resource use; no secret-dependent verbose response |
| PAIR-009 | QR/code leakage | Inspect pairing display and logs | No long-lived bearer credential in QR, URL, logs or analytics |
| PAIR-010 | Owner disables remote access | Disable global remote access locally | New pairing/session attempts fail; existing sessions are invalidated according to approved policy |

**Acceptance:** PAIR-001 through PAIR-010 pass before pairing is considered releasable. Expiry duration, attempt thresholds and concurrent enrollment policy must be set by security review rather than guessed in this document.

## 4. Session authentication, lifecycle and revocation

| ID | Scenario | Setup/action | Expected result |
|---|---|---|---|
| SESS-001 | Valid proof of possession | Paired device proves possession of its registered private key | Session created with approved scope and expiry |
| SESS-002 | Unknown device | Authenticate with unregistered device identity | Denied; no session |
| SESS-003 | Wrong key | Registered device identifier with unrelated key proof | Denied; no session |
| SESS-004 | Revoked device | Authenticate after device revocation | Denied |
| SESS-005 | Expired session | Call protected endpoint after expiry | Denied; no protected data returned |
| SESS-006 | Session replay from another device | Replay credential/proof from a different device context | Denied by device binding/proof rules |
| SESS-007 | Session rotation replay | Reuse a superseded rotation credential/proof | Rejected; replay is recorded without logging secrets |
| SESS-008 | Explicit session logout | Revoke current session then reuse it | Revocation takes effect; protected HTTP requests fail |
| SESS-009 | Device-wide revocation | Revoke one device with multiple sessions | All sessions for that device become invalid |
| SESS-010 | Active WebSocket revocation | Revoke device/session while event stream is open | Stream is closed within the AEGIS-approved bound; subsequent reconnect denied |
| SESS-011 | Service restart | Restart service with sessions present | Behavior follows reviewed persistence policy; if session state is not safely durable, clients must reauthenticate |
| SESS-012 | Clock skew | Client clock is ahead/behind | Server-authoritative expiry; client clock cannot extend credential lifetime |
| SESS-013 | Policy dependency unavailable | Attempt protected mutation while AEGIS is unavailable | Fail closed; Core mutation is not dispatched |
| SESS-014 | Credential leakage | Inspect URL, logs, traces, crash reports and error messages | No bearer token, private key or proof material is exposed |

**Acceptance:** A revoked device/session cannot continue through HTTP or WebSocket. The precise propagation bound, refresh/rotation policy and durable-session behavior require AEGIS-06 approval.

## 5. Authorization and identity spoofing

| ID | Scenario | Setup/action | Expected result |
|---|---|---|---|
| AUTH-001 | Client supplies a different principal | Add/alter `principal_ref` in request JSON | Field rejected as unknown or ignored; authenticated principal is derived server-side |
| AUTH-002 | Client supplies role/admin claim | Add `role`, `is_admin`, `scopes` or policy result | Rejected/ignored; client cannot grant authority |
| AUTH-003 | Client forges remote origin | Supply local origin or another device reference | Rejected/ignored; trusted adapter supplies remote origin and authenticated device reference |
| AUTH-004 | Cross-owner task read | Request task belonging to another principal | Denied or non-disclosing not-found behavior per AEGIS/Core contract |
| AUTH-005 | Cross-owner task mutation | Attempt to cancel another principal's task | Denied before Core mutation |
| AUTH-006 | Policy deny | AEGIS returns deny | No task or mutation dispatched; safe denial returned |
| AUTH-007 | Policy unavailable/invalid | AEGIS timeout, malformed response or unavailable dependency | Fail closed; no mutation |
| AUTH-008 | Policy decision stale | Replay an earlier allow decision after context/session changes | Re-evaluate current policy; stale allow is not reused |
| AUTH-009 | Retry authorization | Repeat mutation after policy-relevant state changes | Fresh authorization on each attempt; idempotency does not bypass policy |
| AUTH-010 | Privileged route probing | Probe shell, D-Bus, Polkit, NEXUS and privileged-broker paths | No such remote endpoint exists; request cannot be routed to those systems |

**Acceptance:** Identity and authorization tests must be jointly reviewed by AEGIS-06 and TUSKER-04. A remote gateway allowlist alone is not proof of authorization.

## 6. Task submission, idempotency and lifecycle

| ID | Scenario | Setup/action | Expected result |
|---|---|---|---|
| TASK-001 | Valid task submission | Submit bounded user request with valid session and required headers | One task accepted by the normal Core path; response identifies task and current safe state |
| TASK-002 | Missing idempotency key | Submit mutation without required key | Rejected before dispatch |
| TASK-003 | Same key, same payload | Submit same request twice for same authenticated principal | Same task/result returned; no duplicate task |
| TASK-004 | Same key, conflicting payload | Reuse key with changed request body | Conflict; original task unchanged |
| TASK-005 | Same key, different principal | Another principal submits identical key/payload | Separate idempotency namespace; cannot read or claim first principal's task |
| TASK-006 | Client injects tool/risk/policy | Add tool name, risk level, authorization outcome or privileged command | Rejected as unknown input; no effect on Core planning/policy |
| TASK-007 | Oversized request/context | Exceed documented body, text or reference limits | Rejected before expensive processing; bounded resource use |
| TASK-008 | Invalid context reference | Supply inaccessible/invalid opaque context reference | Core validates access; no disclosure or privilege expansion |
| TASK-009 | Cancellation of nonterminal task | Request cancel for authorized supported task | Routed to Core; response distinguishes accepted request from confirmed stop |
| TASK-010 | Cancellation of terminal task | Request cancel after terminal state | No state corruption; stable conflict/terminal response per Core contract |
| TASK-011 | Pause/resume without safe checkpoint | Request unsupported pause/resume | Explicit unsupported response; no simulated pause/resume |
| TASK-012 | Dispatch timeout before known acceptance | Simulate timeout with no dispatch evidence | Return documented known-not-dispatched or retry-safe result only when Core proves no dispatch |
| TASK-013 | Connection lost after dispatch | Drop transport after Core may have accepted request | Return/reconcile `unknown_outcome`; do not blindly resubmit |
| TASK-014 | Reconcile unknown outcome | Query authoritative idempotency/task status after uncertain response | Client can discover whether original operation was accepted without creating another task |
| TASK-015 | Core unavailable | Submit when Core is unavailable | Fail closed before dispatch or clearly report unknown outcome if dispatch had begun |
| TASK-016 | Audit context propagation | Submit task | Trusted principal, device/session reference and correlation ID reach Core and AEGIS audit context |

**Acceptance:** TUSKER-04 must confirm canonical state values, terminal-state rules, exact Core submission interface, idempotency retention/scope, cancellation result semantics and unknown-outcome reconciliation behavior before implementation.

## 7. Task snapshot and event stream

| ID | Scenario | Setup/action | Expected result |
|---|---|---|---|
| EVT-001 | Authorized snapshot | Read own task snapshot | Minimal authorized projection only |
| EVT-002 | Sensitive field redaction | Populate fixture with private prompt, path, output and evidence | Fields absent/redacted unless explicit reviewed user/device policy permits them |
| EVT-003 | Event sequence | Receive ordered events for a task | Sequence/cursor semantics match Core contract |
| EVT-004 | Duplicate event | Deliver same event more than once | Client deduplicates by stable event identity/sequence; no duplicate mutation |
| EVT-005 | Missing event/gap | Omit an event in stream | Client detects gap and requests authoritative snapshot/resync |
| EVT-006 | Reconnect with valid cursor | Disconnect and reconnect with supported cursor | Replay is bounded and consistent with documented retention guarantee |
| EVT-007 | Cursor expired/unsupported | Reconnect with cursor outside retention window | Server instructs snapshot reset; does not silently pretend stream is complete |
| EVT-008 | Unauthorized resource event | Attempt to subscribe/read another owner's resource | No unauthorized event or metadata leaks |
| EVT-009 | Stale session on open stream | Expire session while WebSocket is active | Stream closes or authorization is revalidated within approved bound |
| EVT-010 | Origin rejection | Browser client connects with untrusted Origin | Upgrade rejected |
| EVT-011 | Message/resource exhaustion | Send oversized messages or excessive connections | Limits enforced; service remains bounded |
| EVT-012 | Event as authority | Client receives approval/task event and attempts action without fresh authorized request | Event receipt grants no authority; mutation requires normal authenticated policy path |

**Acceptance:** Event ordering, cursor scope, retention and replay guarantees are explicitly unresolved pending TUSKER-04. Tests must be written against the agreed semantics, not assumptions.

## 8. Transport and deployment security

| ID | Scenario | Setup/action | Expected result |
|---|---|---|---|
| NET-001 | Default startup | Start service with default configuration | Listener bound to loopback only |
| NET-002 | Explicit private-network opt-in | Owner enables documented private-network mode | Only configured interface/address exposed; user receives clear status |
| NET-003 | No silent public exposure | Inspect firewall/router/UPnP behavior | No automatic port forwarding, UPnP mapping or public tunnel |
| NET-004 | Invalid TLS identity | Connect with untrusted/expired/mismatched server identity | Connection fails closed; no plaintext downgrade |
| NET-005 | Host/header confusion | Send unexpected Host/forwarded headers | Rejected or normalized according to explicit trusted-proxy configuration |
| NET-006 | Browser Origin allowlist | Send untrusted Origin on WebSocket/browser-auth path | Rejected before upgrade |
| NET-007 | Rate limits | Burst pairing/auth/task/event requests | Limits and backoff apply without bypass via connection churn |
| NET-008 | Request bounds | Send oversized headers/body/frame | Rejected safely; service remains responsive |
| NET-009 | Protocol downgrade | Negotiate unsupported/older insecure protocol | Rejected; no silent fallback |
| NET-010 | Diagnostics secrecy | Trigger errors and inspect diagnostics | No secrets, raw credentials or sensitive task content in logs |

**Acceptance:** Listener and TLS behavior require AEGIS-06 and release/deployment owner review. The exact certificate provisioning model remains open.

## 9. Remote approval — explicitly gated

Remote approval tests are **not executable release criteria** until AEGIS-06 approves at least one remote approval class and the versioned contract.

If such approval is later authorized, add tests that prove:
- Approval binds exact action, resource, input digest, actor, device/session, expiry and audit reference.
- The decision is one-use and idempotent under the approved retry semantics.
- Modified action/resource/input is rejected.
- Expired, replayed, stale-version or revoked-session decisions are rejected.
- Policy is re-evaluated at decision time.
- Deny is auditable and cannot be transformed into allow by the remote adapter.
- No approval event itself grants approval authority.

Until then, approval endpoints remain unavailable/disabled and remote approval attempts are denied.

## 10. Exit gates

### Contract gate — before implementation
- [ ] AEGIS-06 approves device identity, session, authorization, revocation, audit and transport boundary.
- [ ] TUSKER-04 approves task submission, idempotency, snapshot, event, cancellation and unknown-outcome semantics.
- [ ] NOVA-02 approves local pairing initiation/confirmation, device revoke and remote-access disable UX.
- [ ] OpenAPI and event schemas validate against the agreed contracts.
- [ ] Implementation language/framework and repository conventions are selected by project owners.

### MVP security gate — before release
- [ ] All applicable PAIR, SESS, AUTH, TASK, EVT and NET scenarios pass.
- [ ] No critical/high security findings remain unresolved.
- [ ] Active HTTP and WebSocket access is terminated on device/session revoke within approved bounds.
- [ ] No unauthorized mutation reaches Core.
- [ ] Idempotency and unknown-outcome reconciliation are demonstrated under fault injection.
- [ ] Default loopback binding and explicit opt-in network exposure are verified in a clean VM.
- [ ] Secret-redaction checks pass against logs, URLs, traces and error output.
- [ ] Test report states exact platform/VM coverage and residual risks.

## 11. Open decisions (must not be silently assumed)

1. Challenge lifetime, attempt thresholds, concurrent pairing policy and device-label rules.
2. Device key algorithm, key rotation, secure-storage requirements and unsupported-platform behavior.
3. Session credential format, proof-of-possession protocol, lifetime, idle expiry and rotation/revocation consistency.
4. Exact AEGIS policy request/decision schema and fail-closed error mapping.
5. Task state enum, terminal states, idempotency retention and cross-restart behavior.
6. Event cursor scope, ordering, replay retention and snapshot consistency.
7. Cancellation accepted-vs-confirmed semantics and side-effect reporting.
8. Exact unknown-outcome reconciliation API and guarantees.
9. Browser/native client credential and Origin/CSRF strategies.
10. TLS certificate provisioning and trusted-proxy configuration.
11. Audit event schema, retention and privacy/redaction policy.
12. Whether any remote approval category will ever be enabled.

No scenario in this document is claimed implemented or passed. Record test evidence only after an actual test has been executed against an identified build/commit.
